"""
Test script: Phase 3 End-to-End High-Intent Pipeline Visualization
Executes:
1. Phase 3A: Zero-cost HTTPX Googlebot LinkedIn ID Resolution (modal-labs -> 79045818)
2. Phase 3B: Apify LinkedIn Company Insights Scraper (freshdata/linkedin-company-insights-scraper via APIFY_INSIGHTS_API_KEY)
3. Phase 3C: Google Serper ATS Job Search (30-60D lock, Ashby/Greenhouse/Lever, Mid/Senior Tech & TA filters)

Combines everything into the exact unified JSON object ready to save to database & serve to Frontend Jobs Tab!
Saves output to scratch/phase3_full_lead_profile_visualization.json.
"""
import os
import re
import sys
import json
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv("backend/.env")

APIFY_INSIGHTS_API_KEY = os.getenv("APIFY_INSIGHTS_API_KEY") or os.getenv("APIFY_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

OUTPUT_FILE = os.path.join("scratch", "phase3_full_lead_profile_visualization.json")


# -----------------------------------------------------------------
# 3A. Zero-Cost LinkedIn ID Resolver (HTTPX + Googlebot UA)
# -----------------------------------------------------------------
async def resolve_linkedin_company_id(company_slug: str) -> str | None:
    target_url = f"https://www.linkedin.com/company/{company_slug}/"
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"
    ]
    
    patterns = [
        r"urn:li:fs_normalized_company:(\d+)",
        r"urn:li:fs_miniCompany:(\d+)",
        r"urn:li:company:(\d+)",
        r"urn:li:organization:(\d+)",
        r'"objectUrn"\s*:\s*"urn:li:[^"]+:(\d+)"',
        r'companyId["\s:=]+(\d+)',
        r'organizationId["\s:=]+(\d+)',
        r'data-company-id=["\'](\d+)["\']',
        r'com\.linkedin\.voyager\.organization\.Company/(\d+)',
        r'linkedin\.com/company/(\d+)'
    ]

    async with httpx.AsyncClient(follow_redirects=True, timeout=12.0) as client:
        for ua in user_agents:
            headers = {
                "User-Agent": ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9"
            }
            try:
                resp = await client.get(target_url, headers=headers)
                if resp.status_code == 200:
                    for p in patterns:
                        matches = re.findall(p, resp.text)
                        for match in matches:
                            if match and 6 <= len(match) <= 10 and match != "120000":
                                return match
            except Exception as e:
                pass

    return None


# -----------------------------------------------------------------
# 3B. Apify LinkedIn Company Insights Scraper
# -----------------------------------------------------------------
async def fetch_linkedin_company_insights(company_id: str, company_slug: str) -> dict | None:
    if not APIFY_INSIGHTS_API_KEY:
        return None

    url = f"https://api.apify.com/v2/acts/freshdata~linkedin-company-insights-scraper/run-sync-get-dataset-items"
    params = {"token": APIFY_INSIGHTS_API_KEY}
    payload = {"company_id": company_id, "company_name": company_slug}

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, params=params, json=payload)
            if resp.status_code in [200, 201]:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get("data")
                elif isinstance(data, dict):
                    return data.get("data")
    except Exception as e:
        print(f"⚠️ Exception fetching Insights: {e}")

    return None


TECH_AND_TA_KEYWORDS = [
    "engineer", "developer", "architect", "systems", "ml", "ai", "security", 
    "tech", "software", "infrastructure", "data", "product", "manager",
    "talent acquisition", "recruiter", "recruitment", "head of people", "hr", "people partner"
]
ENTRY_LEVEL_EXCLUSIONS = ["junior", "intern", "internship", "trainee"]


def is_entry_level_associate(title_lower: str) -> bool:
    if "associate" not in title_lower:
        return False
    senior_modifiers = ["director", "senior", "vp", "vice president", "head", "lead", "principal", "manager", "solutions architect"]
    return not any(mod in title_lower for mod in senior_modifiers)


def is_valid_company_job(title: str, link: str, snippet: str, company_name: str, company_slug: str) -> bool:
    t_lower = title.lower()
    l_lower = link.lower()
    c_lower = company_name.lower()
    slug_lower = company_slug.lower()

    if any(ex in t_lower for ex in ENTRY_LEVEL_EXCLUSIONS):
        return False
    if is_entry_level_associate(t_lower):
        return False

    has_qualified_role = any(kw in t_lower or kw in snippet.lower() for kw in TECH_AND_TA_KEYWORDS)
    if not has_qualified_role:
        return False

    target_domains = [
        f"ashbyhq.com/{slug_lower}",
        f"greenhouse.io/{slug_lower}",
        f"lever.co/{slug_lower}",
        f"workable.com/{slug_lower}",
        f"indeed.com/cmp/{slug_lower}",
        f"linkedin.com/company/{slug_lower}",
        f"linkedin.com/jobs",
        f"{slug_lower}.com"
    ]
    if any(dom in l_lower for dom in target_domains):
        return True

    title_anchors = [
        f"@ {c_lower}", f"at {c_lower}", f"- {c_lower}", f"| {c_lower}", 
        f", {c_lower}", f"{c_lower} -", f"{c_lower}:", f"{c_lower} jobs"
    ]
    if any(anchor in t_lower for anchor in title_anchors):
        return True

    return False


# -----------------------------------------------------------------
# 3C. Google Serper ATS Job Search (Senior-Calibrated)
# -----------------------------------------------------------------
async def fetch_company_jobs_serper(company_name: str, company_slug: str, domain: str) -> dict:
    if not SERPER_API_KEY:
        return {"total_results": 0, "qualified_jobs": []}

    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}

    single_ats_queries = [
        f"site:jobs.ashbyhq.com/{company_slug}",
        f"site:boards.greenhouse.io/{company_slug}",
        f"site:jobs.lever.co/{company_slug}",
        f"site:apply.workable.com/{company_slug}"
    ]

    qualified = []
    platform_stats = {}

    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            for q in single_ats_queries:
                platform_name = q.split("site:")[1].split("/")[0]
                payload = {"q": q, "num": 10, "tbs": "qdr:m", "autocorrect": False}
                resp = await client.post(url, headers=headers, json=payload)
                raw_items = resp.json().get("organic", []) if resp.status_code == 200 else []
                
                p_qual = []
                for item in raw_items:
                    t = item.get("title", "")
                    l = item.get("link", "")
                    s = item.get("snippet", "")
                    if is_valid_company_job(t, l, s, company_name, company_slug):
                        p_qual.append({
                            "title": t,
                            "link": l,
                            "snippet": s,
                            "date": item.get("date", "Past 30 Days"),
                            "ats_platform": platform_name
                        })
                        qualified.append(p_qual[-1])

                platform_stats[platform_name] = len(p_qual)

            if len(qualified) > 0:
                return {"total_results": len(qualified), "used_fallback": False, "platform_stats": platform_stats, "qualified_jobs": qualified}

            # Fallback
            fallback_query = f'site:linkedin.com/company/{company_slug}/jobs OR site:indeed.com/cmp/{company_slug}/jobs OR site:{domain}/careers OR ("{company_name}" ("Engineer" OR "Manager" OR "Recruiter") (site:ashbyhq.com OR site:greenhouse.io OR site:lever.co OR site:workable.com OR site:linkedin.com/jobs OR site:indeed.com))'
            f_payload = {"q": fallback_query, "num": 10, "tbs": "qdr:m", "autocorrect": False}
            f_resp = await client.post(url, headers=headers, json=f_payload)
            f_raw = f_resp.json().get("organic", []) if f_resp.status_code == 200 else []

            for item in f_raw:
                t = item.get("title", "")
                l = item.get("link", "")
                s = item.get("snippet", "")
                if is_valid_company_job(t, l, s, company_name, company_slug):
                    qualified.append({
                        "title": t,
                        "link": l,
                        "snippet": s,
                        "date": item.get("date", "Past 30 Days"),
                        "ats_platform": "FALLBACK_SERP"
                    })

            return {"total_results": len(qualified), "used_fallback": True, "platform_stats": platform_stats, "qualified_jobs": qualified}

    except Exception as e:
        print(f"⚠️ Exception fetching Jobs: {e}")
        return {"total_results": 0, "error": str(e)}


# -----------------------------------------------------------------
# Main Pipeline Visualization Runner
# -----------------------------------------------------------------
async def run_phase3_full_pipeline_visualization():
    company_name = "Modal"
    company_slug = "modal-labs"
    domain = "modal.com"
    simulated_intent_score = 95  # >= 80, so Phase 3 triggers!

    print("=" * 80)
    print(f"🚀 PHASE 3 HIGH-INTENT ENRICHMENT PIPELINE FOR '{company_name}' ({domain})")
    print(f"🔥 Intent Score: {simulated_intent_score}/100 (>= 80 THRESHOLD PASSED!)")
    print("=" * 80 + "\n")

    # Step 3A: Resolve Company ID ($0 cost)
    print("🔹 [Step 3A] Resolving LinkedIn Company ID via HTTPX Googlebot...")
    company_id = await resolve_linkedin_company_id(company_slug)
    print(f"   Resolved Company ID: '{company_id}'\n")

    # Step 3B: Apify Company Insights
    insights_data = None
    if company_id:
        print(f"🔹 [Step 3B] Fetching LinkedIn Company Insights via Apify (ID: {company_id})...")
        insights_data = await fetch_linkedin_company_insights(company_id, company_slug)
        print(f"   Fetched Insights Data: {'YES' if insights_data else 'NO'}\n")

    # Step 3C: Google Serper ATS Job Search
    print(f"🔹 [Step 3C] Searching Active ATS Job Openings via Serper (Past 30-60D)...")
    jobs_data = await fetch_company_jobs_serper(company_name, company_slug, domain)
    print(f"   Fetched {jobs_data.get('total_results', 0)} qualified Mid/Senior Tech & TA jobs\n")

    # Final Combined JSON Record (Saved to Database & Served to Frontend Jobs Tab)
    full_lead_record = {
        "lead_info": {
            "company_name": company_name,
            "company_slug": company_slug,
            "domain": domain,
            "intent_score": simulated_intent_score,
            "pipeline_status": "QUALIFIED_HIGH_INTENT",
            "company_linkedin_id": company_id,
            "linkedin_url": f"https://www.linkedin.com/company/{company_slug}/"
        },
        "jobs_tab_infographics_data": {
            "headcount_summary": {
                "total_employees": insights_data.get("total_employees") if insights_data else None,
                "headcount_growth_1y": insights_data.get("headcount_growth", {}).get("1y") if insights_data else None,
                "headcount_growth_6m": insights_data.get("headcount_growth", {}).get("6m") if insights_data else None,
                "median_tenure_years": insights_data.get("median_employee_tenure") if insights_data else None
            },
            "department_breakdown": insights_data.get("headcount_by_function") if insights_data else {},
            "department_growth_yoy": insights_data.get("headcount_growth_by_function") if insights_data else {},
            "headcount_24m_trajectory": insights_data.get("headcount_by_month") if insights_data else [],
            "recent_new_hires_monthly": insights_data.get("new_hires") if insights_data else []
        },
        "active_job_openings_cards": jobs_data
    }

    os.makedirs("scratch", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(full_lead_record, f, indent=2)

    print("=" * 80)
    print(f"💾 SAVED COMPLETE PHASE 3 VISUALIZATION RECORD TO: '{OUTPUT_FILE}'")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(run_phase3_full_pipeline_visualization())

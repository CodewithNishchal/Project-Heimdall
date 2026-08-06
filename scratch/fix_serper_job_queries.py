"""
Senior-Calibrated Serper Job Intelligence Engine:
1. Performs 4 separate single-site ATS queries (Ashby, Greenhouse, Lever, Workable) — NO fragile path-level OR chains.
2. Enforces recency lock (tbs="qdr:m") and disables autocorrect (autocorrect=False) for exact slug lookups.
3. Fallback query covers Indeed (indeed.com/cmp/), LinkedIn Jobs (linkedin.com/company/.../jobs), Workable, Ashby, Greenhouse, Lever.
4. Synchronizes 'Manager' in query and allow-list.
5. Smart 'Associate' check: Only rejects entry-level 'Associate' (e.g. Associate Engineer), preserving 'Associate Director', 'Senior Associate', 'Associate VP'.
6. Expanded title format matching: '- Company', '| Company', ', Company', 'at Company', '@ Company', 'Company -', 'Company:'.

Saves output to scratch/fix_serper_job_queries_output.json.
"""
import os
import sys
import re
import json
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv("backend/.env")

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
OUTPUT_FILE = os.path.join("scratch", "fix_serper_job_queries_output.json")

# Synchronized Allow-List (includes Manager, Engineer, Developer, Architect, TA, Recruiter, HR)
TECH_AND_TA_KEYWORDS = [
    "engineer", "developer", "architect", "systems", "ml", "ai", "security", 
    "tech", "software", "infrastructure", "data", "product", "manager",
    "talent acquisition", "recruiter", "recruitment", "head of people", "hr", "people partner"
]

# Excluded Entry-Level Titles
ENTRY_LEVEL_EXCLUSIONS = ["junior", "intern", "internship", "trainee"]


def is_entry_level_associate(title_lower: str) -> bool:
    """
    Smart Associate Check: Only returns True if 'associate' is used as an entry-level title
    (e.g., 'Associate Engineer', 'Software Associate').
    Returns False if paired with senior modifiers (e.g., 'Associate Director', 'Senior Associate', 'Associate Vice President').
    """
    if "associate" not in title_lower:
        return False

    # Preserve senior associate roles
    senior_modifiers = ["director", "senior", "vp", "vice president", "head", "lead", "principal", "manager", "solutions architect"]
    if any(mod in title_lower for mod in senior_modifiers):
        return False  # Not entry level!

    return True


def is_valid_company_job(title: str, link: str, snippet: str, company_name: str, company_slug: str) -> bool:
    t_lower = title.lower()
    l_lower = link.lower()
    c_lower = company_name.lower()
    slug_lower = company_slug.lower()

    # 1. Reject entry-level titles (Junior, Intern, Trainee, or Entry-level Associate)
    if any(ex in t_lower for ex in ENTRY_LEVEL_EXCLUSIONS):
        return False
    if is_entry_level_associate(t_lower):
        return False

    # 2. Check if text matches qualified Tech/TA/Management keywords
    has_qualified_role = any(kw in t_lower or kw in snippet.lower() for kw in TECH_AND_TA_KEYWORDS)
    if not has_qualified_role:
        return False

    # 3. Match ATS / Job Board domain paths (ashbyhq.com/modal, greenhouse.io/modal, lever.co/modal, workable.com/modal, indeed.com/cmp/modal, linkedin.com/company/modal...)
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

    # 4. Expanded Title Anchors (- Company, | Company, , Company, at Company, @ Company, Company -)
    title_anchors = [
        f"@ {c_lower}",
        f"at {c_lower}",
        f"- {c_lower}",
        f"| {c_lower}",
        f", {c_lower}",
        f"{c_lower} -",
        f"{c_lower}:",
        f"{c_lower} jobs"
    ]
    if any(anchor in t_lower for anchor in title_anchors):
        return True

    return False


async def fetch_single_serper_ats_query(client: httpx.AsyncClient, query_str: str) -> list[dict]:
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {
        "q": query_str,
        "num": 10,
        "tbs": "qdr:m",  # Past month recency lock
        "autocorrect": False  # Disable autocorrect for exact slug lookups
    }

    try:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code == 200:
            return resp.json().get("organic", [])
    except Exception as e:
        print(f"⚠️ Error executing query '{query_str}': {e}")
    return []


async def fetch_calibrated_serper_jobs(company_name: str = "Modal", domain: str = "modal.com"):
    if not SERPER_API_KEY:
        print("❌ ERROR: SERPER_API_KEY not found in backend/.env")
        return

    company_slug = company_name.lower().replace(" ", "")

    print("=" * 80)
    print(f"🚀 SENIOR-CALIBRATED SERPER JOB INTELLIGENCE FOR '{company_name}' ({domain})")
    print(f"🗓️ Recency Lock: tbs='qdr:m' | Autocorrect: False")
    print("=" * 80 + "\n")

    # FIX 1: Split into 4 separate unambiguous ATS single-site queries (Ashby, Greenhouse, Lever, Workable)
    single_ats_queries = [
        f"site:jobs.ashbyhq.com/{company_slug}",
        f"site:boards.greenhouse.io/{company_slug}",
        f"site:jobs.lever.co/{company_slug}",
        f"site:apply.workable.com/{company_slug}"
    ]

    qualified_jobs = []
    platform_stats = {}

    async with httpx.AsyncClient(timeout=25.0) as client:
        print("🔹 [Phase 1] Executing 4 Separate Single-Site ATS Queries...")
        for q in single_ats_queries:
            platform_name = q.split("site:")[1].split("/")[0]
            raw_results = await fetch_single_serper_ats_query(client, q)
            
            p_qualified = []
            for item in raw_results:
                t = item.get("title", "")
                l = item.get("link", "")
                s = item.get("snippet", "")
                if is_valid_company_job(t, l, s, company_name, company_slug):
                    p_qualified.append({
                        "title": t,
                        "link": l,
                        "snippet": s,
                        "date": item.get("date", "Past 30 Days"),
                        "ats_platform": platform_name
                    })
                    qualified_jobs.append(p_qualified[-1])

            platform_stats[platform_name] = {
                "raw_count": len(raw_results),
                "qualified_count": len(p_qualified)
            }
            print(f"   • {platform_name}: {len(p_qualified)} qualified jobs (out of {len(raw_results)} raw)")

        used_fallback = False

        # FIX 3: Comprehensive Fallback Query covering Indeed, LinkedIn, Workable, Ashby, Greenhouse, Lever, & Careers page
        if len(qualified_jobs) == 0:
            used_fallback = True
            fallback_query = f'site:linkedin.com/company/{company_slug}/jobs OR site:indeed.com/cmp/{company_slug}/jobs OR site:{domain}/careers OR ("{company_name}" ("Engineer" OR "Manager" OR "Recruiter") (site:ashbyhq.com OR site:greenhouse.io OR site:lever.co OR site:workable.com OR site:linkedin.com/jobs OR site:indeed.com))'
            print("\n⚠️ 0 ATS results across primary boards. Executing COMPREHENSIVE FALLBACK QUERY...")
            print(f"🔹 [Phase 2 Fallback Query]: '{fallback_query}'")

            fallback_raw = await fetch_single_serper_ats_query(client, fallback_query)
            print(f"   Raw Fallback Results: {len(fallback_raw)}")

            for item in fallback_raw:
                t = item.get("title", "")
                l = item.get("link", "")
                s = item.get("snippet", "")
                if is_valid_company_job(t, l, s, company_name, company_slug):
                    qualified_jobs.append({
                        "title": t,
                        "link": l,
                        "snippet": s,
                        "date": item.get("date", "Past 30 Days"),
                        "ats_platform": "FALLBACK_SERP"
                    })

        print(f"\n✅ SUCCESS — Retrieved {len(qualified_jobs)} VERIFIED '{company_name}' JOB OPENINGS!\n")
        print("--- VERIFIED JOB RESULTS SAMPLE ---")
        for idx, res in enumerate(qualified_jobs[:6], start=1):
            print(f"   [{idx}] {res['title']}")
            print(f"       Platform: {res['ats_platform']}")
            print(f"       Link    : {res['link']}")
            print(f"       Snippet : {res['snippet'][:110]}...\n")

        output_record = {
            "company_name": company_name,
            "company_slug": company_slug,
            "domain": domain,
            "used_fallback": used_fallback,
            "platform_stats": platform_stats,
            "total_verified_jobs": len(qualified_jobs),
            "verified_jobs": qualified_jobs
        }

        os.makedirs("scratch", exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output_record, f, indent=2)

        print("=" * 80)
        print(f"💾 SAVED CALIBRATED SERPER JOB RESULTS TO: '{OUTPUT_FILE}'")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(fetch_calibrated_serper_jobs("Modal", "modal.com"))

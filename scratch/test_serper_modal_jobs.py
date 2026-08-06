"""
Test script: Tests Google Serper API on 'Modal' (modal.com) with Senior Guidelines:
1. 30-60 Day Recency Lock (`tbs: "qdr:m2"`)
2. Negative Title Exclusions (`-junior -intern -associate -internship`)
3. Role Qualification Filter:
   - ALLOW: Mid/Senior Tech, IT, Software & Engineering roles
   - ALLOW: Talent Acquisition, Recruiter, HR, Head of People roles (Recruitment Agency Lead Signal!)
   - REJECT: Junior/Intern/Associate roles & Non-tech verticals (Finance, Medical, Legal)
4. Automatic Fallback Search if 0 qualified ATS results are returned.

Saves output to scratch/serper_modal_jobs_output.json.
"""
import os
import sys
import json
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv("backend/.env")

SERPER_API_KEY = os.getenv("SERPER_API_KEY")

OUTPUT_FILE = os.path.join("scratch", "serper_modal_jobs_output.json")

# Keywords for Senior Guidelines
EXCLUDED_KEYWORDS = ["junior", "intern", "internship", "associate", "finance", "medical", "legal", "accounting", "nurse", "physician"]
TECH_KEYWORDS = ["engineer", "developer", "architect", "systems", "ml", "ai", "security", "tech", "software", "infrastructure", "data", "product"]
TA_RECRUITMENT_KEYWORDS = ["talent acquisition", "recruiter", "recruitment", "head of people", "hr", "people partner"]


def is_qualified_role(title: str, snippet: str) -> tuple[bool, str]:
    text = (title + " " + snippet).lower()

    # 1. Check Exclusions (Junior, Intern, Associate, Non-Tech)
    for kw in ["junior", "intern", "internship", "associate"]:
        if kw in text and "solutions architect" not in text:  # preserve architect if matched
            return False, f"Excluded entry-level keyword: '{kw}'"

    # 2. Check TA / Recruitment Exception (🔥 High Value Lead Signal)
    for kw in TA_RECRUITMENT_KEYWORDS:
        if kw in text:
            return True, f"Qualified TA / Recruiting Signal: '{kw}'"

    # 3. Check Tech / Engineering / Software Roles (Mid-to-Senior+)
    for kw in TECH_KEYWORDS:
        if kw in text:
            return True, f"Qualified Tech/Engineering Role: '{kw}'"

    # 4. Filter out non-tech (Finance, Medical, Legal, etc.)
    return False, "Non-tech vertical / unmapped role category"


async def fetch_serper_jobs_senior_guidelines(company_name: str, domain: str):
    if not SERPER_API_KEY:
        print("❌ ERROR: SERPER_API_KEY not found in backend/.env")
        return

    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }

    company_slug = company_name.lower().replace(" ", "")

    # Primary ATS Query with negative keyword exclusions
    primary_query = f"site:jobs.ashbyhq.com/{company_slug} OR site:boards.greenhouse.io/{company_slug} OR site:jobs.lever.co/{company_slug} -junior -intern -associate -internship"

    print("=" * 75)
    print(f"🚀 TESTING SERPER JOB SEARCH (SENIOR GUIDELINES) FOR '{company_name}' ({domain})")
    print(f"🗓️ Recency Lock: Past 30–60 Days (tbs='qdr:m2')")
    print(f"🚫 Negative Exclusions: -junior -intern -associate -internship")
    print("=" * 75 + "\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # STEP 1: Primary ATS Call
        print(f"🔹 PRIMARY ATS QUERY: '{primary_query}'")
        primary_payload = {
            "q": primary_query,
            "num": 10,
            "tbs": "qdr:m2",  # 30-60 day recency lock (2 months)
            "autocorrect": True
        }

        resp = await client.post(url, headers=headers, json=primary_payload)
        data = resp.json() if resp.status_code == 200 else {}
        raw_organic = data.get("organic", [])

        qualified_results = []
        for item in raw_organic:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            is_qual, reason = is_qualified_role(title, snippet)
            item["qualification_status"] = "QUALIFIED" if is_qual else "DISCARDED"
            item["qualification_reason"] = reason
            if is_qual:
                qualified_results.append(item)

        used_fallback = False
        executed_query = primary_query

        if resp.status_code == 200 and len(qualified_results) > 0:
            print(f"   ✅ SUCCESS — Found {len(qualified_results)} qualified mid/senior Tech & TA job postings!\n")
        else:
            # STEP 2: Fallback Query
            used_fallback = True
            fallback_query = f'"{company_name}" ("Software Engineer" OR "Engineering Manager" OR "Recruiter" OR "Talent Acquisition") site:{domain} OR site:linkedin.com/jobs -junior -intern -associate'
            executed_query = fallback_query
            print("   ⚠️ 0 qualified ATS results. Triggering FALLBACK GOOGLE SEARCH...")
            print(f"🔹 FALLBACK QUERY: '{fallback_query}'")

            fallback_payload = {
                "q": fallback_query,
                "num": 10,
                "tbs": "qdr:m2",  # 30-60 days
                "autocorrect": True
            }

            resp = await client.post(url, headers=headers, json=fallback_payload)
            data = resp.json() if resp.status_code == 200 else {}
            raw_organic = data.get("organic", [])

            qualified_results = []
            for item in raw_organic:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                is_qual, reason = is_qualified_role(title, snippet)
                item["qualification_status"] = "QUALIFIED" if is_qual else "DISCARDED"
                item["qualification_reason"] = reason
                if is_qual:
                    qualified_results.append(item)

            print(f"   ✅ FALLBACK RESULTS — Received {len(qualified_results)} qualified search results\n")

        print("--- QUALIFIED MID/SENIOR TECH & TA JOB RESULTS ---")
        for idx, res in enumerate(qualified_results[:6], start=1):
            title = res.get("title", "")
            link = res.get("link", "")
            snippet = res.get("snippet", "")
            reason = res.get("qualification_reason", "")
            print(f"   [{idx}] {title}")
            print(f"       Reason : {reason}")
            print(f"       Link   : {link}")
            print(f"       Snippet: {snippet[:110]}...\n")

        results_summary = {
            "company_name": company_name,
            "domain": domain,
            "recency_filter": "qdr:m2 (30-60 days)",
            "senior_guidelines": {
                "excluded_titles": ["junior", "intern", "associate"],
                "allowed_categories": ["Mid/Senior Tech, IT, Software & Engineering", "Talent Acquisition, Recruiter, HR"]
            },
            "used_fallback": used_fallback,
            "executed_query": executed_query,
            "status_code": resp.status_code,
            "total_raw_results": len(raw_organic),
            "total_qualified_results": len(qualified_results),
            "qualified_organic": qualified_results
        }

        os.makedirs("scratch", exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(results_summary, f, indent=2)

        print("=" * 75)
        print(f"💾 SAVED SENIOR-GUIDELINE TEST RESULTS TO: '{OUTPUT_FILE}'")
        print("=" * 75 + "\n")


if __name__ == "__main__":
    asyncio.run(fetch_serper_jobs_senior_guidelines("Modal", "modal.com"))

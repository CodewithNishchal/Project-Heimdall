import os
import sys
import requests
import json
import copy
from sqlalchemy.orm.attributes import flag_modified
from dotenv import load_dotenv

# Load environment variables from backend/.env
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join("backend", ".env"), override=True)

from backend.database import SessionLocal
from backend.models import LeadSnapshot

THEIRSTACK_API_URL = "https://api.theirstack.com/v1/jobs/search"
THEIRSTACK_API_KEY = os.getenv("THEIRSTACK_API_KEY")

def fetch_theirstack_single_job(domain: str, company_name: str):
    if not THEIRSTACK_API_KEY:
        print("❌ THEIRSTACK_API_KEY not configured in backend/.env!")
        return None

    headers = {
        "Authorization": f"Bearer {THEIRSTACK_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    slug = domain.split(".")[0].lower() if domain else company_name.lower().replace(" ", "")
    linkedin_url = f"https://www.linkedin.com/company/{slug}"

    payload = {
        "company_domain_or": [domain] if domain else [],
        "posted_at_max_age_days": 90,
        "limit": 1,
        "page": 0
    }
    if linkedin_url:
        payload["company_linkedin_url_or"] = [linkedin_url]

    try:
        resp = requests.post(THEIRSTACK_API_URL, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            jobs = data.get("data", [])
            if isinstance(jobs, list) and len(jobs) > 0:
                j = jobs[0]
                company_info = j.get("company_object", {})
                qualified_job = {
                    "title": j.get("job_title", "Position Open"),
                    "link": j.get("url") or j.get("source_url") or f"https://www.linkedin.com/company/{slug}/jobs",
                    "snippet": (j.get("description") or "")[:250].replace("\n", " "),
                    "date": j.get("date_posted", "Recent"),
                    "ats_platform": "TheirStack API (LinkedIn)",
                    "seniority": j.get("seniority", "mid_level"),
                    "location": j.get("location", ""),
                    "technologies": company_info.get("technology_names", [])
                }
                return {
                    "total_results": 1,
                    "used_fallback": False,
                    "source": "theirstack",
                    "qualified_jobs": [qualified_job]
                }
    except Exception as e:
        print(f"⚠️ Exception fetching TheirStack job for {company_name}: {e}")

    return None

def clean_and_update_db_jobs():
    db = SessionLocal()
    try:
        leads = db.query(LeadSnapshot).all()
        print(f"======================================================================")
        print(f"🧹 BACKFILL & JOB URL CLEANUP FOR {len(leads)} LEADS IN DATABASE")
        print(f"======================================================================\n")

        updated_count = 0
        cleared_count = 0

        for lead in leads:
            company_name = lead.company_name or "Unknown Company"
            domain = lead.domain or ""
            print(f"🏢 Processing Lead: '{company_name}' ({domain})...")

            # Fetch 1 fresh job from TheirStack
            theirstack_res = fetch_theirstack_single_job(domain, company_name)

            if theirstack_res and len(theirstack_res.get("qualified_jobs", [])) > 0:
                job_title = theirstack_res["qualified_jobs"][0]["title"]
                job_url = theirstack_res["qualified_jobs"][0]["link"]
                print(f"   ✅ Replaced job openings with TheirStack verified job:")
                print(f"      • Title: {job_title}")
                print(f"      • URL: {job_url}")

                lead.job_openings = theirstack_res
                if isinstance(lead.full_payload, dict):
                    fp = copy.deepcopy(lead.full_payload)
                    fp["job_openings"] = theirstack_res
                    lead.full_payload = fp
                    flag_modified(lead, "full_payload")
                updated_count += 1
            else:
                print(f"   ⚠️ No TheirStack job found. Clearing outdated/wrong job URLs...")
                empty_payload = {"total_results": 0, "used_fallback": False, "qualified_jobs": []}
                lead.job_openings = empty_payload
                if isinstance(lead.full_payload, dict):
                    fp = copy.deepcopy(lead.full_payload)
                    fp["job_openings"] = empty_payload
                    lead.full_payload = fp
                    flag_modified(lead, "full_payload")
                cleared_count += 1

            print("-" * 70)

        db.commit()
        print(f"\n🎉 BACKFILL COMPLETED SUCCESSFULLY!")
        print(f"   • Updated with verified TheirStack jobs: {updated_count}")
        print(f"   • Cleared wrong/outdated job entries: {cleared_count}")

    finally:
        db.close()

if __name__ == "__main__":
    clean_and_update_db_jobs()

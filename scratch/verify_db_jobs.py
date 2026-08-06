import os
import sys
import json
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join("backend", ".env"), override=True)

from backend.database import SessionLocal
from backend.models import LeadSnapshot

def verify_db_jobs():
    db = SessionLocal()
    try:
        leads = db.query(LeadSnapshot).all()
        print("======================================================================")
        print(f"📊 DATABASE JOB DATA VERIFICATION INSPECTOR ({len(leads)} TOTAL LEADS)")
        print("======================================================================\n")

        with_jobs = 0
        without_jobs = 0

        for idx, lead in enumerate(leads, 1):
            c_name = lead.company_name or "Unknown"
            dom = lead.domain or ""
            job_data = lead.job_openings or {}
            
            # Extract jobs list from dictionary or array
            jobs_list = []
            source = "None"
            if isinstance(job_data, dict):
                jobs_list = job_data.get("qualified_jobs") or job_data.get("verified_jobs") or []
                source = job_data.get("source", "serper/ats")
            elif isinstance(job_data, list):
                jobs_list = job_data
                source = "array"

            count = len(jobs_list)

            print(f"[{idx:02d}] {c_name} ({dom})")
            print(f"     • Jobs Count: {count} | Source: {source}")

            if count > 0:
                with_jobs += 1
                for j_idx, job in enumerate(jobs_list, 1):
                    title = job.get("title") or job.get("job_title") or "No Title"
                    link = job.get("link") or job.get("url") or job.get("source_url") or "No Link"
                    ats = job.get("ats_platform", "N/A")
                    print(f"     • Job #{j_idx}: {title}")
                    print(f"       🔗 URL: {link}")
                    print(f"       🏷️ Platform: {ats}")
            else:
                without_jobs += 1
                print(f"     • Status: 🧹 Cleared (No active jobs found)")
            print("-" * 70)

        print(f"\n📈 VERIFICATION SUMMARY:")
        print(f"   • Total Leads in Database: {len(leads)}")
        print(f"   • Leads with Active Verified Jobs: {with_jobs}")
        print(f"   • Leads Cleaned / 0 Jobs: {without_jobs}")

    finally:
        db.close()

if __name__ == "__main__":
    verify_db_jobs()

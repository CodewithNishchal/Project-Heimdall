import os
import sys
import json
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join("backend", ".env"), override=True)

from backend.database import SessionLocal
from backend.models import LeadSnapshot

def inspect_insights():
    db = SessionLocal()
    try:
        leads = db.query(LeadSnapshot).all()
        print(f"Total leads: {len(leads)}")
        for lead in leads:
            print("="*60)
            print(f"Company: {lead.company_name} ({lead.domain}) | ID: {lead.company_linkedin_id}")
            insights = lead.company_insights if isinstance(lead.company_insights, dict) else {}
            new_hires = insights.get("new_hires")
            senior_trend = insights.get("senior_hiring_trend")
            print(f"  new_hires: {json.dumps(new_hires)}")
            print(f"  senior_hiring_trend: {json.dumps(senior_trend)}")
            jobs = lead.job_openings if isinstance(lead.job_openings, dict) else {}
            jobs_list = jobs.get("verified_jobs") or jobs.get("qualified_jobs") or []
            print(f"  jobs_count: {len(jobs_list)}")
    finally:
        db.close()

if __name__ == "__main__":
    inspect_insights()

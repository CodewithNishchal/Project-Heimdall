import sys
import os
import json

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal
from backend.models import LeadSnapshot

def main():
    print("🚀 Cleaning up fake jobs for ZapScale, Sei, and Karini AI in Database...")
    targets = ["zapscale", "sei", "karini"]
    db = SessionLocal()
    try:
        clean_job_payload = {
            "total_results": 0,
            "used_fallback": False,
            "source": "apify_career_scraper",
            "qualified_jobs": []
        }

        for target in targets:
            leads = db.query(LeadSnapshot).filter(
                (LeadSnapshot.domain.ilike(f"%{target}%")) |
                (LeadSnapshot.company_name.ilike(f"%{target}%"))
            ).all()

            if not leads:
                print(f"⚠️ No database record found matching '{target}'.")
                continue

            for lead in leads:
                lead.job_openings = clean_job_payload
                if isinstance(lead.full_payload, dict):
                    lead.full_payload["job_openings"] = clean_job_payload
                print(f"  ✅ Cleared jobs for '{lead.company_name}' ({lead.domain}) [ID: {lead.id}]")

        db.commit()
        print("\n=========================================================================")
        print("🎉 Successfully cleaned up jobs for ZapScale, Sei, and Karini AI in DB!")
        print("=========================================================================")

    except Exception as e:
        print(f"❌ Error updating database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()

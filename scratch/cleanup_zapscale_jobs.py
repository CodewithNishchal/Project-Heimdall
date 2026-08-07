import sys
import os
import json

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal
from backend.models import LeadSnapshot

def main():
    print("🚀 Cleaning up fake jobs for ZapScale in Database...")
    db = SessionLocal()
    try:
        lead = db.query(LeadSnapshot).filter(
            (LeadSnapshot.domain.ilike("%zapscale%")) |
            (LeadSnapshot.company_name.ilike("%zapscale%"))
        ).first()

        if not lead:
            print("⚠️ ZapScale record not found in database snapshot table.")
            return

        print(f"✅ Found Lead: '{lead.company_name}' ({lead.domain}) [ID: {lead.id}]")

        clean_job_payload = {
            "total_results": 0,
            "used_fallback": False,
            "source": "apify_career_scraper",
            "qualified_jobs": []
        }

        lead.job_openings = clean_job_payload
        if isinstance(lead.full_payload, dict):
            lead.full_payload["job_openings"] = clean_job_payload

        db.commit()
        print("✅ Successfully removed fake jobs ('Support' & 'Privacy Policy') from ZapScale!")

    except Exception as e:
        print(f"❌ Error updating database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()

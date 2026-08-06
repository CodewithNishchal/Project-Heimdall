import os
import sys
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend.models import LeadSnapshot

def clean_db_revenues():
    db = SessionLocal()
    try:
        leads = db.query(LeadSnapshot).all()
        updated_count = 0
        
        for lead in leads:
            rev = (lead.annual_revenue or "").strip()
            if rev and (len(rev) > 20 or not any(c.isdigit() for c in rev)):
                print(f"🧹 Cleaning long/non-numeric revenue for '{lead.company_name}': '{rev[:30]}...' -> 'N/A'")
                lead.annual_revenue = "N/A"
                if isinstance(lead.full_payload, dict):
                    lead.full_payload["annual_revenue"] = "N/A"
                updated_count += 1

        db.commit()
        print(f"\n🎉 Cleaned {updated_count} lead revenue entries in database!")
    finally:
        db.close()

if __name__ == "__main__":
    clean_db_revenues()

"""Quick check: how many leads are in the database right now?"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal
from backend.models import LeadSnapshot

db = SessionLocal()
try:
    count = db.query(LeadSnapshot).count()
    print(f"\n📊 Total leads in database: {count}\n")
    if count > 0:
        leads = db.query(LeadSnapshot).all()
        for lead in leads:
            print(f"  • {lead.company_name} | {lead.domain} | Score: {lead.intent_score} | Tier: {lead.tier}")
    else:
        print("  ⚠️  Database is empty. No pipeline run has successfully persisted leads yet.")
        print("  → The _persist_lead fix was applied AFTER your last pipeline run.")
        print("  → Run the pipeline again from the website to populate leads.\n")
finally:
    db.close()

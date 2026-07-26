"""Check if full_payload is populated for existing leads."""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal
from backend.models import LeadSnapshot

db = SessionLocal()
try:
    leads = db.query(LeadSnapshot).all()
    print(f"\n📊 Total leads: {len(leads)}\n")
    for lead in leads:
        has_payload = lead.full_payload is not None
        payload_size = len(str(lead.full_payload)) if has_payload else 0
        print(f"  {'✅' if has_payload else '❌'} {lead.company_name:35s} | full_payload: {'Present (' + str(payload_size) + ' chars)' if has_payload else 'NULL ← SKIPPED BY API'}")
finally:
    db.close()

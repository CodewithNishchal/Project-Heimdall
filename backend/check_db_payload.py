import json
from backend.database import SessionLocal
from backend.models import LeadSnapshot

db = SessionLocal()
leads = db.query(LeadSnapshot).all()
for lead in leads:
    if lead.company_name == "Just Ingredients" or lead.company_name == "Nitra":
        print(f"--- {lead.company_name} ---")
        print(json.dumps(lead.full_payload, indent=2))
db.close()

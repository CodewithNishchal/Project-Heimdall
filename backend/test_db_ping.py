import json
from backend.database import SessionLocal
from backend.models import LeadSnapshot

def dump_leads_info():
    db = SessionLocal()
    try:
        leads = db.query(LeadSnapshot).all()
        print(f"Total leads in DB: {len(leads)}")
        for lead in leads:
            print("=" * 60)
            print(f"ID: {lead.id}")
            print(f"Company: {lead.company_name}")
            print(f"Domain: {lead.domain}")
            print(f"Top-level Industry column: {lead.industry}")
            
            if lead.full_payload:
                payload = dict(lead.full_payload)
                print(f"Payload Industry field: {payload.get('industry')}")
                print("Payload Top-level Keys:", list(payload.keys()))
                print("Full Payload Preview:")
                print(json.dumps(payload, indent=2))
            else:
                print("No full_payload found!")
    finally:
        db.close()

if __name__ == "__main__":
    dump_leads_info()

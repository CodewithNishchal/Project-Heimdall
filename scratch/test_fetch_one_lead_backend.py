import sys
import os
import json

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal
from backend.models import LeadSnapshot

def main():
    print("🚀 Fetching 1 Lead Snapshot JSON from Backend Database...")
    db = SessionLocal()
    try:
        # Fetch the most recent lead snapshot
        lead = db.query(LeadSnapshot).order_by(LeadSnapshot.id.desc()).first()
        
        if not lead:
            print("⚠️ No lead snapshots found in the database.")
            return

        print(f"\n✅ Found Lead Record: '{lead.company_name}' ({lead.domain}) [ID: {lead.id}]")
        
        # Safely convert SQLAlchemy LeadSnapshot model to dictionary
        lead_dict = {
            "id": getattr(lead, "id", None),
            "company_name": getattr(lead, "company_name", None),
            "domain": getattr(lead, "domain", None),
            "intent_score": getattr(lead, "intent_score", None),
            "tier": getattr(lead, "tier", None),
            "company_segment": getattr(lead, "company_segment", None),
            "why_now": getattr(lead, "why_now", None),
            "signal_tags": getattr(lead, "signal_tags", None),
            "employee_count": getattr(lead, "employee_count", None),
            "company_insights": getattr(lead, "company_insights", None),
            "job_openings": getattr(lead, "job_openings", None),
            "full_payload": getattr(lead, "full_payload", None),
            "last_updated": lead.last_updated.isoformat() if getattr(lead, "last_updated", None) else None
        }

        print("\n=========================================================================")
        print(f"📦 BACKEND DATABASE JSON FOR '{lead.company_name}':")
        print("=========================================================================")
        print(json.dumps(lead_dict, indent=2, default=str))

    except Exception as e:
        print(f"❌ Error querying backend database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()

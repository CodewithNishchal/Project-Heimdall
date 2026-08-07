import sys
import os
import json

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal
from backend.models import LeadSnapshot

def main():
    print("🚀 Fetching COMPLETE Backend Database Object for Karini AI...")
    db = SessionLocal()
    try:
        lead = db.query(LeadSnapshot).filter(
            (LeadSnapshot.domain.ilike("%karini%")) |
            (LeadSnapshot.company_name.ilike("%karini%"))
        ).first()

        if not lead:
            print("⚠️ Karini AI record NOT found in current database snapshot table!")
            return

        print(f"\n=========================================================================")
        print(f"📦 FULL BACKEND RECORD FOR '{lead.company_name}' ({lead.domain})")
        print("=========================================================================")
        
        full_dict = {
            "id": lead.id,
            "domain": lead.domain,
            "company_name": lead.company_name,
            "company_segment": lead.company_segment,
            "industry": lead.industry,
            "employee_count": lead.employee_count,
            "funding_stage": lead.funding_stage,
            "annual_revenue": lead.annual_revenue,
            "intent_score": lead.intent_score,
            "signal_freshness": lead.signal_freshness,
            "tier": lead.tier,
            "icp_fit": lead.icp_fit,
            "badge": lead.badge,
            "why_now": lead.why_now,
            "signal_tags": lead.signal_tags,
            "ai_verdict": lead.ai_verdict,
            "company_linkedin_id": lead.company_linkedin_id,
            "company_insights": lead.company_insights,
            "job_openings": lead.job_openings,
            "full_payload": lead.full_payload,
            "last_updated": lead.last_updated.isoformat() if lead.last_updated else None
        }

        print(json.dumps(full_dict, indent=2, default=str))

    except Exception as e:
        print(f"❌ Error querying backend database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()

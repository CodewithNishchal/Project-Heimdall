import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join("backend", ".env"), override=True)

from backend.database import SessionLocal
from backend.models import LeadSnapshot

def lead_to_dict(lead: LeadSnapshot) -> dict:
    """Converts a LeadSnapshot DB record into a complete JSON dictionary."""
    record = {}
    for column in lead.__table__.columns:
        val = getattr(lead, column.name)
        if isinstance(val, datetime):
            val = val.isoformat()
        record[column.name] = val

    # Ensure full_payload is unpacked if available
    if isinstance(lead.full_payload, dict):
        record["full_payload"] = lead.full_payload

    return record

def fetch_company_db_json(query: str):
    db = SessionLocal()
    query_clean = query.strip().lower()

    print("======================================================================")
    print(f"📦 FETCHING DATABASE LEAD RECORD FOR QUERY: '{query}'")
    print("======================================================================\n")

    try:
        # Match by ID, exact domain, domain contains query, or company_name contains query
        leads = db.query(LeadSnapshot).filter(
            (LeadSnapshot.id == query) |
            (LeadSnapshot.domain.ilike(f"%{query_clean}%")) |
            (LeadSnapshot.company_name.ilike(f"%{query_clean}%"))
        ).all()

        if not leads:
            print(f"❌ No matching lead record found in database for query: '{query}'")
            
            # List available companies in DB for user reference
            all_leads = db.query(LeadSnapshot).all()
            print("\n📋 Available companies in database:")
            for l in all_leads:
                print(f"   - {l.company_name} ({l.domain}) [ID: {l.id}]")
            return

        print(f"✅ Found {len(leads)} matching record(s) in database:\n")

        for lead in leads:
            company_slug = (lead.domain or lead.company_name or lead.id).replace(".", "_").replace(" ", "_").lower()
            output_file = os.path.join("scratch", f"db_lead_{company_slug}.json")
            
            lead_dict = lead_to_dict(lead)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(lead_dict, f, indent=2)

            print(f"🏢 Company: {lead.company_name} ({lead.domain})")
            print(f"   - DB Lead ID     : {lead.id}")
            print(f"   - Intent Score   : {lead.intent_score} | Tier: {lead.tier}")
            print(f"   - Employee Count : {lead.employee_count}")
            print(f"   - Annual Revenue : {lead.annual_revenue or 'N/A'}")
            print(f"   - LinkedIn ID    : {lead.company_linkedin_id or 'N/A'}")
            print(f"   - Insights Present: {bool(lead.company_insights)}")
            print(f"   - Jobs Present    : {bool(lead.job_openings)}")
            print(f"   - Last Updated   : {lead.last_updated}")
            print(f"📁 Full DB JSON saved to: {output_file}\n")

    finally:
        db.close()

if __name__ == "__main__":
    search_query = sys.argv[1] if len(sys.argv) > 1 else "rutter"
    fetch_company_db_json(search_query)

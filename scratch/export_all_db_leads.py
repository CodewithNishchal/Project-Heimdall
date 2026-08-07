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

def export_all_db_leads():
    print("======================================================================")
    print("📦 EXPORTING ALL BACKEND LEAD RECORDS FROM DATABASE")
    print("======================================================================\n")

    db = SessionLocal()
    output_file = os.path.join("scratch", "all_backend_leads_dump.json")

    try:
        leads = db.query(LeadSnapshot).all()
        print(f"📋 Found {len(leads)} total lead records in database.\n")

        all_leads_data = []

        for idx, lead in enumerate(leads, 1):
            record = lead_to_dict(lead)
            all_leads_data.append(record)

            c_name = lead.company_name or "Unknown"
            dom = lead.domain or "N/A"
            score = lead.intent_score
            tier = lead.tier
            has_insights = bool(lead.company_insights)
            has_jobs = bool(lead.job_openings)

            print(f"[{idx:02d}] 🏢 {c_name} ({dom})")
            print(f"     • Lead ID      : {lead.id}")
            print(f"     • Intent Score : {score} | Tier: {tier}")
            print(f"     • Employees    : {lead.employee_count} | Revenue: {lead.annual_revenue or 'N/A'}")
            print(f"     • Has Insights : {has_insights} | Has Jobs: {has_jobs}")
            print("-" * 70)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_leads_data, f, indent=2)

        print(f"\n✅ SUCCESS! All {len(all_leads_data)} backend company records saved to:")
        print(f"📁 {output_file}\n")

    finally:
        db.close()

if __name__ == "__main__":
    export_all_db_leads()

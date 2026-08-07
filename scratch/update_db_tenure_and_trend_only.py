import os
import sys
import json
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join("backend", ".env"), override=True)

from backend.database import SessionLocal
from backend.models import LeadSnapshot
from sqlalchemy.orm.attributes import flag_modified

LOCAL_APIFY_FILE = os.path.join("scratch", "all_companies_apify_insights.json")

def update_tenure_and_hiring_trend_only():
    print("======================================================================")
    print("🛠️ UPDATING ONLY MEDIAN TENURE & HIRING TREND IN DATABASE")
    print("======================================================================\n")

    # Step 1: Check database schema structure
    print("🔍 DB SCHEMA CHECK:")
    print("   • Table: 'lead_snapshots'")
    print("   • Column: 'company_insights' (JSON column storing median_employee_tenure & new_hires/hiring_trend)")
    print("   • Column: 'full_payload' (JSON column mirroring company_insights)\n")

    if not os.path.exists(LOCAL_APIFY_FILE):
        print(f"❌ ERROR: '{LOCAL_APIFY_FILE}' not found! Run fetch_all_apify_insights_local.py first.")
        return

    with open(LOCAL_APIFY_FILE, "r", encoding="utf-8") as f:
        apify_records = json.load(f)

    db = SessionLocal()

    try:
        leads = db.query(LeadSnapshot).all()
        print(f"📋 Found {len(leads)} lead snapshots in database.\n")

        updated_count = 0

        for idx, lead in enumerate(leads, 1):
            c_name = lead.company_name or "Unknown"
            matching_apify = apify_records.get(c_name, {})

            if not matching_apify and isinstance(apify_records, dict):
                # Try fuzzy key match
                for k, v in apify_records.items():
                    if k.lower() in c_name.lower() or c_name.lower() in k.lower():
                        matching_apify = v
                        break

            raw_payload = matching_apify.get("payload", [])
            data_body = {}
            if isinstance(raw_payload, list) and len(raw_payload) > 0:
                data_body = raw_payload[0].get("data", {})
            elif isinstance(raw_payload, dict):
                data_body = raw_payload.get("data", {})

            # Extract ONLY tenure and new_hires / hiring_trend
            tenure_val = data_body.get("median_employee_tenure")
            new_hires_val = data_body.get("new_hires")

            if not isinstance(lead.company_insights, dict):
                lead.company_insights = {}

            # Create clean copy of existing company_insights
            ci = dict(lead.company_insights)

            # Preserve existing firmographic total_employees & headcount_by_function untouched
            # ONLY update median_employee_tenure and new_hires / senior_hiring_trend!
            if tenure_val is not None:
                ci["median_employee_tenure"] = tenure_val
            elif "median_employee_tenure" not in ci:
                ci["median_employee_tenure"] = None

            if new_hires_val is not None:
                ci["new_hires"] = new_hires_val

            lead.company_insights = ci
            flag_modified(lead, "company_insights")

            # Mirror ONLY these two fields in full_payload["company_insights"]
            if isinstance(lead.full_payload, dict):
                fp = dict(lead.full_payload)
                if "company_insights" not in fp or not isinstance(fp["company_insights"], dict):
                    fp["company_insights"] = {}

                if tenure_val is not None:
                    fp["company_insights"]["median_employee_tenure"] = tenure_val
                if new_hires_val is not None:
                    fp["company_insights"]["new_hires"] = new_hires_val

                lead.full_payload = fp
                flag_modified(lead, "full_payload")

            updated_count += 1
            hires_cnt = len(new_hires_val) if isinstance(new_hires_val, list) else 0
            print(f"[{idx:02d}] 🏢 {c_name:28s} | Tenure: {str(tenure_val):6s} | Monthly New Hires: {hires_cnt}")

        db.commit()
        print("\n" + "=" * 70)
        print(f"💾 SUCCESS! Updated ONLY tenure & hiring trend for {updated_count} database leads.")
        print("=" * 70 + "\n")

    finally:
        db.close()

if __name__ == "__main__":
    update_tenure_and_hiring_trend_only()

import os
import sys
import json
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join("backend", ".env"), override=True)

from backend.database import SessionLocal
from backend.models import LeadSnapshot
from sqlalchemy.orm.attributes import flag_modified

ALL_INSIGHTS_FILE = os.path.join("scratch", "all_companies_apify_insights.json")

def enrich_pending_leads():
    print("======================================================================")
    print("⚡ ENRICHING BACKEND DATABASE FOR 8 PENDING COMPANIES (OFFLINE)")
    print("======================================================================\n")

    if not os.path.exists(ALL_INSIGHTS_FILE):
        print(f"❌ ERROR: File '{ALL_INSIGHTS_FILE}' not found!")
        return

    with open(ALL_INSIGHTS_FILE, "r", encoding="utf-8") as f:
        all_insights = json.load(f)

    db = SessionLocal()
    try:
        leads = db.query(LeadSnapshot).all()
        enriched_count = 0

        target_companies = [
            "Valence", "Jigx", "Netstock", "Remark",
            "Azion", "SurePoint Technologies", "Baxter Clewis Cybersecurity", "AI Automation"
        ]

        for lead in leads:
            c_name = lead.company_name or "Unknown"

            # Check if lead matches target company list
            matched_key = None
            for t in target_companies:
                if t.lower() in c_name.lower() or c_name.lower() in t.lower():
                    matched_key = t
                    break

            if not matched_key:
                continue

            ap_entry = all_insights.get(matched_key, {})
            if not ap_entry:
                for k, v in all_insights.items():
                    if k.lower() in c_name.lower() or c_name.lower() in k.lower():
                        ap_entry = v
                        break

            raw_p = ap_entry.get("payload", [])
            data_b = {}
            if isinstance(raw_p, list) and len(raw_p) > 0:
                data_b = raw_p[0].get("data", {})
            elif isinstance(raw_p, dict):
                data_b = raw_p.get("data", {})

            if not data_b:
                print(f"⚠️ No payload data found for {c_name}. Skipping.")
                continue

            # Extract fields from Apify payload
            tenure_val = data_b.get("median_employee_tenure")
            new_hires_val = data_b.get("new_hires", [])
            depts_val = data_b.get("headcount_by_function", {})
            growth_val = data_b.get("headcount_growth", {})
            h_month_val = data_b.get("headcount_by_month", [])

            if not isinstance(lead.company_insights, dict):
                lead.company_insights = {}

            ci = dict(lead.company_insights)

            # Update insights fields
            if tenure_val is not None:
                ci["median_employee_tenure"] = tenure_val
            if new_hires_val:
                ci["new_hires"] = new_hires_val
            if depts_val:
                ci["headcount_by_function"] = depts_val
            if growth_val:
                ci["headcount_growth"] = growth_val
            if h_month_val and len(h_month_val) > 0:
                ci["headcount_by_month"] = h_month_val
                latest_count = h_month_val[-1].get("employee_count")
                if latest_count and isinstance(latest_count, (int, float)):
                    ci["total_employees"] = int(latest_count)
                    lead.employee_count = int(latest_count)

            lead.company_insights = ci
            flag_modified(lead, "company_insights")

            # Mirror to full_payload
            if isinstance(lead.full_payload, dict):
                fp = dict(lead.full_payload)
                if "company_insights" not in fp or not isinstance(fp["company_insights"], dict):
                    fp["company_insights"] = {}
                fp["company_insights"].update(ci)
                if lead.employee_count is not None:
                    fp["employee_count"] = lead.employee_count
                lead.full_payload = fp
                flag_modified(lead, "full_payload")

            enriched_count += 1
            print(f"✅ Enriched {c_name:30s} | Tenure: {str(tenure_val):5s} | New Hires: {len(new_hires_val)} records | Depts: {len(depts_val)}")

        db.commit()
        print("\n" + "=" * 70)
        print(f"💾 SUCCESS! Enriched and committed backend database for {enriched_count} companies.")
        print("=" * 70 + "\n")

    finally:
        db.close()

if __name__ == "__main__":
    enrich_pending_leads()

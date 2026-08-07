import os
import sys
import json
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join("backend", ".env"), override=True)

from backend.database import SessionLocal
from backend.models import LeadSnapshot

LOCAL_APIFY_FILE = os.path.join("scratch", "all_companies_apify_insights.json")

def compare_valence():
    print("======================================================================")
    print("🔍 HONEST COMPARISON: APIFY RAW VS BACKEND DB FOR VALENCE")
    print("======================================================================\n")

    # Load Apify Raw
    apify_raw = {}
    if os.path.exists(LOCAL_APIFY_FILE):
        with open(LOCAL_APIFY_FILE, "r", encoding="utf-8") as f:
            all_ap = json.load(f)
            apify_raw = all_ap.get("Valence", {})

    apify_payload = {}
    raw_p = apify_raw.get("payload", [])
    if isinstance(raw_p, list) and len(raw_p) > 0:
        apify_payload = raw_p[0].get("data", {})
    elif isinstance(raw_p, dict):
        apify_payload = raw_p.get("data", {})

    # Load Database Record
    db = SessionLocal()
    db_lead = None
    try:
        db_lead = db.query(LeadSnapshot).filter(
            (LeadSnapshot.domain == "getvalence.com") | (LeadSnapshot.company_name == "Valence")
        ).first()

        print(f"🏢 Company: {db_lead.company_name} ({db_lead.domain}) | DB ID: {db_lead.id}")
        print(f"🔗 Stored LinkedIn ID: {db_lead.company_linkedin_id}")

        ci = db_lead.company_insights if isinstance(db_lead.company_insights, dict) else {}
        fp = db_lead.full_payload.get("company_insights", {}) if isinstance(db_lead.full_payload, dict) else {}

        print("\n--- 1. MEDIAN EMPLOYEE TENURE ---")
        print(f"   • Apify Raw Value      : {apify_payload.get('median_employee_tenure')} years")
        print(f"   • Database ci field    : {ci.get('median_employee_tenure')}")
        print(f"   • Database fp field    : {fp.get('median_employee_tenure')}")

        print("\n--- 2. TOTAL EMPLOYEES ---")
        print(f"   • Apify Raw Value      : {apify_payload.get('total_employees')}")
        print(f"   • Lead employee_count  : {db_lead.employee_count}")
        print(f"   • Database ci field    : {ci.get('total_employees')}")

        print("\n--- 3. NEW HIRES / HIRING TREND ---")
        ap_hires = apify_payload.get("new_hires", [])
        ci_hires = ci.get("new_hires", [])
        ci_trend = ci.get("senior_hiring_trend", [])

        print(f"   • Apify Raw New Hires ({len(ap_hires)} records) : {json.dumps(ap_hires)}")
        print(f"   • Database ci.new_hires ({len(ci_hires)} records): {json.dumps(ci_hires)}")
        print(f"   • Database ci.senior_hiring_trend     : {json.dumps(ci_trend)}")

        print("\n--- 4. HEADCOUNT BY FUNCTION (DEPARTMENTS) ---")
        print(f"   • Apify Raw Functions   : {json.dumps(apify_payload.get('headcount_by_function', {}))}")
        print(f"   • Database ci Functions: {json.dumps(ci.get('headcount_by_function', {}))}")

        print("\n" + "=" * 70)

    finally:
        db.close()

if __name__ == "__main__":
    compare_valence()

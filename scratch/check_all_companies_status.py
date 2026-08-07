import os
import sys
import json
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join("backend", ".env"), override=True)

from backend.database import SessionLocal
from backend.models import LeadSnapshot

LOCAL_APIFY_FILE = os.path.join("scratch", "all_companies_apify_insights.json")

def check_all_status():
    print("======================================================================")
    print("📋 STATUS CHECK FOR ALL 17 LEADS: APIFY FETCHED VS BACKEND DB")
    print("======================================================================\n")

    apify_all = {}
    if os.path.exists(LOCAL_APIFY_FILE):
        with open(LOCAL_APIFY_FILE, "r", encoding="utf-8") as f:
            apify_all = json.load(f)

    db = SessionLocal()
    try:
        leads = db.query(LeadSnapshot).all()
        print(f"{'Company Name':<28} | {'Apify Tenure':<12} | {'DB Tenure':<10} | {'Apify Hires':<11} | {'DB Hires':<10} | Status")
        print("-" * 105)

        for lead in leads:
            c_name = lead.company_name or "Unknown"
            ci = lead.company_insights if isinstance(lead.company_insights, dict) else {}

            ap_entry = apify_all.get(c_name, {})
            if not ap_entry and isinstance(apify_all, dict):
                for k, v in apify_all.items():
                    if k.lower() in c_name.lower() or c_name.lower() in k.lower():
                        ap_entry = v
                        break

            raw_p = ap_entry.get("payload", [])
            data_b = {}
            if isinstance(raw_p, list) and len(raw_p) > 0:
                data_b = raw_p[0].get("data", {})
            elif isinstance(raw_p, dict):
                data_b = raw_p.get("data", {})

            ap_tenure = data_b.get("median_employee_tenure", "N/A")
            ap_hires = len(data_b.get("new_hires", [])) if isinstance(data_b.get("new_hires"), list) else 0

            db_tenure = ci.get("median_employee_tenure", "N/A")
            db_hires = len(ci.get("new_hires", [])) if isinstance(ci.get("new_hires"), list) else 0

            is_synced = (str(ap_tenure) == str(db_tenure)) and (ap_hires == db_hires)
            status = "✅ SYNCED TO DB" if is_synced else "⏳ PENDING DB COMMIT"

            print(f"{c_name:<28} | {str(ap_tenure):<12} | {str(db_tenure):<10} | {ap_hires:<11} | {db_hires:<10} | {status}")

    finally:
        db.close()

if __name__ == "__main__":
    check_all_status()

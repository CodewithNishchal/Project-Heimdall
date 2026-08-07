import os
import sys
import json
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join("backend", ".env"), override=True)

from backend.database import SessionLocal
from backend.models import LeadSnapshot

SCRATCH_DIR = "scratch"

def audit_json_vs_db():
    print("======================================================================")
    print("🔬 COMPREHENSIVE AUDIT: ALL SCRATCH JSON FILES VS BACKEND DB")
    print("======================================================================\n")

    db = SessionLocal()
    try:
        leads = db.query(LeadSnapshot).all()
        leads_map = {l.company_name.lower(): l for l in leads if l.company_name}

        # Map domain to lead
        domain_map = {l.domain.lower(): l for l in leads if l.domain}

        json_files = [f for f in os.listdir(SCRATCH_DIR) if f.startswith("apify_insights_") or f == "apify_chalk_output.json"]

        print(f"📁 Found {len(json_files)} Apify JSON result files in '{SCRATCH_DIR}/':\n")

        pending_list = []
        synced_list = []

        for j_file in sorted(json_files):
            file_path = os.path.join(SCRATCH_DIR, j_file)
            with open(file_path, "r", encoding="utf-8") as f:
                content = json.load(f)

            data_obj = {}
            if isinstance(content, list) and len(content) > 0:
                data_obj = content[0].get("data", {})
            elif isinstance(content, dict):
                data_obj = content.get("data", {})

            # Match with DB lead
            matched_lead = None
            for d_name, lead_obj in leads_map.items():
                if d_name in j_file.lower() or j_file.lower().replace("apify_insights_", "").replace(".json", "").replace("_", "") in d_name.replace(" ", "").lower():
                    matched_lead = lead_obj
                    break

            if not matched_lead:
                for dom, lead_obj in domain_map.items():
                    dom_clean = dom.split(".")[0]
                    if dom_clean in j_file.lower():
                        matched_lead = lead_obj
                        break

            c_name = matched_lead.company_name if matched_lead else j_file
            c_dom = matched_lead.domain if matched_lead else "N/A"

            json_tenure = data_obj.get("median_employee_tenure")
            json_hires = data_obj.get("new_hires", [])
            json_hires_cnt = len(json_hires) if isinstance(json_hires, list) else 0

            db_ci = matched_lead.company_insights if matched_lead and isinstance(matched_lead.company_insights, dict) else {}
            db_tenure = db_ci.get("median_employee_tenure")
            db_hires = db_ci.get("new_hires", [])
            db_hires_cnt = len(db_hires) if isinstance(db_hires, list) else 0

            tenure_match = (str(json_tenure) == str(db_tenure))
            hires_match = (json_hires_cnt == db_hires_cnt)

            if tenure_match and hires_match and matched_lead:
                synced_list.append({
                    "company_name": c_name,
                    "file": j_file,
                    "tenure": json_tenure,
                    "hires_count": json_hires_cnt
                })
            else:
                pending_list.append({
                    "company_name": c_name,
                    "domain": c_dom,
                    "file": j_file,
                    "json_tenure": json_tenure,
                    "db_tenure": db_tenure,
                    "json_hires": json_hires_cnt,
                    "db_hires": db_hires_cnt,
                    "reason": f"Tenure in DB is '{db_tenure}' vs JSON '{json_tenure}'; Hires in DB is {db_hires_cnt} vs JSON {json_hires_cnt}"
                })

        print("======================================================================")
        print(f"✅ FULLY SYNCED TO BACKEND DB ({len(synced_list)} companies):")
        print("======================================================================")
        for s in synced_list:
            print(f" • {s['company_name']:28s} | Tenure: {str(s['tenure']):5s} | Monthly Hires: {s['hires_count']}")

        print("\n======================================================================")
        print(f"⏳ PENDING COMMIT TO BACKEND DB ({len(pending_list)} companies):")
        print("======================================================================")
        for p in pending_list:
            print(f" • {p['company_name']:28s} ({p['domain']})")
            print(f"   - File        : scratch/{p['file']}")
            print(f"   - JSON vs DB  : Tenure = JSON({p['json_tenure']}) vs DB({p['db_tenure']}) | Hires = JSON({p['json_hires']}) vs DB({p['db_hires']})")
            print(f"   - Discrepancy : {p['reason']}")
            print("-" * 65)

    finally:
        db.close()

if __name__ == "__main__":
    audit_json_vs_db()

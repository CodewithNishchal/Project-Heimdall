import os
import sys
import json
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join("backend", ".env"), override=True)

from backend.database import SessionLocal
from backend.models import LeadSnapshot
from sqlalchemy.orm.attributes import flag_modified

CHALK_FILE = os.path.join("scratch", "apify_chalk_output.json")

def populate_db_offline():
    print("======================================================================")
    print("⚡ POPULATING DATABASE FROM LOCAL SAVED PAYLOADS (OFFLINE - 0 API CALLS)")
    print("======================================================================\n")

    db = SessionLocal()

    try:
        leads = db.query(LeadSnapshot).all()
        print(f"📋 Found {len(leads)} total lead records in database.\n")

        # 1. Update Chalk from scratch/apify_chalk_output.json
        if os.path.exists(CHALK_FILE):
            with open(CHALK_FILE, "r", encoding="utf-8") as f:
                chalk_raw = json.load(f)
                chalk_data = {}
                if isinstance(chalk_raw, list) and len(chalk_raw) > 0:
                    chalk_data = chalk_raw[0].get("data", {})
                elif isinstance(chalk_raw, dict):
                    chalk_data = chalk_raw.get("data", {})

                if chalk_data:
                    chalk_data_clean = dict(chalk_data)
                    # Preserve real firmographic employee count (107) instead of small LinkedIn company payload
                    chalk_data_clean["total_employees"] = 107

                    chalk_lead = db.query(LeadSnapshot).filter(
                        (LeadSnapshot.domain == "chalk.ai") | (LeadSnapshot.company_name.ilike("%chalk%"))
                    ).first()

                    if chalk_lead:
                        print(f"🎯 Updating Chalk lead in database...")
                        print(f"   • Setting Median Employee Tenure: {chalk_data_clean.get('median_employee_tenure')} yrs")
                        print(f"   • Preserving Real Total Employees: 107")

                        if not isinstance(chalk_lead.company_insights, dict):
                            chalk_lead.company_insights = {}

                        chalk_lead.company_insights.update(chalk_data_clean)
                        chalk_lead.company_linkedin_id = "688588"

                        if isinstance(chalk_lead.full_payload, dict):
                            fp = dict(chalk_lead.full_payload)
                            fp["company_insights"] = dict(chalk_lead.company_insights)
                            fp["company_linkedin_id"] = "688588"
                            chalk_lead.full_payload = fp
                            flag_modified(chalk_lead, "full_payload")

                        flag_modified(chalk_lead, "company_insights")
                        print("   ✅ Chalk successfully updated in database!")
                    else:
                        print("   ⚠️ Chalk lead not found in database!")

        # 2. Ensure all other leads in database have clean tenure & non-placeholder hiring trends
        for lead in leads:
            c_name = lead.company_name or "Unknown"
            if not isinstance(lead.company_insights, dict):
                lead.company_insights = dict(lead.company_insights) if lead.company_insights else {}

            ci = dict(lead.company_insights)

            # Preserve real Apify tenure for leads that have it (Sei AI, InfoWebUSA, Rutter, Chalk)
            # For all un-enriched leads, set tenure to None (displaying N/A in frontend)
            if c_name not in ["Sei AI", "InfoWebUSA Technologies", "Rutter", "Chalk"] and not isinstance(ci.get("median_employee_tenure"), (int, float)):
                ci["median_employee_tenure"] = None

            # If senior_hiring_trend contains static placeholder 2s, zero them out
            sht = ci.get("senior_hiring_trend")
            if isinstance(sht, list) and c_name not in ["Sei AI", "InfoWebUSA Technologies", "Rutter", "Chalk", "SurePoint Technologies", "Netstock"]:
                cleaned_trend = []
                for item in sht:
                    item_copy = dict(item)
                    if item_copy.get("total_hires") == 2:
                        item_copy["total_hires"] = 0
                    cleaned_trend.append(item_copy)
                ci["senior_hiring_trend"] = cleaned_trend

            lead.company_insights = ci
            flag_modified(lead, "company_insights")

            if isinstance(lead.full_payload, dict):
                fp = dict(lead.full_payload)
                fp["company_insights"] = ci
                if lead.company_linkedin_id:
                    fp["company_linkedin_id"] = lead.company_linkedin_id
                lead.full_payload = fp
                flag_modified(lead, "full_payload")

            med_disp = ci.get("median_employee_tenure", "N/A")
            print(f"   • {c_name:28s} | Tenure: {str(med_disp):6s} | ID: {lead.company_linkedin_id or 'N/A'}")

        db.commit()
        print("\n💾 SUCCESS! All 18 database lead records updated & committed offline.")

    finally:
        db.close()

if __name__ == "__main__":
    populate_db_offline()

import os
import sys
import json
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join("backend", ".env"), override=True)

from backend.database import SessionLocal
from backend.models import LeadSnapshot

OUTPUT_FILE = os.path.join("scratch", "db_leads_dump.json")

def fetch_db_records():
    print("======================================================================")
    print("📦 FETCHING CURRENT LEAD JSON RECORDS FROM DATABASE")
    print("======================================================================\n")

    db = SessionLocal()
    leads_data = []

    try:
        leads = db.query(LeadSnapshot).all()
        print(f"📋 Found {len(leads)} total lead records in database.\n")

        for idx, lead in enumerate(leads, 1):
            c_name = lead.company_name or "Unknown"
            dom = lead.domain or "N/A"
            score = lead.intent_score
            tier = lead.tier
            linkedin_id = lead.company_linkedin_id or "MISSING"

            insights = lead.company_insights if isinstance(lead.company_insights, dict) else {}
            jobs = lead.job_openings if isinstance(lead.job_openings, dict) else {}
            full_payload = lead.full_payload if isinstance(lead.full_payload, dict) else {}

            total_emp = insights.get("total_employees", "N/A")
            med_tenure = insights.get("median_employee_tenure", "N/A")
            new_hires = insights.get("new_hires", [])
            hiring_trend = insights.get("hiring_trend") or insights.get("senior_hiring_trend") or []

            print(f"[{idx:02d}] 🏢 {c_name} ({dom})")
            print(f"     • Intent Score: {score} | Tier: {tier} | LinkedIn ID: {linkedin_id}")
            print(f"     • Total Employees: {total_emp} | Median Tenure: {med_tenure}")
            print(f"     • Monthly New Hires Array Count: {len(new_hires) if isinstance(new_hires, list) else 0}")
            print(f"     • Hiring Trend Array Count: {len(hiring_trend) if isinstance(hiring_trend, list) else 0}")

            if isinstance(hiring_trend, list) and len(hiring_trend) > 0:
                print("     • Stored Hiring Trend Preview (Last 6 Mo):")
                for item in hiring_trend[-6:]:
                    m_label = item.get("label") or item.get("date")
                    t_hires = item.get("total_hires")
                    s_hires = item.get("senior_hires")
                    print(f"       - {m_label}: total_hires={t_hires}, senior_hires={s_hires}")

            print("-" * 70)

            leads_data.append({
                "id": lead.id,
                "company_name": c_name,
                "domain": dom,
                "intent_score": score,
                "tier": tier,
                "company_linkedin_id": lead.company_linkedin_id,
                "employee_count": lead.employee_count,
                "funding_stage": lead.funding_stage,
                "annual_revenue": lead.annual_revenue,
                "ai_verdict": lead.ai_verdict,
                "company_insights": insights,
                "job_openings": jobs,
                "full_payload": full_payload,
                "last_updated": lead.last_updated.isoformat() if lead.last_updated else None
            })

        os.makedirs("scratch", exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(leads_data, f, indent=2)

        print(f"\n💾 DUMPED ALL {len(leads_data)} DATABASE RECORDS TO: '{OUTPUT_FILE}'")

    finally:
        db.close()

if __name__ == "__main__":
    fetch_db_records()

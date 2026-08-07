import asyncio
import sys
import os
import json
import httpx
from datetime import datetime
from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
load_dotenv(env_path, override=True)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal
from backend.models import LeadSnapshot

async def main():
    print("🚀 Backfilling complete company_insights (including median_employee_tenure: 1.4) for Karini AI in DB...")
    token = os.getenv("APIFY_INSIGHTS_API_KEY") or os.getenv("APIFY_API_KEY")
    
    url = "https://api.apify.com/v2/acts/riceman~linkedin-company-data-insights-scraper/run-sync-get-dataset-items"
    params = {"token": token}
    payload = {
        "company_linkedin_urls": ["https://www.linkedin.com/company/karini-ai/"],
        "get_company_insights": True,
        "get_total_job_openings": True
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, params=params, json=payload)
        if resp.status_code not in [200, 201]:
            print(f"❌ Apify error: {resp.text}")
            return
        data = resp.json()
        if not data or not isinstance(data, list):
            print("❌ Empty data returned")
            return
        insights = data[0]

    # Process trend
    now_dt = datetime.now()
    hires_by_date = {}
    new_hires_raw = insights.get("new_hires", [])
    if isinstance(new_hires_raw, list):
        for item in new_hires_raw:
            d_str = str(item.get("date", "")).strip()
            if d_str:
                parts = d_str.split("-")
                if len(parts) >= 2:
                    try:
                        norm_key = f"{int(parts[0])}-{int(parts[1])}"
                        hires_by_date[norm_key] = item
                    except Exception:
                        pass

    trend = []
    for i in range(5, -1, -1):
        m_val = now_dt.month - i
        y_val = now_dt.year
        while m_val <= 0:
            m_val += 12
            y_val -= 1

        month_dt = datetime(y_val, m_val, 1)
        date_key = f"{y_val}-{m_val}"
        label = month_dt.strftime("%b")

        match_item = hires_by_date.get(date_key, {})
        s_hires = match_item.get("senior_hires", 0)
        t_hires = match_item.get("total_hires", 0)

        trend.append({
            "date": date_key,
            "label": label,
            "senior_hires": s_hires,
            "total_hires": t_hires
        })

    insights["hiring_trend"] = trend
    insights["senior_hiring_trend"] = trend
    insights["total_employees"] = 34

    # Update Database Record
    db = SessionLocal()
    try:
        lead = db.query(LeadSnapshot).filter(
            (LeadSnapshot.domain.ilike("%karini%")) |
            (LeadSnapshot.company_name.ilike("%karini%"))
        ).first()

        if lead:
            lead.company_insights = insights
            if isinstance(lead.full_payload, dict):
                lead.full_payload["company_insights"] = insights
                lead.full_payload["company_linkedin_id"] = insights.get("company_id")
                lead.full_payload["logo_url"] = insights.get("logo_url")
                lead.full_payload["tagline"] = insights.get("tagline")
                lead.full_payload["description"] = insights.get("description")
                lead.full_payload["hq_address"] = insights.get("hq_full_address")
                lead.full_payload["locations"] = insights.get("locations")
                lead.full_payload["phone"] = insights.get("phone")
                lead.full_payload["year_founded"] = insights.get("year_founded")
                
            db.commit()
            print("✅ Successfully updated Karini AI in DB snapshot table!")
            print(f"   median_employee_tenure is now: {lead.company_insights.get('median_employee_tenure')} yrs")
        else:
            print("⚠️ Karini AI not found in DB table")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())

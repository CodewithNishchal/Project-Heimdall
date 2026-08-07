import os
import sys
import json
import asyncio
import httpx
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join("backend", ".env"), override=True)

from backend.database import SessionLocal
from backend.models import LeadSnapshot
from backend.pipeline.linkedin_id_resolver import resolve_linkedin_company_id

APIFY_INSIGHTS_API_KEY = os.getenv("APIFY_INSIGHTS_API_KEY") or os.getenv("APIFY_API_KEY")
ACTOR_ID = "freshdata~linkedin-company-insights-scraper"
OUTPUT_FILE = os.path.join("scratch", "company_hiring_apify_results.json")

async def fetch_apify_insights_for_company(client: httpx.AsyncClient, company_id: str, company_slug: str):
    if not APIFY_INSIGHTS_API_KEY or not company_id:
        return None

    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items"
    params = {"token": APIFY_INSIGHTS_API_KEY}
    payload = {"company_id": str(company_id), "company_name": company_slug}

    try:
        resp = await client.post(url, params=params, json=payload, timeout=120.0)
        if resp.status_code in [200, 201]:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0].get("data")
            elif isinstance(data, dict):
                return data.get("data")
    except Exception as e:
        print(f"❌ Error fetching Apify LinkedIn Insights for company_id {company_id}: {e}")

    return None

async def run_hiring_data_fetch():
    print("======================================================================")
    print("🚀 APIFY COMPANY INSIGHTS & HIRING DATA RE-FETCHER & DATABASE UPDATER")
    print("======================================================================\n")

    if not APIFY_INSIGHTS_API_KEY:
        print("❌ ERROR: APIFY_INSIGHTS_API_KEY / APIFY_API_KEY not found in backend/.env")
        return

    db = SessionLocal()
    summary_output = []

    try:
        leads = db.query(LeadSnapshot).all()
        print(f"📋 Found {len(leads)} lead snapshots in database.\n")

        async with httpx.AsyncClient(timeout=120.0) as client:
            for idx, lead in enumerate(leads, 1):
                company_name = lead.company_name or "Unknown"
                domain = lead.domain or ""
                linkedin_id = lead.company_linkedin_id
                company_slug = domain.split(".")[0] if domain else company_name.lower().replace(" ", "-")

                print(f"[{idx:02d}] Processing: {company_name} ({domain}) | LinkedIn ID: {linkedin_id or 'MISSING'}")

                if not linkedin_id:
                    print(f"     🔍 Resolving LinkedIn Company ID for '{company_slug}'...")
                    linkedin_id = await resolve_linkedin_company_id(company_slug)
                    if linkedin_id:
                        lead.company_linkedin_id = linkedin_id
                        print(f"     ✅ Resolved LinkedIn ID: {linkedin_id}")
                    else:
                        print(f"     ⚠️ Could not resolve LinkedIn ID for {company_name}. Skipping Apify call.")
                        summary_output.append({
                            "company_name": company_name,
                            "domain": domain,
                            "status": "Skipped (Unresolved LinkedIn ID)",
                            "data": lead.company_insights
                        })
                        continue

                print(f"     📡 Triggering Apify actor '{ACTOR_ID}' for ID: {linkedin_id}...")
                fetched_insights = await fetch_apify_insights_for_company(client, linkedin_id, company_slug)

                if fetched_insights:
                    new_hires = fetched_insights.get("new_hires", [])
                    total_emp = fetched_insights.get("total_employees")
                    headcount_growth = fetched_insights.get("headcount_growth", {})

                    print(f"     ✅ SUCCESS! Total Employees: {total_emp} | Monthly Hires Records: {len(new_hires)}")
                    
                    # Update database model
                    if not isinstance(lead.company_insights, dict):
                        lead.company_insights = {}
                    
                    # Merge fetched insights into company_insights
                    lead.company_insights.update(fetched_insights)
                    
                    # Also populate senior_hiring_trend with total_hires & senior_hires
                    now = datetime.now()
                    hires_by_date = {}
                    if isinstance(new_hires, list):
                        for item in new_hires:
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
                        m_val = now.month - i
                        y_val = now.year
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

                    from sqlalchemy.orm.attributes import flag_modified

                    ci_copy = dict(lead.company_insights)
                    ci_copy["senior_hiring_trend"] = trend
                    lead.company_insights = ci_copy
                    flag_modified(lead, "company_insights")

                    if isinstance(lead.full_payload, dict):
                        fp_copy = dict(lead.full_payload)
                        if "company_insights" not in fp_copy or not isinstance(fp_copy["company_insights"], dict):
                            fp_copy["company_insights"] = {}
                        fp_copy["company_insights"].update(ci_copy)
                        lead.full_payload = fp_copy
                        flag_modified(lead, "full_payload")

                    summary_output.append({
                        "company_name": company_name,
                        "domain": domain,
                        "linkedin_id": linkedin_id,
                        "status": "Fetched & Updated",
                        "total_employees": total_emp,
                        "headcount_growth": headcount_growth,
                        "new_hires": new_hires,
                        "last_6_months_trend": trend
                    })
                else:
                    print(f"     ❌ Failed or empty dataset returned from Apify for {company_name}.")
                    summary_output.append({
                        "company_name": company_name,
                        "domain": domain,
                        "status": "Failed / Empty",
                        "data": lead.company_insights
                    })

                print("-" * 70)

        db.commit()
        print("\n💾 Committing changes to SQLite/PostgreSQL Database...")
        print("🎉 Database successfully updated with fresh Apify Insights data!")

        # Save consolidated JSON output file for verification
        os.makedirs("scratch", exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(summary_output, f, indent=2)

        print(f"📄 Saved complete Apify results JSON to: '{OUTPUT_FILE}'")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_hiring_data_fetch())

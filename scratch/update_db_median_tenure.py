import os
import sys
import json
import asyncio
import httpx
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join("backend", ".env"), override=True)

from backend.database import SessionLocal
from backend.models import LeadSnapshot
from backend.pipeline.linkedin_id_resolver import resolve_linkedin_company_id
from sqlalchemy.orm.attributes import flag_modified

APIFY_INSIGHTS_API_KEY = os.getenv("APIFY_INSIGHTS_API_KEY") or os.getenv("APIFY_API_KEY")
ACTOR_ID = "freshdata~linkedin-company-insights-scraper"

async def fetch_apify_tenure(client: httpx.AsyncClient, company_id: str, company_slug: str):
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
                return data[0].get("data", {})
            elif isinstance(data, dict):
                return data.get("data", {})
    except Exception as e:
        print(f"❌ Error fetching Apify Insights for company_id {company_id}: {e}")
    return None

async def sync_median_tenure_in_db():
    print("======================================================================")
    print("🧹 DATABASE MEDIAN TENURE CLEANER & APIFY SYNCHRONIZER")
    print("======================================================================\n")

    db = SessionLocal()

    try:
        leads = db.query(LeadSnapshot).all()
        print(f"📋 Found {len(leads)} lead snapshots in database.\n")

        async with httpx.AsyncClient(timeout=120.0) as client:
            for idx, lead in enumerate(leads, 1):
                company_name = lead.company_name or "Unknown"
                domain = lead.domain or ""
                linkedin_id = lead.company_linkedin_id
                company_slug = domain.split(".")[0] if domain else company_name.lower().replace(" ", "-")

                if not isinstance(lead.company_insights, dict):
                    lead.company_insights = {}

                current_tenure = lead.company_insights.get("median_employee_tenure")

                # If missing LinkedIn ID, try resolving
                if not linkedin_id:
                    linkedin_id = await resolve_linkedin_company_id(company_slug)
                    if linkedin_id:
                        lead.company_linkedin_id = linkedin_id

                # If LinkedIn ID exists, fetch live Apify insights to get exact tenure
                if linkedin_id:
                    print(f"[{idx:02d}] Fetching Apify insights for {company_name} (ID: {linkedin_id})...")
                    fetched = await fetch_apify_tenure(client, linkedin_id, company_slug)
                    if fetched and "median_employee_tenure" in fetched:
                        real_tenure = fetched.get("median_employee_tenure")
                        lead.company_insights.update(fetched)
                        print(f"     ✅ Set real Apify median_employee_tenure: {real_tenure} yrs")
                    else:
                        lead.company_insights["median_employee_tenure"] = current_tenure if isinstance(current_tenure, (int, float)) else None
                        print(f"     ℹ️ No Apify tenure returned. Set median_employee_tenure: {lead.company_insights['median_employee_tenure']}")
                else:
                    # Explicitly ensure no dummy value is stored
                    lead.company_insights["median_employee_tenure"] = current_tenure if isinstance(current_tenure, (int, float)) else None
                    print(f"[{idx:02d}] {company_name}: No LinkedIn ID. Set median_employee_tenure: None")

                if isinstance(lead.full_payload, dict):
                    fp = dict(lead.full_payload)
                    fp["company_insights"] = dict(lead.company_insights)
                    lead.full_payload = fp
                    flag_modified(lead, "full_payload")

                lead.company_insights = dict(lead.company_insights)
                flag_modified(lead, "company_insights")

                print("-" * 70)

        db.commit()
        print("\n💾 Database successfully updated and committed!")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(sync_median_tenure_in_db())

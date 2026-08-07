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

APIFY_API_KEY = os.getenv("APIFY_INSIGHTS_API_KEY") or os.getenv("APIFY_API_KEY")
ACTOR_ID = "freshdata~linkedin-company-insights-scraper"
OUTPUT_DIR = "scratch"
ALL_PAYLOADS_FILE = os.path.join(OUTPUT_DIR, "all_companies_apify_insights.json")

async def fetch_insights_for_company(client: httpx.AsyncClient, company_id: str, company_slug: str):
    if not APIFY_API_KEY or not company_id:
        return None

    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items"
    params = {"token": APIFY_API_KEY}
    payload = {
        "company_id": str(company_id),
        "company_name": company_slug
    }

    try:
        resp = await client.post(url, params=params, json=payload, timeout=120.0)
        if resp.status_code in [200, 201]:
            return resp.json()
        else:
            print(f"     ❌ HTTP Error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"     ❌ Request Exception: {e}")
    return None

async def fetch_all_companies_local():
    print("======================================================================")
    print("📡 FETCHING APIFY INSIGHTS FOR ALL LEADS & SAVING LOCALLY")
    print("======================================================================\n")

    if not APIFY_API_KEY:
        print("❌ ERROR: APIFY_INSIGHTS_API_KEY or APIFY_API_KEY not found in backend/.env!")
        return

    print(f"🔑 Using Token Prefix: {APIFY_API_KEY[:12]}...")
    db = SessionLocal()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    all_results = {}

    try:
        leads = db.query(LeadSnapshot).all()
        print(f"📋 Found {len(leads)} total leads in database.\n")

        async with httpx.AsyncClient(timeout=120.0) as client:
            for idx, lead in enumerate(leads, 1):
                c_name = lead.company_name or "Unknown"
                domain = lead.domain or ""
                linkedin_id = lead.company_linkedin_id
                company_slug = domain.split(".")[0] if domain else c_name.lower().replace(" ", "-")

                print(f"[{idx:02d}] 🏢 {c_name} ({domain})")

                # Step 1: Resolve LinkedIn ID if missing
                if not linkedin_id:
                    print(f"     🔍 Resolving LinkedIn Company ID for '{company_slug}'...")
                    linkedin_id = await resolve_linkedin_company_id(company_slug)
                    if linkedin_id:
                        lead.company_linkedin_id = linkedin_id
                        db.commit()
                        print(f"     ✅ Resolved LinkedIn ID: {linkedin_id}")
                    else:
                        print(f"     ⚠️ Could not resolve LinkedIn ID for {c_name}. Skipping.")
                        print("-" * 70)
                        continue

                # Step 2: Ping Apify Actor
                print(f"     📡 Pinging Apify actor for ID {linkedin_id} ({c_name})...")
                data = await fetch_insights_for_company(client, linkedin_id, company_slug)

                if data:
                    item_data = {}
                    if isinstance(data, list) and len(data) > 0:
                        item_data = data[0].get("data", {})
                    elif isinstance(data, dict):
                        item_data = data.get("data", {})

                    total_emp = item_data.get("total_employees", "N/A")
                    med_tenure = item_data.get("median_employee_tenure", "N/A")
                    new_hires = item_data.get("new_hires", [])

                    print(f"     ✅ SUCCESS! Total Emp: {total_emp} | Median Tenure: {med_tenure} yrs | New Hires Records: {len(new_hires)}")

                    # Save individual JSON file
                    slug_clean = company_slug.replace(".", "_").replace(" ", "_").lower()
                    indiv_file = os.path.join(OUTPUT_DIR, f"apify_insights_{slug_clean}.json")
                    with open(indiv_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)

                    all_results[c_name] = {
                        "company_name": c_name,
                        "domain": domain,
                        "linkedin_id": linkedin_id,
                        "raw_file": indiv_file,
                        "insights_summary": {
                            "total_employees": total_emp,
                            "median_employee_tenure": med_tenure,
                            "new_hires_count": len(new_hires)
                        },
                        "payload": data
                    }
                else:
                    print(f"     ⚠️ No data returned from Apify for {c_name}.")

                print("-" * 70)

        # Save master aggregated file
        with open(ALL_PAYLOADS_FILE, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2)

        print("\n======================================================================")
        print(f"💾 SUCCESSFULLY SAVED LOCAL PAYLOADS FOR {len(all_results)} COMPANIES")
        print(f"📁 Master output saved to: '{ALL_PAYLOADS_FILE}'")
        print("======================================================================\n")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(fetch_all_companies_local())

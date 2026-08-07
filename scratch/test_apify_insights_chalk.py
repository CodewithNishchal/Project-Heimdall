import os
import sys
import json
import asyncio
import httpx
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join("backend", ".env"), override=True)

from backend.pipeline.linkedin_id_resolver import resolve_linkedin_company_id

APIFY_API_KEY = os.getenv("APIFY_INSIGHTS_API_KEY") or os.getenv("APIFY_API_KEY")
ACTOR_ID = "freshdata~linkedin-company-insights-scraper"
OUTPUT_FILE = os.path.join("scratch", "apify_chalk_output.json")

async def test_chalk_apify_insights():
    print("======================================================================")
    print("📡 FETCHING APIFY INSIGHTS FOR COMPANY: Chalk (chalk.ai)")
    print("======================================================================\n")

    if not APIFY_API_KEY:
        print("❌ ERROR: APIFY_INSIGHTS_API_KEY / APIFY_API_KEY not found in backend/.env!")
        return

    company_slug = "chalk-ai"
    print(f"🔍 Step 1: Resolving LinkedIn Company ID for '{company_slug}'...")
    
    company_id = await resolve_linkedin_company_id(company_slug)
    if not company_id:
        # Fallback to alternate slug
        company_slug = "chalk"
        company_id = await resolve_linkedin_company_id(company_slug)

    if not company_id:
        print("⚠️ Could not automatically resolve numeric LinkedIn ID. Trying known ID or fallback...")
        company_id = "688588"  # Known ID if resolved, or test ID

    print(f"✅ Resolved LinkedIn Company ID: {company_id} (slug: {company_slug})\n")

    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items"
    params = {"token": APIFY_API_KEY}
    payload = {
        "company_id": str(company_id),
        "company_name": company_slug
    }

    print(f"🔑 Using Token Prefix: {APIFY_API_KEY[:12]}...")
    print(f"⏳ Pinging Apify actor '{ACTOR_ID}' for Chalk...")

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(url, params=params, json=payload)
            print(f"   HTTP Status Code: {resp.status_code}\n")

            if resp.status_code in [200, 201]:
                items = resp.json()
                print("======================================================================")
                print("✅ SUCCESS! RECEIVED APIFY INSIGHTS FOR CHALK:")
                print("======================================================================\n")

                company_data = {}
                if isinstance(items, list) and len(items) > 0:
                    company_data = items[0].get("data", {})
                elif isinstance(items, dict):
                    company_data = items.get("data", {})

                # Summary metrics
                print(f"🏢 Total Employees: {company_data.get('total_employees', 'N/A')}")
                print(f"⏳ Median Employee Tenure: {company_data.get('median_employee_tenure', 'N/A')} years")
                print(f"📈 Headcount Growth: {json.dumps(company_data.get('headcount_growth', {}))}")

                dept_breakdown = company_data.get("headcount_by_function", {})
                print(f"\n📊 Department Breakdown ({len(dept_breakdown)} functions):")
                for fn, info in list(dept_breakdown.items())[:6]:
                    print(f"   • {fn}: {info.get('count')} employees ({info.get('percentage')}%)")

                new_hires = company_data.get("new_hires", [])
                print(f"\n📅 Monthly New Hires Array ({len(new_hires)} months total):")
                for nh in new_hires[-6:]:
                    print(f"   • {nh.get('date')}: Total Hires = {nh.get('total_hires')}, Senior Hires = {nh.get('senior_hires')}")

                # Save raw JSON output
                os.makedirs("scratch", exist_ok=True)
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(items, f, indent=2)

                print("\n" + "=" * 70)
                print(f"💾 Raw JSON output saved to: '{OUTPUT_FILE}'")
                print("=" * 70 + "\n")
            else:
                print(f"❌ API Error {resp.status_code}: {resp.text[:300]}")

        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_chalk_apify_insights())

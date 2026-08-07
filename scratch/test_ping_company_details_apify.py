import os
import sys
import json
import asyncio
import httpx
from dotenv import load_dotenv

# Load environment variables from backend/.env
load_dotenv(os.path.join("backend", ".env"), override=True)

APIFY_API_KEY = os.getenv("APIFY_INSIGHTS_API_KEY") or os.getenv("APIFY_API_KEY")
ACTOR_ID = "freshdata~linkedin-company-insights-scraper"
OUTPUT_FILE = os.path.join("scratch", "test_company_details_output.json")

async def test_ping_company_details(company_id: str = "79045818", company_name: str = "modal-labs"):
    print("======================================================================")
    print(f"📡 APIFY ACTOR FOR COMPANY DETAILS: '{ACTOR_ID}'")
    print("======================================================================\n")

    if not APIFY_API_KEY:
        print("❌ ERROR: APIFY_INSIGHTS_API_KEY / APIFY_API_KEY not found in backend/.env!")
        return

    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items"
    params = {"token": APIFY_API_KEY}
    payload = {
        "company_id": str(company_id),
        "company_name": company_name
    }

    print(f"🔑 Token Prefix: {APIFY_API_KEY[:12]}...")
    print(f"🎯 Target Company: {company_name} (ID: {company_id})")
    print("⏳ Pinging Apify actor (synchronous run)...")

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(url, params=params, json=payload)
            print(f"   HTTP Response Status: {resp.status_code}\n")

            if resp.status_code in [200, 201]:
                items = resp.json()
                print("======================================================================")
                print("✅ SUCCESS! RECEIVED COMPANY DETAILS PAYLOAD FROM APIFY:")
                print("======================================================================\n")

                company_data = {}
                if isinstance(items, list) and len(items) > 0:
                    company_data = items[0].get("data", {})
                elif isinstance(items, dict):
                    company_data = items.get("data", {})

                # Print summary key fields
                print(f"🏢 Total Employees: {company_data.get('total_employees', 'N/A')}")
                print(f"⏳ Median Employee Tenure: {company_data.get('median_employee_tenure', 'N/A')} years")
                print(f"📈 Headcount Growth: {json.dumps(company_data.get('headcount_growth', {}))}")
                
                dept_breakdown = company_data.get("headcount_by_function", {})
                print(f"📊 Top Functions/Departments ({len(dept_breakdown)} total):")
                for fn, info in list(dept_breakdown.items())[:5]:
                    print(f"   • {fn}: {info.get('count')} employees ({info.get('percentage')}%)")

                new_hires = company_data.get("new_hires", [])
                print(f"📅 Monthly New Hires Records ({len(new_hires)} months total):")
                for nh in new_hires[-4:]:
                    print(f"   • {nh.get('date')}: Total Hires = {nh.get('total_hires')}, Senior Hires = {nh.get('senior_hires')}")

                # Save raw response to scratch file
                os.makedirs("scratch", exist_ok=True)
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(items, f, indent=2)

                print("\n" + "=" * 70)
                print(f"💾 Full raw JSON output saved to: '{OUTPUT_FILE}'")
                print("=" * 70 + "\n")

            else:
                print(f"❌ API Error {resp.status_code}: {resp.text[:300]}")

        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_ping_company_details("79045818", "modal-labs"))

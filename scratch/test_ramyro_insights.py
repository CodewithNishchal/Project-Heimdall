import asyncio
import sys
import os
import json
import httpx
from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
load_dotenv(env_path, override=True)

APIFY_API_KEY = os.getenv("APIFY_API_KEY")
APIFY_INSIGHTS_API_KEY = os.getenv("APIFY_INSIGHTS_API_KEY")

async def main():
    token = APIFY_INSIGHTS_API_KEY or APIFY_API_KEY
    if not token:
        print("❌ Apify API key is missing!")
        return

    url = "https://api.apify.com/v2/acts/riceman~linkedin-company-data-insights-scraper/run-sync-get-dataset-items"
    params = {"token": token}
    
    test_urls = [
        "https://www.linkedin.com/company/ramyro/",
        "https://www.linkedin.com/company/ramyro-tech/",
        "https://www.linkedin.com/company/ramyro-ai/"
    ]

    for target_url in test_urls:
        print(f"\n🚀 Querying riceman actor for: '{target_url}'...")
        payload = {
            "company_linkedin_urls": [target_url],
            "get_company_insights": True,
            "get_total_job_openings": True
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                resp = await client.post(url, params=params, json=payload)
                print(f"  HTTP Status Code: {resp.status_code}")
                if resp.status_code in [200, 201]:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        item = data[0]
                        if item.get("company_name"):
                            print(f"  ✅ Data Received for '{item.get('company_name')}'!")
                            print(f"     Company ID: {item.get('company_id')}")
                            print(f"     Employee Count: {item.get('employee_count')}")
                            print(f"     median_employee_tenure: {item.get('median_employee_tenure')}")
                            print(f"     Headcount Growth (1Y): {item.get('headcount_growth', {}).get('1y')}")
                            print("\nDetailed JSON Output:")
                            print(json.dumps(item, indent=2))
                            break
                        else:
                            print("  ⚠️ Empty/Invalid company returned from Apify.")
                    else:
                        print("  ⚠️ Empty list returned from Apify.")
                else:
                    print(f"  ❌ Error: {resp.text[:300]}")
            except Exception as e:
                print(f"  ❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(main())

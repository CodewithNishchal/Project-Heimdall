import asyncio
import sys
import os
import json
import httpx
from dotenv import load_dotenv

# Load env variables from backend/.env
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
load_dotenv(env_path, override=True)

APIFY_API_KEY = os.getenv("APIFY_API_KEY")
APIFY_INSIGHTS_API_KEY = os.getenv("APIFY_INSIGHTS_API_KEY")

async def main():
    token = APIFY_INSIGHTS_API_KEY or APIFY_API_KEY
    if not token:
        print("❌ Apify API key is missing in backend/.env!")
        return

    url = "https://api.apify.com/v2/acts/riceman~linkedin-company-data-insights-scraper/run-sync-get-dataset-items"
    params = {"token": token}
    payload = {
        "company_linkedin_urls": [
            "https://www.linkedin.com/company/hyperce/"
        ],
        "get_company_insights": True,
        "get_total_job_openings": True
    }

    print("🚀 Testing Apify Actor: riceman/linkedin-company-data-insights-scraper")
    print(f"  Target URL: https://www.linkedin.com/company/hyperce/")
    print(f"  Actor ID  : riceman~linkedin-company-data-insights-scraper\n")

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(url, params=params, json=payload)
            print(f"  HTTP Status Code: {resp.status_code}")
            
            if resp.status_code in [200, 201]:
                items = resp.json()
                print("\n✅ SUCCESS! Received Data from riceman actor:")
                print(json.dumps(items, indent=2))
            else:
                print(f"❌ Error Response: {resp.text[:500]}")
        except Exception as e:
            print(f"❌ Exception occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import sys
import os
import json
import httpx
from dotenv import load_dotenv

# Load env variables directly from backend/.env
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
load_dotenv(env_path, override=True)

APIFY_API_KEY = os.getenv("APIFY_API_KEY")
APIFY_INSIGHTS_API_KEY = os.getenv("APIFY_INSIGHTS_API_KEY")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.pipeline.linkedin_id_resolver import resolve_linkedin_company_id
from backend.pipeline.streaming_orchestrator import fetch_linkedin_company_insights

async def main():
    company_name = "Hyperce"
    company_slug = "hyperce"
    
    print("🚀 Testing freshdata/linkedin-company-insights-scraper Actor...")
    
    # 1. Resolve ID
    print("\n--- 1. Resolving LinkedIn Company ID ---")
    company_id = await resolve_linkedin_company_id(company_slug)
    print(f"  -> Company ID: {company_id}")

    if not company_id:
        print("❌ Could not resolve LinkedIn Company ID!")
        return

    # 2. Test via Streaming Orchestrator function (which uses freshdata actor)
    print("\n--- 2. Executing fetch_linkedin_company_insights() ---")
    insights = await fetch_linkedin_company_insights(company_id, company_slug)
    
    if insights:
        print("✅ SUCCESS! freshdata/linkedin-company-insights-scraper returned data:")
        print(json.dumps(insights, indent=2))
    else:
        print("❌ Scraper returned None. Testing raw HTTP request for detailed error...")
        
        # 3. Direct HTTP debug check with freshdata actor
        url = "https://api.apify.com/v2/acts/freshdata~linkedin-company-insights-scraper/run-sync-get-dataset-items"
        key_to_use = APIFY_INSIGHTS_API_KEY or APIFY_API_KEY
        params = {"token": key_to_use}
        payload = {"company_id": company_id, "company_name": company_slug}
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(url, params=params, json=payload)
            print(f"  HTTP Status: {res.status_code}")
            print(f"  Raw Body: {res.text[:500]}")

if __name__ == "__main__":
    asyncio.run(main())

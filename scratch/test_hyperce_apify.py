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

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.pipeline.linkedin_id_resolver import resolve_linkedin_company_id

async def test_raw_apify_calls():
    company_name = "Hyperce"
    domain = "hyperce.io"
    company_slug = "hyperce"
    
    print("🔎 Resolving LinkedIn Company ID...")
    company_id = await resolve_linkedin_company_id(company_slug)
    print(f"  -> Resolved ID: {company_id}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Test Career Page Scraper
        print("\n--- 1. Testing Apify Career Page Scraper (piotrv1001~company-career-page-scraper) ---")
        url1 = "https://api.apify.com/v2/acts/piotrv1001~company-career-page-scraper/run-sync-get-dataset-items"
        params1 = {"token": APIFY_API_KEY}
        payload1 = {"startUrls": [{"url": "https://hyperce.io"}]}
        
        res1 = await client.post(url1, params=params1, json=payload1)
        print(f"  HTTP Status: {res1.status_code}")
        print(f"  Response Body: {res1.text[:500]}")

        # 2. Test LinkedIn Insights Scraper
        print("\n--- 2. Testing Apify LinkedIn Insights Scraper (freshdata~linkedin-company-insights-scraper) ---")
        url2 = "https://api.apify.com/v2/acts/freshdata~linkedin-company-insights-scraper/run-sync-get-dataset-items"
        params2 = {"token": APIFY_INSIGHTS_API_KEY}
        payload2 = {"company_id": company_id, "company_name": company_slug}
        
        res2 = await client.post(url2, params=params2, json=payload2)
        print(f"  HTTP Status: {res2.status_code}")
        print(f"  Response Body: {res2.text[:500]}")

if __name__ == "__main__":
    asyncio.run(test_raw_apify_calls())

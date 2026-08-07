import asyncio
import sys
import os
import json
import re
import httpx
from dotenv import load_dotenv

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
load_dotenv(env_path, override=True)

EXA_API_KEY = os.getenv("EXA_API_KEY")
APIFY_API_KEY = os.getenv("APIFY_API_KEY")
APIFY_INSIGHTS_API_KEY = os.getenv("APIFY_INSIGHTS_API_KEY")

async def search_exa(query: str):
    print(f"🔎 Querying Exa AI for: '{query}'...")
    url = "https://api.exa.ai/search"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": EXA_API_KEY
    }
    payload = {
        "query": query,
        "type": "neural",
        "useAutoprompt": False,
        "numResults": 10,
        "contents": {
            "text": True,
            "summary": True
        }
    }

    async with httpx.AsyncClient(timeout=25.0) as client:
        res = await client.post(url, headers=headers, json=payload)
        if res.status_code == 200:
            return res.json().get("results", [])
        else:
            print(f"❌ Exa Error ({res.status_code}): {res.text}")
            return []

async def fetch_riceman(linkedin_url: str):
    token = APIFY_INSIGHTS_API_KEY or APIFY_API_KEY
    # Ensure URL starts with https://www.
    if not linkedin_url.startswith("https://www."):
        slug = linkedin_url.rstrip("/").split("/company/")[-1]
        linkedin_url = f"https://www.linkedin.com/company/{slug}/"

    print(f"\n📈 Querying riceman actor for Exa-found LinkedIn URL: '{linkedin_url}'...")
    url = "https://api.apify.com/v2/acts/riceman~linkedin-company-data-insights-scraper/run-sync-get-dataset-items"
    params = {"token": token}
    payload = {
        "company_linkedin_urls": [linkedin_url],
        "get_company_insights": True,
        "get_total_job_openings": True
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, params=params, json=payload)
        print(f"  HTTP Status Code: {resp.status_code}")
        if resp.status_code in [200, 201]:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0 and data[0].get("company_name"):
                item = data[0]
                print(f"  ✅ SUCCESS! Data Received for '{item.get('company_name')}'")
                print(f"     LinkedIn URL: {item.get('linkedin_url')}")
                print(f"     Employee Count: {item.get('employee_count')}")
                print(f"     median_employee_tenure: {item.get('median_employee_tenure')}")
                print("\nDetailed JSON Output:")
                print(json.dumps(item, indent=2))
                return item
            else:
                print("  ⚠️ Empty / Invalid response from Apify riceman actor.")
        else:
            print(f"  ❌ Apify Error: {resp.text[:300]}")

async def main():
    if not EXA_API_KEY:
        print("❌ EXA_API_KEY is missing!")
        return

    # Step 1: Run Exa Search for Ramyro
    results = await search_exa("Ramyro company LinkedIn profile software B2B")
    
    print("\n--- EXA AI SEARCH RESULTS ---")
    extracted_linkedin_urls = []
    
    for idx, item in enumerate(results, 1):
        url = item.get("url", "")
        title = item.get("title", "")
        text = item.get("text", "")
        summary = item.get("summary", "")
        
        print(f"\n[{idx}] Title: {title}")
        print(f"    URL: {url}")
        print(f"    Summary: {summary[:150]}...")
        
        # Scan for LinkedIn URL in result URL and text
        full_blob = f"{url} {title} {text} {summary}"
        matches = re.findall(r'https?://(?:www\.)?linkedin\.com/company/[a-zA-Z0-9_-]+/?', full_blob, re.IGNORECASE)
        for m in matches:
            clean_url = m.rstrip("/") + "/"
            if clean_url not in extracted_linkedin_urls:
                extracted_linkedin_urls.append(clean_url)

    print("\n=========================================================================")
    print(f"🔗 EXTRACTED LINKEDIN URL(S) FROM EXA: {extracted_linkedin_urls}")
    print("=========================================================================")

    # Step 2: Fetch insights via riceman for any extracted LinkedIn URLs
    if extracted_linkedin_urls:
        for link_url in extracted_linkedin_urls:
            await fetch_riceman(link_url)
    else:
        print("⚠️ No LinkedIn URLs found in Exa text. Trying direct Exa query for LinkedIn...")
        linkedin_results = await search_exa("site:linkedin.com/company/ Ramyro")
        for item in linkedin_results:
            l_url = item.get("url", "")
            if "linkedin.com/company/" in l_url:
                clean_url = l_url.split("?")[0].rstrip("/") + "/"
                print(f"\n🎯 Found LinkedIn URL via direct site search: {clean_url}")
                await fetch_riceman(clean_url)
                break

if __name__ == "__main__":
    asyncio.run(main())

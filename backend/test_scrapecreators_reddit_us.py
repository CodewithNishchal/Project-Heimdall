"""
Test script: Tests ScrapeCreators Google/Reddit search using US-specific keyword qualifiers.
(e.g., 'USA', 'United States', 'California', 'New York', 'Austin', 'San Francisco').

Endpoint: GET https://api.scrapecreators.com/v1/google/search
Header: x-api-key: {SCRAPE_CREATORS_API_KEY}
"""
import os
import sys
import asyncio
import json
import logging
import httpx
from dotenv import dotenv_values

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

env_vars = dotenv_values(os.path.join(os.path.dirname(__file__), ".env"))
SCRAPE_CREATORS_API_KEY = env_vars.get("SCRAPE_CREATORS_API_KEY") or os.getenv("SCRAPE_CREATORS_API_KEY")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestScrapeCreatorsRedditUS")

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "test_scrapecreators_reddit_us_results.json")

# US-Enriched Query Matrix for ScrapeCreators Search
US_ENRICHED_QUERIES = [
    # Query 1: Site-restricted Reddit search with US location keyword
    'site:reddit.com "recruiting agency" USA OR "United States"',
    
    # Query 2: US Tech Hub & Hiring Intent
    'site:reddit.com "hiring software engineers" California OR "New York" OR Austin',
    
    # Query 3: US Founder / Team Scaling Intent
    'site:reddit.com "scaling engineering team" "United States"',

    # Query 4: Direct Staffing Firm Recommendation in US
    'site:reddit.com "staffing agency recommendation" US OR USA'
]


async def test_scrapecreators_google_reddit(client: httpx.AsyncClient, query_str: str) -> dict:
    url = "https://api.scrapecreators.com/v1/google/search"
    headers = {
        "x-api-key": SCRAPE_CREATORS_API_KEY
    }
    params = {
        "query": query_str,
        "date_posted": "last-month",
        "page": 1
    }

    print(f"\n" + "=" * 70)
    print(f"🚀 TESTING US-ENRICHED QUERY: '{query_str}'")
    print("=" * 70)

    try:
        resp = await client.get(url, params=params, headers=headers, timeout=35.0)
        if resp.status_code == 200:
            data = resp.json()
            items = (
                data.get("organic") or 
                data.get("results") or 
                data.get("data") or 
                data.get("posts") or 
                (data if isinstance(data, list) else [])
            )
            print(f"✅ SUCCESS — Received {len(items)} items for query")

            for i, item in enumerate(items[:5], 1):
                title = item.get("title") or item.get("name") or "No Title"
                snippet = item.get("snippet") or item.get("description") or ""
                link = item.get("link") or item.get("url") or "N/A"

                print(f"\n   [{i}] Title  : {title[:75]}")
                print(f"       Link   : {link}")
                print(f"       Snippet: {snippet[:110]}...")

            return {
                "query": query_str,
                "total_items": len(items),
                "items": items
            }
        else:
            print(f"❌ HTTP {resp.status_code}: {resp.text[:180]}")
            return {"query": query_str, "error": resp.text[:180]}

    except Exception as e:
        print(f"❌ Exception: {e}")
        return {"query": query_str, "error": str(e)}


async def main():
    if not SCRAPE_CREATORS_API_KEY:
        print("❌ SCRAPE_CREATORS_API_KEY is missing in backend/.env!")
        return

    all_results = {}

    async with httpx.AsyncClient(timeout=40.0) as client:
        for q in US_ENRICHED_QUERIES:
            res = await test_scrapecreators_google_reddit(client, q)
            all_results[q] = res

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    print("\n" + "=" * 70)
    print(f"💾 SAVED FULL US-ENRICHED RESULTS TO: {OUTPUT_FILE}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

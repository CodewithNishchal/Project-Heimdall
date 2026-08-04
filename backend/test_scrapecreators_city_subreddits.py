"""
Test script: Tests ScrapeCreators Search API using US Metro Subreddits & US City Keywords
(e.g., 'r/SanJose', 'r/austinjobs', 'r/nycjobs', 'r/bayarea', 'San Francisco', 'New York', 'Austin', 'Seattle').

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
logger = logging.getLogger("TestUSCitySubreddits")

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "test_scrapecreators_city_subreddits_results.json")

# US City & US Metro Subreddit Queries
US_CITY_QUERIES = [
    # Query 1: Targeted US Metro Job/Tech Subreddits
    'site:reddit.com/r/SanJose OR site:reddit.com/r/austinjobs OR site:reddit.com/r/nycjobs OR site:reddit.com/r/bayarea "hiring" OR "recruiting"',
    
    # Query 2: US Tech Hub City Names with Agency Intent
    'site:reddit.com "recruiting agency" "San Francisco" OR "New York" OR "Austin" OR "Chicago" OR "Seattle"',
    
    # Query 3: US Metro Founder/Startup Hiring Needs
    'site:reddit.com "hiring software engineers" "Bay Area" OR "NYC" OR "Austin" OR "Boston"'
]


async def test_scrapecreators_city_search(client: httpx.AsyncClient, query_str: str) -> dict:
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
    print(f"🚀 TESTING US CITY / SUBREDDIT QUERY: '{query_str}'")
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
        for q in US_CITY_QUERIES:
            res = await test_scrapecreators_city_search(client, q)
            all_results[q] = res

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    print("\n" + "=" * 70)
    print(f"💾 SAVED FULL US CITY/SUBREDDIT RESULTS TO: {OUTPUT_FILE}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

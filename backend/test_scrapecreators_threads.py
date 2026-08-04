"""
Test script: Tests ScrapeCreators Threads Search API exclusively.
Outputs detailed console logs and saves full raw JSON responses to backend/test_scrapecreators_threads_results.json.

Endpoint: GET https://api.scrapecreators.com/v1/threads/search
Header: x-api-key: {SCRAPE_CREATORS_API_KEY}
"""
import os
import sys
import asyncio
import json
import logging
import httpx
from datetime import datetime, timezone, timedelta
from dotenv import dotenv_values

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

env_vars = dotenv_values(os.path.join(os.path.dirname(__file__), ".env"))
SCRAPE_CREATORS_API_KEY = env_vars.get("SCRAPE_CREATORS_API_KEY") or os.getenv("SCRAPE_CREATORS_API_KEY")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestScrapeCreatorsThreads")

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "test_scrapecreators_threads_results.json")


async def test_scrapecreators_threads_query(client: httpx.AsyncClient, query_str: str) -> dict:
    url = "https://api.scrapecreators.com/v1/threads/search"
    headers = {
        "x-api-key": SCRAPE_CREATORS_API_KEY
    }
    
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    
    params = {
        "query": query_str,
        "start_date": thirty_days_ago.strftime("%Y-%m-%d"),
        "end_date": now.strftime("%Y-%m-%d")
    }

    print(f"\n" + "=" * 65)
    print(f"🚀 TESTING SCRAPECREATORS THREADS QUERY: '{query_str}'")
    print("=" * 65)
    print(f"Sending GET to {url} with params: {params}...")

    try:
        resp = await client.get(url, params=params, headers=headers, timeout=40.0)
        print(f"HTTP Response Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            items = (
                data.get("posts") or 
                data.get("data") or 
                data.get("threads") or 
                data.get("results") or 
                (data if isinstance(data, list) else [])
            )
            print(f"✅ SUCCESS — Received {len(items)} Threads posts for query '{query_str}'\n")

            for i, item in enumerate(items[:5], 1):
                text = item.get("caption") or item.get("text") or item.get("content") or ""
                author = item.get("user") or item.get("author") or {}
                username = author.get("username") or author.get("name") or "Unknown"
                post_url = item.get("url") or item.get("link") or "N/A"
                pub_date = item.get("published_at") or item.get("created_at") or item.get("taken_at") or "N/A"
                
                print(f"   [{i}] User    : @{username}")
                print(f"       Date    : {pub_date}")
                print(f"       URL     : {post_url}")
                print(f"       Caption : {text[:120]}...\n")

            return {
                "query": query_str,
                "status_code": resp.status_code,
                "total_items": len(items),
                "items": items,
                "raw_response": data
            }
        else:
            print(f"❌ Error HTTP {resp.status_code}: {resp.text[:200]}")
            return {
                "query": query_str,
                "status_code": resp.status_code,
                "error": resp.text[:200]
            }

    except Exception as e:
        print(f"❌ Exception during ScrapeCreators request: {e}")
        return {
            "query": query_str,
            "error": str(e)
        }


async def main():
    if not SCRAPE_CREATORS_API_KEY:
        print("❌ SCRAPE_CREATORS_API_KEY is missing in backend/.env!")
        return

    queries_to_test = [
        "scaling engineering team",
        "hiring senior engineers",
        "looking for a recruitment agency"
    ]

    all_results = {}

    async with httpx.AsyncClient(timeout=45.0) as client:
        for q in queries_to_test:
            res = await test_scrapecreators_threads_query(client, q)
            all_results[q] = res

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    print("\n" + "=" * 65)
    print(f"💾 SAVED ALL THREADS RESULTS TO: {OUTPUT_FILE}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

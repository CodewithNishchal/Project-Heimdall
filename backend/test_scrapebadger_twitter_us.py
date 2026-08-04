"""
Test script: Tests X (Twitter) post search via ScrapeBadger API with:
1. Dynamic `since:YYYY-MM-DD` (past 30 days) date filter to kill 2016/2020 bot archive spam.
2. US Location targeting & City filters.

Saves raw JSON output to backend/test_scrapebadger_twitter_us_results.json.

Endpoint: GET https://scrapebadger.com/v1/twitter/tweets/advanced_search
Header: x-api-key: {SCRAPEBADGER_API_KEY}
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
SCRAPEBADGER_API_KEY = env_vars.get("SCRAPEBADGER_API_KEY") or os.getenv("SCRAPEBADGER_API_KEY")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestScrapeBadgerTwitterUS")

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "test_scrapebadger_twitter_us_results.json")

# Calculate past 30 days date filter
thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
SINCE_DATE = thirty_days_ago.strftime("%Y-%m-%d")

# US-Targeted Fresh X (Twitter) Advanced Search Queries with since: operator
X_TWITTER_FRESH_QUERIES = [
    # Query 1: Fresh US Hiring & Recruitment Intent (Past 30 Days)
    f'("looking for a recruiting agency" OR "hiring DevOps" OR "hiring senior engineers") USA since:{SINCE_DATE} -"looking for a job" -"my resume"',
    
    # Query 2: Fresh US Growth & Marketing Intent (Past 30 Days)
    f'("looking for a marketing agency" OR "need a growth marketer") USA since:{SINCE_DATE}',
    
    # Query 3: Fresh US Metro Tech Hub Hiring (Past 30 Days)
    f'("hiring software engineers" OR "scaling engineering team") ("San Francisco" OR "New York" OR "Austin") since:{SINCE_DATE}'
]


async def test_scrapebadger_twitter_query(client: httpx.AsyncClient, query_str: str) -> dict:
    url = "https://scrapebadger.com/v1/twitter/tweets/advanced_search"
    headers = {
        "x-api-key": SCRAPEBADGER_API_KEY
    }
    params = {
        "query": query_str,
        "count": 25
    }

    print(f"\n" + "=" * 70)
    print(f"🚀 TESTING FRESH SCRAPEBADGER X (TWITTER) QUERY: '{query_str}'")
    print("=" * 70)

    try:
        resp = await client.get(url, params=params, headers=headers, timeout=40.0)
        print(f"HTTP Status Code: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            items = data.get("tweets") or data.get("data") or data.get("results") or (data if isinstance(data, list) else [])
            print(f"✅ SUCCESS — Received {len(items)} FRESH tweets (since {SINCE_DATE})")

            for i, item in enumerate(items[:5], 1):
                text = item.get("text") or item.get("full_text") or ""
                user_obj = item.get("user") or item.get("author") or {}
                username = user_obj.get("screen_name") or user_obj.get("username") or item.get("userName") or "Unknown"
                name = user_obj.get("name") or item.get("name") or "Unknown"
                location = user_obj.get("location") or "N/A"
                created_at = item.get("created_at") or item.get("createdAt") or "N/A"

                print(f"\n   [{i}] User    : @{username} ({name}) | Location: {location}")
                print(f"       Date    : {created_at}")
                print(f"       Tweet   : {text[:100]}...")

            return {
                "query": query_str,
                "status_code": resp.status_code,
                "total_items": len(items),
                "items": items
            }
        else:
            print(f"❌ Error HTTP {resp.status_code}: {resp.text[:200]}")
            return {"query": query_str, "status_code": resp.status_code, "error": resp.text[:200]}

    except Exception as e:
        print(f"❌ Exception: {e}")
        return {"query": query_str, "error": str(e)}


async def main():
    if not SCRAPEBADGER_API_KEY:
        print("❌ SCRAPEBADGER_API_KEY is missing in backend/.env!")
        return

    all_results = {}

    async with httpx.AsyncClient(timeout=45.0) as client:
        for q in X_TWITTER_FRESH_QUERIES:
            res = await test_scrapebadger_twitter_query(client, q)
            all_results[q] = res

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    print("\n" + "=" * 70)
    print(f"💾 SAVED FRESH X (TWITTER) US RESULTS TO: {OUTPUT_FILE}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

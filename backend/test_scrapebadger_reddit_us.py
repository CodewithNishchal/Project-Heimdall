"""
Test script: Tests Reddit post search via ScrapeBadger API with US location and city targeting.
Saves raw JSON output to backend/test_scrapebadger_reddit_us_results.json.

Endpoint: GET https://scrapebadger.com/v1/reddit/search/posts
Header: x-api-key: {SCRAPEBADGER_API_KEY}
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
SCRAPEBADGER_API_KEY = env_vars.get("SCRAPEBADGER_API_KEY") or os.getenv("SCRAPEBADGER_API_KEY")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestScrapeBadgerRedditUS")

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "test_scrapebadger_reddit_us_results.json")

# US-Targeted Reddit Queries via ScrapeBadger
REDDIT_US_QUERIES = [
    # Query 1: Targeted US Metro Subreddits & Hiring Intent
    'hiring senior engineers San Jose OR Austin OR NYC',
    
    # Query 2: Recruiting / Staffing Agency Intent in US
    'recruiting agency recommendation San Francisco OR New York OR Austin',
    
    # Query 3: Startup Engineering Scaling in US
    'scaling engineering team USA OR California'
]


async def test_scrapebadger_reddit_query(client: httpx.AsyncClient, query_str: str) -> dict:
    url = "https://scrapebadger.com/v1/reddit/search/posts"
    headers = {
        "x-api-key": SCRAPEBADGER_API_KEY
    }
    params = {
        "q": query_str,
        "limit": 20
    }

    print(f"\n" + "=" * 70)
    print(f"🚀 TESTING SCRAPEBADGER REDDIT QUERY: '{query_str}'")
    print("=" * 70)
    print(f"Sending GET to {url}...")

    try:
        resp = await client.get(url, params=params, headers=headers, timeout=35.0)
        print(f"HTTP Status Code: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            posts = data.get("posts", [])
            print(f"✅ SUCCESS — Received {len(posts)} Reddit posts for query")

            for i, p in enumerate(posts[:5], 1):
                title = p.get("title") or "No Title"
                selftext = p.get("selftext") or p.get("text") or ""
                subreddit = p.get("subreddit") or p.get("subreddit_name_prefixed") or "N/A"
                permalink = p.get("permalink") or p.get("url") or "N/A"
                if permalink and not permalink.startswith("http"):
                    permalink = f"https://reddit.com{permalink}"
                
                print(f"\n   [{i}] Subreddit: r/{subreddit}")
                print(f"       Title    : {title[:75]}")
                print(f"       URL      : {permalink}")
                print(f"       Text     : {selftext[:100]}...")

            return {
                "query": query_str,
                "status_code": resp.status_code,
                "total_items": len(posts),
                "items": posts
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

    async with httpx.AsyncClient(timeout=40.0) as client:
        for q in REDDIT_US_QUERIES:
            res = await test_scrapebadger_reddit_query(client, q)
            all_results[q] = res

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    print("\n" + "=" * 70)
    print(f"💾 SAVED FULL REDDIT US RESULTS TO: {OUTPUT_FILE}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

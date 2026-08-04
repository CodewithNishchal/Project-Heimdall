"""
Test script: Tests Apify LinkedIn Post Scraper (harvestapi~linkedin-post-search)
using natural unquoted queries with US keywords (e.g. USA, United States, California).

Saves full JSON responses to backend/test_apify_linkedin_us_results.json.
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
APIFY_API_KEY = env_vars.get("APIFY_API_KEY") or os.getenv("APIFY_API_KEY")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestApifyLinkedInUS")

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "test_apify_linkedin_us_results.json")

# Natural Unquoted Queries with US Location Keywords
LINKEDIN_NATURAL_US_QUERIES = [
    'looking for a recruiting agency USA',
    'hiring senior engineers United States',
    'scaling engineering team USA',
    'looking for a staffing firm California',
    'welcomes VP of Engineering United States'
]


async def test_apify_linkedin_query(client: httpx.AsyncClient, query_str: str) -> dict:
    url = f"https://api.apify.com/v2/acts/harvestapi~linkedin-post-search/run-sync-get-dataset-items?token={APIFY_API_KEY}"
    
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    limit_date_str = thirty_days_ago.strftime("%Y-%m-%d")
    
    payload = {
        "searchQueries": [query_str],
        "maxPosts": 10,
        "postedLimitDate": limit_date_str,
        "postNestedComments": False,
        "postNestedReactions": False,
        "scrapeComments": False,
        "scrapeReactions": False
    }

    print(f"\n" + "=" * 70)
    print(f"🚀 TESTING NATURAL UNQUOTED LINKEDIN QUERY: '{query_str}'")
    print("=" * 70)
    print(f"Sending POST to HarvestAPI Actor...")

    try:
        resp = await client.post(url, json=payload, timeout=90.0)
        print(f"HTTP Status Code: {resp.status_code}")

        if resp.status_code in (200, 201):
            data = resp.json()
            items = data if isinstance(data, list) else data.get("data", [])
            print(f"✅ SUCCESS — Received {len(items)} LinkedIn posts for query")

            for i, item in enumerate(items[:5], 1):
                text = item.get("text") or item.get("content") or ""
                author = item.get("author", {}) if isinstance(item.get("author"), dict) else {}
                author_name = author.get("name") or item.get("authorName") or "Unknown"
                author_title = author.get("headline") or author.get("title") or "Unknown"
                post_url = item.get("url") or item.get("link") or "N/A"
                posted_date = item.get("postedAt", {}).get("date") if isinstance(item.get("postedAt"), dict) else "N/A"

                print(f"\n   [{i}] Author: {author_name}")
                print(f"       Headline: {author_title[:70]}")
                print(f"       Date    : {posted_date}")
                print(f"       URL     : {post_url}")
                print(f"       Text    : {text[:100]}...")

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
    if not APIFY_API_KEY:
        print("❌ APIFY_API_KEY is missing in backend/.env!")
        return

    all_results = {}

    async with httpx.AsyncClient(timeout=95.0) as client:
        for q in LINKEDIN_NATURAL_US_QUERIES:
            res = await test_apify_linkedin_query(client, q)
            all_results[q] = res

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    print("\n" + "=" * 70)
    print(f"💾 SAVED FULL LINKEDIN US NATURAL RESULTS TO: {OUTPUT_FILE}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

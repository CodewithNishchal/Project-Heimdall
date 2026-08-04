"""
Test script: Tests Apify LinkedIn Post Scraper (HarvestAPI) and ScrapeCreators Threads API with US location preference.
Saves raw JSON output to backend/test_apify_linkedin_threads_us_results.json.

1. Apify LinkedIn Post Scraper (harvestapi~linkedin-post-search):
   - Query: "looking for a recruitment agency"

2. ScrapeCreators Threads Search:
   - Query: "looking for a recruitment agency"
   - Date range: past 30 days
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
SCRAPE_CREATORS_API_KEY = env_vars.get("SCRAPE_CREATORS_API_KEY") or os.getenv("SCRAPE_CREATORS_API_KEY")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestApifyLinkedInThreadsUS")

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "test_apify_linkedin_threads_us_results.json")


async def test_apify_linkedin():
    print("\n" + "=" * 65)
    print("🚀 1. TESTING APIFY LINKEDIN POST SCRAPER (HARVESTAPI)")
    print("=" * 65)

    if not APIFY_API_KEY:
        print("❌ APIFY_API_KEY is missing in backend/.env!")
        return {"error": "APIFY_API_KEY missing"}

    url = f"https://api.apify.com/v2/acts/harvestapi~linkedin-post-search/run-sync-get-dataset-items?token={APIFY_API_KEY}"
    
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    limit_date_str = thirty_days_ago.strftime("%Y-%m-%d")
    
    # Query specifying US context in search string and payload
    query_str = '"looking for a recruitment agency" United States'
    payload = {
        "maxPosts": 10,
        "postNestedComments": False,
        "postNestedReactions": False,
        "postedLimitDate": limit_date_str,
        "scrapeComments": False,
        "scrapeReactions": False,
        "searchQueries": [query_str]
    }

    print(f"Sending Apify LinkedIn POST request to HarvestAPI Actor...")
    print(f"Query: {query_str}")

    async with httpx.AsyncClient(timeout=95.0) as client:
        try:
            resp = await client.post(url, json=payload, timeout=90.0)
            if resp.status_code in (200, 201):
                data = resp.json()
                items = data if isinstance(data, list) else data.get("data", [])
                print(f"✅ APIFY LINKEDIN HTTP {resp.status_code} OK — Received {len(items)} posts\n")

                for i, item in enumerate(items[:5], 1):
                    text = item.get("text") or item.get("content") or ""
                    author = item.get("author", {}) if isinstance(item.get("author"), dict) else {}
                    author_name = author.get("name") or item.get("authorName") or "Unknown"
                    author_title = author.get("headline") or author.get("title") or "Unknown"
                    post_url = item.get("url") or item.get("link") or "N/A"
                    
                    print(f"   [{i}] Author: {author_name} ({author_title[:50]})")
                    print(f"       URL   : {post_url}")
                    print(f"       Text  : {text[:100]}...\n")

                return {
                    "query": query_str,
                    "total_items": len(items),
                    "items": items
                }
            else:
                print(f"⚠️ Apify LinkedIn Returned HTTP {resp.status_code}: {resp.text[:150]}")
                return {"error": f"HTTP {resp.status_code}: {resp.text[:150]}"}
        except Exception as e:
            print(f"❌ Apify LinkedIn Error: {e}")
            return {"error": str(e)}


async def test_scrapecreators_threads_us():
    print("\n" + "=" * 65)
    print("🚀 2. TESTING SCRAPECREATORS THREADS API WITH US TARGETING")
    print("=" * 65)

    if not SCRAPE_CREATORS_API_KEY:
        print("❌ SCRAPE_CREATORS_API_KEY is missing in backend/.env!")
        return {"error": "SCRAPE_CREATORS_API_KEY missing"}

    url = "https://api.scrapecreators.com/v1/threads/search"
    headers = {
        "x-api-key": SCRAPE_CREATORS_API_KEY
    }
    
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    
    query_str = "looking for a recruitment agency"
    params = {
        "query": query_str,
        "country": "US",
        "location": "United States",
        "start_date": thirty_days_ago.strftime("%Y-%m-%d"),
        "end_date": now.strftime("%Y-%m-%d")
    }

    print(f"Sending ScrapeCreators Threads GET to {url}...")
    print(f"Params: {params}")

    async with httpx.AsyncClient(timeout=40.0) as client:
        try:
            resp = await client.get(url, params=params, headers=headers, timeout=30.0)
            if resp.status_code == 200:
                data = resp.json()
                items = (
                    data.get("posts") or 
                    data.get("data") or 
                    data.get("threads") or 
                    data.get("results") or 
                    (data if isinstance(data, list) else [])
                )
                print(f"✅ SCRAPECREATORS THREADS HTTP 200 OK — Received {len(items)} posts\n")

                for i, item in enumerate(items[:5], 1):
                    text = item.get("caption") or item.get("text") or item.get("content") or ""
                    author = item.get("user") or item.get("author") or {}
                    username = author.get("username") or author.get("name") or "Unknown"
                    post_url = item.get("url") or item.get("link") or "N/A"
                    
                    print(f"   [{i}] User: @{username}")
                    print(f"       URL : {post_url}")
                    print(f"       Text: {text[:100]}...\n")

                return {
                    "params": params,
                    "total_items": len(items),
                    "items": items
                }
            else:
                print(f"⚠️ ScrapeCreators Threads Returned HTTP {resp.status_code}: {resp.text[:150]}")
                return {"error": f"HTTP {resp.status_code}: {resp.text[:150]}"}
        except Exception as e:
            print(f"❌ ScrapeCreators Threads Error: {e}")
            return {"error": str(e)}


async def main():
    linkedin_data = await test_apify_linkedin()
    threads_data = await test_scrapecreators_threads_us()

    full_output = {
        "apify_linkedin_results": linkedin_data,
        "scrapecreators_threads_results": threads_data
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(full_output, f, indent=2)

    print("\n" + "=" * 65)
    print(f"💾 SAVED FULL RESULTS TO FILE: {OUTPUT_FILE}")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    asyncio.run(main())

"""
Test script: Verifies setting US location preferences for Google Serper API and Apify API.
Saves raw JSON response output to backend/test_apify_serper_us_results.json.

1. Google Serper API (Google Search / News / Reddit):
   - Parameters: "gl": "us", "location": "United States"

2. Apify Twitter (X) Actor:
   - Parameters: "searchTerms": [...], "tweetLanguage": "en", "searchMode": "live"
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
SERPER_API_KEY = env_vars.get("SERPER_API_KEY") or os.getenv("SERPER_API_KEY")
APIFY_API_KEY = env_vars.get("APIFY_API_KEY") or os.getenv("APIFY_API_KEY")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestApifySerperUS")

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "test_apify_serper_us_results.json")


async def test_serper_us_location() -> dict:
    print("\n" + "=" * 65)
    print("🚀 1. TESTING GOOGLE SERPER API WITH US LOCATION PREFERENCE")
    print("=" * 65)

    if not SERPER_API_KEY:
        print("❌ SERPER_API_KEY is missing in backend/.env!")
        return {"error": "SERPER_API_KEY missing"}

    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "q": "looking for a recruitment agency site:linkedin.com OR site:reddit.com",
        "gl": "us",
        "location": "United States",
        "tbs": "qdr:w",
        "num": 10
    }

    print(f"Sending Serper POST to {url} with gl='us' & location='United States'...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            organic = data.get("organic", [])
            search_params = data.get("searchParameters", {})

            print(f"✅ SERPER HTTP 200 OK — Returned {len(organic)} US-targeted search results")
            print(f"   - Search Location Parameter Applied: {search_params.get('location', 'N/A')}")
            print(f"   - Country Code Parameter Applied   : {search_params.get('gl', 'N/A')}")
            print("\nSample US Search Results:")

            for i, item in enumerate(organic[:5], 1):
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                link = item.get("link", "")
                print(f"   [{i}] {title[:60]}")
                print(f"       URL    : {link}")
                print(f"       Snippet: {snippet[:80]}...\n")

            return {
                "search_parameters": search_params,
                "total_results": len(organic),
                "organic_results": organic
            }

        except Exception as e:
            print(f"❌ Serper API Error: {e}")
            return {"error": str(e)}


async def test_apify_twitter_us_location() -> dict:
    print("\n" + "=" * 65)
    print("🚀 2. TESTING APIFY TWITTER (X) SCRAPER WITH US GEO/LANG TARGETING")
    print("=" * 65)

    if not APIFY_API_KEY:
        print("❌ APIFY_API_KEY is missing in backend/.env!")
        return {"error": "APIFY_API_KEY missing"}

    url = f"https://api.apify.com/v2/actors/apidojo~tweet-scraper/run-sync-get-dataset-items?token={APIFY_API_KEY}"

    us_query = '"looking for a recruitment agency" geocode:39.8283,-98.5795,1500mi'
    
    payload = {
        "searchTerms": [us_query],
        "tweetLanguage": "en",
        "maxItems": 10,
        "sort": "Latest"
    }

    print(f"Sending Apify Twitter Actor Run with US Geocode Radius...")
    print(f"Query: {us_query}")

    async with httpx.AsyncClient(timeout=95.0) as client:
        try:
            resp = await client.post(url, json=payload, timeout=90.0)
            if resp.status_code in (200, 201):
                data = resp.json()
                items = data if isinstance(data, list) else data.get("data", [])
                print(f"✅ APIFY TWITTER HTTP {resp.status_code} OK — Received {len(items)} US-targeted tweets")

                for i, item in enumerate(items[:5], 1):
                    text = item.get("text") or item.get("full_text") or ""
                    author = item.get("author", {}) if isinstance(item.get("author"), dict) else {}
                    username = item.get("userName") or author.get("userName") or "unknown"
                    location = author.get("location") or item.get("user", {}).get("location") or "N/A"
                    
                    print(f"   [{i}] User: @{username} (Location: {location})")
                    print(f"       Tweet: {text[:100]}...\n")

                return {
                    "search_query": us_query,
                    "total_items": len(items),
                    "items": items
                }
            else:
                print(f"⚠️ Apify Returned HTTP {resp.status_code}: {resp.text[:150]}")
                return {"error": f"HTTP {resp.status_code}: {resp.text[:150]}"}
        except Exception as e:
            print(f"❌ Apify Twitter Error: {e}")
            return {"error": str(e)}


async def main():
    serper_data = await test_serper_us_location()
    apify_data = await test_apify_twitter_us_location()

    full_output = {
        "serper_us_results": serper_data,
        "apify_twitter_us_results": apify_data
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(full_output, f, indent=2)

    print("\n" + "=" * 65)
    print(f"💾 SAVED FULL RESULTS TO FILE: {OUTPUT_FILE}")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    asyncio.run(main())

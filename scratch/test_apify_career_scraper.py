"""
Test script: Tests Apify actor 'piotrv1001/company-career-page-scraper'.
Uses APIFY_API_KEY from backend/.env.

Endpoint: POST https://api.apify.com/v2/acts/piotrv1001~company-career-page-scraper/run-sync-get-dataset-items?token={APIFY_API_KEY}
Saves output to scratch/apify_career_page_output.json.
"""
import os
import sys
import json
import asyncio
import httpx
from dotenv import load_dotenv

# Load environment variables from backend/.env
load_dotenv("backend/.env")

# Reads APIFY_API_KEY
APIFY_API_KEY = os.getenv("APIFY_API_KEY")

OUTPUT_FILE = os.path.join("scratch", "apify_career_page_output.json")

ACTOR_ID = "piotrv1001~company-career-page-scraper"

async def test_apify_career_scraper():
    if not APIFY_API_KEY:
        print("❌ ERROR: APIFY_API_KEY not found in backend/.env")
        return

    # Sync run & fetch dataset items endpoint
    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items"
    params = {"token": APIFY_API_KEY}

    # Payload options for piotrv1001/company-career-page-scraper
    # Apify scrapers typically use 'startUrls' for target URLs
    target_url = "https://careers.google.com/jobs/results/" # Replace with target career page
    payload = {
        "startUrls": [{"url": target_url}]
    }

    print("=" * 75)
    print(f"🚀 TESTING APIFY ACTOR: '{ACTOR_ID}'")
    print(f"🎯 Target URL: {target_url}")
    print(f"🔑 Using Token: {APIFY_API_KEY[:10]}... (from APIFY_API_KEY)")
    print("=" * 75 + "\n")

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            print("🔹 Triggering synchronous Apify Actor run...")
            resp = await client.post(url, params=params, json=payload)
            print(f"   HTTP Status: {resp.status_code}")

            if resp.status_code in [200, 201]:
                items = resp.json()
                if isinstance(items, dict) and "error" in items:
                    print(f"   ❌ Apify Error: {items.get('error')}")
                    results = items
                else:
                    print(f"   ✅ SUCCESS — Received {len(items)} items from Apify!")
                    results = items

                # Save output to scratch/apify_career_page_output.json
                os.makedirs("scratch", exist_ok=True)
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2)

                print("\n" + "=" * 75)
                print(f"💾 SAVED FULL APIFY OUTPUT TO: '{OUTPUT_FILE}'")
                print("=" * 75 + "\n")

            else:
                print(f"   ❌ HTTP Error {resp.status_code}: {resp.text[:300]}")

        except Exception as e:
            print(f"   ❌ Exception: {e}")


if __name__ == "__main__":
    asyncio.run(test_apify_career_scraper())

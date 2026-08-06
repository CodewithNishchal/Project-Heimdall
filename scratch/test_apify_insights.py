"""
Test script: Tests Apify actor 'freshdata/linkedin-company-insights-scraper' on 'Modal' (company_id: 79045818 / modal-labs).
Uses APIFY_INSIGHTS_API_KEY from backend/.env.

Endpoint: POST https://api.apify.com/v2/acts/freshdata~linkedin-company-insights-scraper/run-sync-get-dataset-items?token={APIFY_INSIGHTS_API_KEY}
Saves output to scratch/apify_insights_output.json.
"""
import os
import sys
import json
import asyncio
import httpx
from dotenv import load_dotenv

# Load environment variables from backend/.env
load_dotenv("backend/.env")

# Reads dedicated APIFY_INSIGHTS_API_KEY (falls back to APIFY_API_KEY if not set)
APIFY_INSIGHTS_API_KEY = os.getenv("APIFY_INSIGHTS_API_KEY") or os.getenv("APIFY_API_KEY")

OUTPUT_FILE = os.path.join("scratch", "apify_insights_output.json")

ACTOR_ID = "freshdata~linkedin-company-insights-scraper"


async def test_apify_company_insights():
    if not APIFY_INSIGHTS_API_KEY:
        print("❌ ERROR: APIFY_INSIGHTS_API_KEY not found in backend/.env")
        return

    # Sync run & fetch dataset items endpoint
    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items"
    params = {"token": APIFY_INSIGHTS_API_KEY}

    # Payload options for freshdata/linkedin-company-insights-scraper
    payload = {
        "company_id": "79045818",
        "company_name": "modal-labs"
    }

    print("=" * 75)
    print(f"🚀 TESTING APIFY ACTOR: '{ACTOR_ID}' FOR 'Modal' (company_id: 79045818)")
    print(f"🔑 Using Token: {APIFY_INSIGHTS_API_KEY[:10]}... (from APIFY_INSIGHTS_API_KEY)")
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

                # Save output to scratch/apify_insights_output.json
                os.makedirs("scratch", exist_ok=True)
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2)

                print("\n" + "=" * 75)
                print(f"💾 SAVED FULL APIFY INSIGHTS OUTPUT TO: '{OUTPUT_FILE}'")
                print("=" * 75 + "\n")

            else:
                print(f"   ❌ HTTP Error {resp.status_code}: {resp.text[:300]}")

        except Exception as e:
            print(f"   ❌ Exception: {e}")


if __name__ == "__main__":
    asyncio.run(test_apify_company_insights())

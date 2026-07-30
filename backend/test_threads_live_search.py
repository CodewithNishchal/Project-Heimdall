import asyncio
import os
import sys
import json
import httpx
from datetime import datetime, timezone, timedelta
from dotenv import dotenv_values

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.config_manager import load_intent_config
from backend.config import settings

async def test_threads_live_search():
    print("=" * 75)
    print("THREADS SCRAPECREATORS LIVE SEARCH DIAGNOSTIC TEST")
    print("=" * 75)

    env_vars = dotenv_values("backend/.env")
    api_key = (
        env_vars.get("SCRAPE_CREATORS_API_KEY") or
        os.getenv("SCRAPE_CREATORS_API_KEY") or
        getattr(settings, "SCRAPE_CREATORS_API_KEY", "")
    )

    if not api_key:
        print("❌ Error: SCRAPE_CREATORS_API_KEY is missing from backend/.env")
        return

    print(f"--> Found ScrapeCreators API Key: {api_key[:10]}...")

    # Load active configuration
    config = load_intent_config()
    topics = config.get("social_topics", ["Fractional CMO", "Growth Marketing"])
    triggers = config.get("social_triggers", ["looking for", "need an agency"])

    top1 = topics[0] if topics else "Fractional CMO"
    top2 = topics[1] if len(topics) > 1 else "Growth Marketing"

    # Current queries constructed by social_discovery.py
    current_queries = [
        f"{top1}",               # "Fractional CMO"
        f"{top1} agency",        # "Fractional CMO agency"
        f"{top2}",               # "Growth Marketing"
        f"looking for {top1}",   # "looking for Fractional CMO"
        "agency"                 # "agency" (Broad sanity test)
    ]

    print(f"Current Configured Topics   : {topics}")
    print(f"Current Configured Triggers : {triggers}")
    print(f"Queries to Test             : {current_queries}")
    print("=" * 75)

    url = "https://api.scrapecreators.com/v1/threads/search"
    headers = {
        "x-api-key": api_key
    }

    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    start_date_str = thirty_days_ago.strftime("%Y-%m-%d")
    end_date_str = now.strftime("%Y-%m-%d")

    async with httpx.AsyncClient(timeout=45.0) as client:
        for q in current_queries:
            print(f"\n🔍 [TESTING QUERY]: '{q}'")

            # 1. Test WITH start_date / end_date params
            params_with_dates = {
                "query": q,
                "start_date": start_date_str,
                "end_date": end_date_str
            }
            
            # 2. Test WITHOUT dates (plain query)
            params_no_dates = {
                "query": q
            }

            for p_desc, p_dict in [("WITH DATES", params_with_dates), ("WITHOUT DATES", params_no_dates)]:
                try:
                    resp = await client.get(url, params=p_dict, headers=headers)
                    print(f"   -> [{p_desc}] HTTP {resp.status_code}")
                    if resp.status_code == 200:
                        data = resp.json()
                        items = (
                            data.get("posts") or 
                            data.get("data") or 
                            data.get("threads") or 
                            data.get("results") or 
                            (data if isinstance(data, list) else [])
                        )
                        print(f"      Response Keys: {list(data.keys()) if isinstance(data, dict) else 'List'}")
                        print(f"      Received Items Count: {len(items)}")
                        if items and len(items) > 0:
                            print(f"      ✅ SAMPLE POST: {json.dumps(items[0], indent=2)[:300]}...")
                    else:
                        print(f"      ❌ Error {resp.status_code}: {resp.text[:200]}")
                except Exception as e:
                    print(f"      ❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_threads_live_search())

import asyncio
import httpx
import json
import logging
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.config_manager import load_intent_config
from backend.config import settings

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

async def test_google_ping():
    api_key = settings.SCRAPE_CREATORS_API_KEY
    if not api_key:
        print("Missing SCRAPE_CREATORS_API_KEY in .env!")
        return
        
    print("=" * 70)
    print(f"Pinging ScrapeCreators Google Search API with Key: {api_key[:8]}...")
    print("=" * 70)

    # Load dynamic config
    cfg = load_intent_config()
    triggers = cfg.get("social_triggers", ["looking for", "recommend"])
    topics = cfg.get("social_topics", ["marketing agency"])

    # Construct plain query, e.g. "RFP marketing agency"
    clean_trigs = [t.strip('\'"') for t in triggers if t.strip() and "looking for a" not in t.lower()]
    if not clean_trigs:
        clean_trigs = ["RFP"]
    clean_tops = [tp.strip('\'"') for tp in topics if tp.strip()]
    
    # Using the exact query from your curl command
    query = "RFP digital marketing agency"

    print(f"Constructed Google Query: {query}")
    
    url = "https://api.scrapecreators.com/v1/google/search"
    params = {
        "query": query,
        "date_posted": "last-month",
        "page": 2  # Updated to page 2 as requested
    }
    headers = {
        "x-api-key": api_key
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print(f"Sending GET to {url} with params: {params}")
            resp = await client.get(url, params=params, headers=headers)
            
            if resp.status_code == 200:
                data = resp.json()
                items = (
                    data.get("organic") or 
                    data.get("results") or 
                    data.get("data") or 
                    data.get("posts") or 
                    (data if isinstance(data, list) else [])
                )
                print(f"--> Received {len(items)} posts from Google.\n")
                
                if items:
                    print("RAW ITEM 1:")
                    print(json.dumps(items[0], indent=2))
                
                for i, item in enumerate(items, 1):
                    # Schema mapping for typical Google JSON results
                    title = item.get("title") or item.get("name") or "Unknown"
                    url_val = item.get("url") or item.get("link") or ""
                    snippet = item.get("snippet") or item.get("description") or item.get("content") or ""
                    
                    print(f"[{i}] {title}")
                    print(f"    URL: {url_val}")
                    print(f"    Content: {snippet[:140].replace(chr(10), ' ')}...")
                    print("-" * 50)
            else:
                print(f"Error {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_google_ping())

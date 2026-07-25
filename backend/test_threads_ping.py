import asyncio
import httpx
import json
import logging
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.pipeline.social_discovery import fetch_scrapecreators_threads
from backend.config_manager import load_intent_config
from backend.config import settings

# Disable verbose HTTP logging so console output is clean
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

async def test_threads_ping():
    api_key = settings.SCRAPE_CREATORS_API_KEY
    print("=" * 70)
    print(f"Pinging ScrapeCreators Threads API with Key: {api_key[:8]}...")
    print("=" * 70)

    # Load dynamic config
    cfg = load_intent_config()
    triggers = cfg.get("social_triggers", ["looking for", "recommend"])
    topics = cfg.get("social_topics", ["marketing agency"])

    # Form 2 iterations based on settings
    test_queries = [
        f"{triggers[0]} {topics[0]}",
        f"{triggers[1] if len(triggers) > 1 else 'need a'} {topics[0]}"
    ]

    async with httpx.AsyncClient(timeout=30.0) as client:
        for q in test_queries:
            print("\n" + "=" * 70)
            print(f"  SEARCH QUERY: '{q}'")
            print("=" * 70)
            results = await fetch_scrapecreators_threads(client, q)
            print(f"--> Received {len(results)} posts from Threads.\n")
            
            for i, item in enumerate(results, 1):
                caption = (
                    item.get("caption") or 
                    item.get("text") or 
                    item.get("post_text") or 
                    item.get("content") or ""
                )
                if isinstance(caption, dict):
                    caption = caption.get("text", "")
                
                user = item.get("user", {}) if isinstance(item.get("user"), dict) else {}
                username = user.get("username") or item.get("username") or "threads_user"
                url = item.get("url") or item.get("post_url") or f"https://www.threads.net/@{username}"
                clean_text = str(caption).strip().replace("\n", " ")[:140]

                print(f"[{i}] @{username}")
                print(f"    URL: {url}")
                print(f"    Content: {clean_text}...")
                print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_threads_ping())

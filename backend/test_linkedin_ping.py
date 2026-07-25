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

async def test_linkedin_ping():
    api_key = settings.APIFY_API_KEY
    if not api_key:
        print("Missing APIFY_API_KEY in .env!")
        return
        
    print("=" * 70)
    print(f"Pinging Apify LinkedIn API with Key: {api_key[:8]}...")
    print("=" * 70)

    # Load dynamic config
    cfg = load_intent_config()
    triggers = cfg.get("social_triggers", ["looking for", "recommend"])
    topics = cfg.get("social_topics", ["marketing agency"])

    # Blacklist "looking for a" / "hiring agency" logic
    clean_trigs = [t for t in triggers if "looking for a" not in t.lower() and "hiring agency" not in t.lower()]
    if not clean_trigs:
        clean_trigs = ["RFP", "recommend"]

    clean_tops = topics

    formatted_trigs = [f'"{t}"' for t in clean_trigs]
    trig_clause = f"({' OR '.join(formatted_trigs)})" if len(formatted_trigs) > 1 else formatted_trigs[0]
    
    formatted_tops = [f'"{tp}"' for tp in clean_tops]
    topic_clause = f"({' OR '.join(formatted_tops)})" if len(formatted_tops) > 1 else formatted_tops[0]

    # Combine
    linkedin_query = f"{trig_clause} {topic_clause}"

    # For testing exactly what the user mentioned:
    test_exact_query = '"RFP" "marketing agency"'

    print(f"Constructed LinkedIn Query: {linkedin_query}")
    print("Testing against apimaestro~linkedin-posts-search-scraper-no-cookies ...")

    # Calculate postedLimitDate (1 month ago)
    from datetime import datetime, timedelta
    one_month_ago = datetime.now() - timedelta(days=30)
    limit_date_str = one_month_ago.strftime("%Y-%m-%d")

    # The Actor URL we are currently hitting
    url = f"https://api.apify.com/v2/acts/harvestapi~linkedin-post-search/run-sync-get-dataset-items?token={api_key}"
    
    payload = {
        "maxPosts": 20,
        "postNestedComments": False,
        "postNestedReactions": False,
        "postedLimitDate": limit_date_str,
        "scrapeComments": False,
        "scrapeReactions": False,
        "searchQueries": [test_exact_query]
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            print(f"Sending payload: {json.dumps(payload, indent=2)}")
            resp = await client.post(url, json=payload)
            if resp.status_code in (200, 201):
                data = resp.json()
                items = data if isinstance(data, list) else data.get("data", [])
                print(f"--> Received {len(items)} posts from LinkedIn.\n")
                if items:
                    print("RAW ITEM 1:")
                    print(json.dumps(items[0], indent=2))
                
                for i, item in enumerate(items, 1):
                    # harvestapi~linkedin-post-search JSON schema:
                    author = item.get("author", {})
                    name = author.get("name") or "Unknown"
                    text = item.get("content") or ""
                    post_url = item.get("linkedinUrl") or ""
                    
                    print(f"[{i}] {name}")
                    print(f"    URL: {post_url}")
                    print(f"    Content: {text[:140].replace(chr(10), ' ')}...")
                    print("-" * 50)
            else:
                print(f"Error {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_linkedin_ping())

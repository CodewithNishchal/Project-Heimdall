import asyncio
import os
import sys
import json
import logging
import httpx
from dotenv import load_dotenv

# Ensure root backend dir is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv("backend/.env")

async def test_scrapebadger_reddit():
    print("\n" + "="*65)
    print("🦡 SCRAPEBADGER REDDIT SEARCH TESTER (/v1/reddit/search/posts)")
    print("="*65 + "\n")

    api_key = settings.SCRAPEBADGER_API_KEY or os.getenv("SCRAPEBADGER_API_KEY")
    if not api_key or api_key == "mock_key_if_empty":
        print("❌ Error: SCRAPEBADGER_API_KEY is missing in backend/.env")
        return

    company_name = sys.argv[1].strip() if len(sys.argv) > 1 else "Triomics"
    domain = sys.argv[2].strip() if len(sys.argv) > 2 else "triomics.com"

    # Build the search query
    clean_name = company_name.replace(" Inc.", "").replace(" LLC", "").replace(" Corp", "").strip()
    query = f'"{domain}" OR ("{clean_name}")' if domain else f'"{clean_name}"'

    print(f"Target Company : {company_name}")
    print(f"Target Domain  : {domain}")
    print(f"Exact Query    : {query}")
    print(f"Endpoint       : https://scrapebadger.com/v1/reddit/search/posts\n")

    headers = {"x-api-key": api_key}
    params = {
        "q": query,
        "sort": "relevance"
    }

    print("Fetching posts from ScrapeBadger...")
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            res = await client.get("https://scrapebadger.com/v1/reddit/search/posts", headers=headers, params=params)
            print(f"HTTP Response Status: {res.status_code}\n")

            if res.status_code != 200:
                print(f"❌ ScrapeBadger API Error ({res.status_code}): {res.text}")
                return

            data = res.json()
            posts = data.get("posts") or data.get("data") or []

            print(f"======================================================================")
            print(f"🎉 SCRAPEBADGER REDDIT RESULTS (Total Found: {len(posts)})")
            print(f"======================================================================\n")

            if not posts:
                print("No posts found for this query.")
                return

            for i, p in enumerate(posts, 1):
                title = p.get("title", "No Title")
                sub = p.get("subreddit_name_prefixed") or f"r/{p.get('subreddit', 'unknown')}"
                created = p.get("created_at") or p.get("created_utc", "Unknown")
                score = p.get("score", 0)
                permalink = p.get("permalink", "")
                reddit_url = f"https://reddit.com{permalink}" if permalink else p.get("url", "")
                selftext = p.get("selftext", "").strip()
                snippet = (selftext[:150] + "...") if len(selftext) > 150 else selftext

                print(f"[{i}] {title}")
                print(f"    Subreddit : {sub}")
                print(f"    Posted At : {created}")
                print(f"    Score/Up  : {score}")
                print(f"    Post URL  : {reddit_url}")
                if snippet:
                    print(f"    Snippet   : {snippet}")
                print("-" * 65)

        except Exception as e:
            print(f"❌ Exception occurred: {e}")

if __name__ == "__main__":
    asyncio.run(test_scrapebadger_reddit())

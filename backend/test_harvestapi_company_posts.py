import asyncio
import os
import sys
import json
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from backend.config import settings
from backend.pipeline.enrichment import fetch_harvestapi_linkedin_posts, resolve_domain_via_serper

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv("backend/.env")

async def test_harvestapi_posts():
    print("\n" + "="*70)
    print("🎉 HARVESTAPI LINKEDIN COMPANY POSTS TESTER (harvestapi~linkedin-company-posts)")
    print("="*70 + "\n")

    apify_key = settings.APIFY_API_KEY
    serper_key = settings.SERPER_API_KEY

    if not apify_key or apify_key == "mock_key_if_empty":
        print("❌ Error: APIFY_API_KEY is missing in backend/.env")
        return

    company_name = sys.argv[1].strip() if len(sys.argv) > 1 else "Triomics"

    print(f"Resolving LinkedIn domain and fetching posts for: {company_name}...")
    domain, firmographics = await resolve_domain_via_serper(company_name, serper_key)

    print(f"\n======================================================================")
    print(f"✅ ENTITY RESOLUTION & INFOGRAPHICS RESULT")
    print(f"======================================================================")
    print(f"Domain         : {domain}")
    print(f"Company Name   : {company_name}")
    print(f"LinkedIn URL   : {firmographics.get('linkedin_url')}")
    print(f"Employee Count : {firmographics.get('employee_count')}")
    print(f"Industry       : {firmographics.get('industry')}")
    
    posts = firmographics.get("linkedin_posts", [])
    print(f"\n======================================================================")
    print(f"🎉 HARVESTAPI LINKEDIN POSTS (Total Fetched: {len(posts)})")
    print(f"======================================================================\n")

    for i, p in enumerate(posts, 1):
        content = p.get("content", "").strip()
        snippet = (content[:150] + "...") if len(content) > 150 else content
        posted = p.get("postedAt", {}).get("date") or p.get("postedAt", {})
        eng = p.get("engagement", {})
        likes = eng.get("likes", 0)
        comments = eng.get("comments", 0)
        url = p.get("linkedinUrl") or p.get("socialContent", {}).get("shareUrl")

        print(f"[{i}] Post ID: {p.get('id')}")
        print(f"    Date    : {posted}")
        print(f"    Likes   : {likes} | Comments: {comments}")
        print(f"    URL     : {url}")
        print(f"    Content : {snippet}")
        print("-" * 70)

if __name__ == "__main__":
    asyncio.run(test_harvestapi_posts())

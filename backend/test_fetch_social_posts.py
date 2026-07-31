import asyncio
import json
import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.config_manager import load_intent_config
from backend.pipeline.social_discovery import fetch_social_micro_intent
from backend.pipeline.social_classifier import is_prefiltered

async def run_social_fetch_test():
    print("=" * 90)
    print("🧪 SOCIAL POST FETCHING TEST (ZERO LLM COST)")
    print("=" * 90)

    config = load_intent_config()
    active_niche = config.get("active_niche", "recruitment")
    niche_info = config.get("niches", {}).get(active_niche, {})
    niche_label = niche_info.get("label", "Unknown ICP Target")

    print(f"📌 ACTIVE ICP NICHE  : {active_niche.upper()} ('{niche_label}')")
    print(f"📋 TARGET INDUSTRIES : {', '.join(niche_info.get('target_industries', []))}")
    print(f"👥 HEADCOUNT BOUNDS : {niche_info.get('min_employees')} - {niche_info.get('max_employees')} employees")
    print("=" * 90 + "\n")

    print(f"🚀 Executing live multi-platform social discovery for '{active_niche}'...")
    raw_posts = await fetch_social_micro_intent(triggers=[], topics=[])

    print(f"\n📥 TOTAL RAW POSTS FETCHED: {len(raw_posts)} posts\n")
    print("=" * 90)
    print("📊 PLATFORM BREAKDOWN & REGEX PRE-FILTER RESULTS")
    print("=" * 90)

    platform_counts = {}
    passed_prefilter = []
    skipped_prefilter = []

    for idx, post in enumerate(raw_posts, start=1):
        source = post.get("source_api") or post.get("platform") or "Social"
        platform_counts[source] = platform_counts.get(source, 0) + 1

        content = str(post.get("content") or post.get("raw_text") or post.get("title") or "").strip()
        author = post.get("author") or post.get("company_name") or "Unknown Author"
        url = post.get("url") or post.get("post_url") or "No URL"

        is_skip, matched_pattern = is_prefiltered(content, niche_id=active_niche)

        item_info = {
            "idx": idx,
            "source": source,
            "author": author,
            "content": content[:180].replace("\n", " "),
            "url": url,
            "matched_pattern": matched_pattern
        }

        if is_skip:
            skipped_prefilter.append(item_info)
        else:
            passed_prefilter.append(item_info)

    for plat, count in platform_counts.items():
        print(f"   • {plat:<20}: {count} posts")

    print(f"\n   ✅ Passed Regex Pre-Filter (Candidates for LLM) : {len(passed_prefilter)} posts")
    print(f"   🚫 Skipped by Pre-Filter (Agency promo / Seekers) : {len(skipped_prefilter)} posts")

    print("\n" + "=" * 90)
    print("🔍 SAMPLE CANDIDATE POSTS PASSED TO LLM (TOP 15)")
    print("=" * 90)
    for p in passed_prefilter[:15]:
        print(f"\n[{p['idx']}] [{p['source']}] Author: {p['author']}")
        print(f"    Snippet : \"{p['content']}...\"")
        print(f"    URL     : {p['url']}")

    if skipped_prefilter:
        print("\n" + "=" * 90)
        print("🚫 SAMPLE PRE-FILTERED SKIPPED POSTS (TOP 10)")
        print("=" * 90)
        for p in skipped_prefilter[:10]:
            print(f"\n[{p['idx']}] [{p['source']}] Author: {p['author']}")
            print(f"    Matched Pattern : {p['matched_pattern']}")
            print(f"    Snippet         : \"{p['content']}...\"")

    print("\n" + "=" * 90)
    print("💡 SUMMARY")
    print(f"   • Active Niche        : {active_niche}")
    print(f"   • Total Posts Fetched : {len(raw_posts)}")
    print(f"   • Qualified for LLM   : {len(passed_prefilter)}")
    print(f"   • Pre-Filter Savings  : {len(skipped_prefilter)} LLM calls saved")
    print("=" * 90)

if __name__ == "__main__":
    asyncio.run(run_social_fetch_test())

"""
End-to-End Test Script: Tests fetch_social_micro_intent from backend/pipeline/social_discovery.py
across ALL 5 social discovery providers:
1. LinkedIn (via Apify HarvestAPI)
2. X / Twitter (via ScrapeBadger with US location + past 30 days date lock)
3. Reddit (via ScrapeBadger with US tech hub cities)
4. Threads (via ScrapeCreators with high-volume keywords)
5. Google (via ScrapeCreators)

Saves output to backend/test_social_discovery_all_providers_results.json.
"""
import os
import sys
import asyncio
import json
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.pipeline.social_discovery import fetch_social_micro_intent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestSocialDiscoveryAllProviders")

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "test_social_discovery_all_providers_results.json")


async def main():
    print("\n" + "=" * 70)
    print("🚀 RUNNING END-TO-END SOCIAL DISCOVERY PIPELINE (ALL 5 PROVIDERS)...")
    print("=" * 70 + "\n")

    # Run for active niche recruitment
    results = await fetch_social_micro_intent(
        triggers=["hiring DevOps engineers", "looking for recruiting partner"],
        topics=["Recruitment", "Engineering"]
    )

    print(f"\n" + "=" * 70)
    print(f"✅ PIPELINE COMPLETE — Total Items Fetched Across All Providers: {len(results)}")
    print("=" * 70 + "\n")

    # Group results by platform
    by_platform = {}
    for item in results:
        plat = item.get("platform", "unknown")
        if plat not in by_platform:
            by_platform[plat] = []
        by_platform[plat].append(item)

    for plat, items in by_platform.items():
        print(f"📊 {plat.upper()}: Fetched {len(items)} items")
        for i, it in enumerate(items[:3], 1):
            title = it.get("title") or it.get("text") or it.get("content") or ""
            author = it.get("author") or it.get("user") or "Unknown"
            url = it.get("url") or "N/A"
            print(f"   [{i}] Author: {str(author)[:40]}")
            print(f"       Title : {str(title)[:80]}...")
            print(f"       URL   : {url}\n")

    # Save summary & raw output
    output_payload = {
        "total_items": len(results),
        "platform_counts": {k: len(v) for k, v in by_platform.items()},
        "items": results
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    print(f"💾 SAVED FULL RESULTS TO: {OUTPUT_FILE}\n")


if __name__ == "__main__":
    asyncio.run(main())

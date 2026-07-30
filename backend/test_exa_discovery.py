import asyncio
import json
import time
import logging
from backend.config_manager import load_intent_config
from backend.pipeline.discovery import fetch_exa_candidates_50, apply_deterministic_filter

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TestExaDiscovery")

async def test_exa_discovery():
    print("=" * 70)
    print("🚀 HEIMDALL EXA AI MULTI-QUERY DISCOVERY TEST")
    print("=" * 70)

    config = load_intent_config()
    active_niche = config.get("active_niche", "recruitment_agencies")
    active_subtype = config.get("active_subtype", "tech_recruitment")

    print(f"📌 Active Niche:    {active_niche}")
    print(f"📌 Active Sub-Type: {active_subtype}")
    
    niche_query_key = f"{active_niche.split('_')[0]}_exa_queries" if "_" in active_niche else "marketing_exa_queries"
    if active_niche == "appointment_setting":
        niche_query_key = "appointment_setting_exa_queries"
    elif active_niche == "recruitment_agencies":
        niche_query_key = "recruitment_exa_queries"
        
    query_objs = config.get(niche_query_key, [])
    print(f"🔍 Executing {len(query_objs)} Parallel Queries for '{niche_query_key}':")
    for i, q in enumerate(query_objs, 1):
        print(f"   [{i}] Label: {q.get('label')}")
        print(f"       Query: \"{q.get('query')}\"")

    print("\n⏳ Executing Exa AI discovery sweep...")
    start_time = time.time()
    candidates = await fetch_exa_candidates_50()
    elapsed = time.time() - start_time

    print(f"\n✅ Exa AI Discovery Completed in {elapsed:.2f} seconds.")
    print(f"📦 Total Deduplicated Candidates Returned: {len(candidates)}")

    if not candidates:
        print("⚠️ No candidates returned. Check EXA_API_KEY in backend/.env")
        return

    print("\n" + "-" * 70)
    print("📋 SAMPLE CANDIDATES (Top 5 Results):")
    print("-" * 70)
    for idx, c in enumerate(candidates[:5], 1):
        title = c.get("title") or c.get("company_name") or "Unknown"
        url = c.get("url") or "No URL"
        summary = (c.get("summary") or c.get("text_snippet") or "")[:150].replace("\n", " ")
        print(f"[{idx}] {title}")
        print(f"    URL: {url}")
        print(f"    Summary: {summary}...")
        print()

    print("-" * 70)
    print("🧹 TESTING DETERMINISTIC REGEX PRE-FILTERING ($0 Tokens)")
    print("-" * 70)
    survivors = apply_deterministic_filter(candidates)
    print(f"📊 Filtering Results: {len(candidates)} Raw Candidates -> {len(survivors)} SURVIVORS passed regex category & headcount rules.")

    output_path = "backend/exa_test_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "active_niche": active_niche,
            "active_subtype": active_subtype,
            "execution_time_seconds": round(elapsed, 2),
            "total_candidates": len(candidates),
            "survivors_count": len(survivors),
            "top_10_candidates": candidates[:10],
            "all_candidates": candidates[:150]
        }, f, indent=2)

    print(f"\n💾 Results successfully saved to: {output_path}")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_exa_discovery())

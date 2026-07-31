import asyncio
import json
import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.config_manager import load_intent_config
from backend.pipeline.social_discovery import fetch_social_micro_intent
from backend.pipeline.social_classifier import batch_classify_social_intent, is_prefiltered

async def run_social_llm_test():
    print("=" * 90)
    print("🧪 SOCIAL POST DISCOVERY & LLM CLASSIFICATION TEST")
    print("=" * 90)

    config = load_intent_config()
    active_niche = config.get("active_niche", "recruitment")
    niche_info = config.get("niches", {}).get(active_niche, {})
    niche_label = niche_info.get("label", "Unknown ICP Target")

    print(f"📌 ACTIVE ICP NICHE  : {active_niche.upper()} ('{niche_label}')")
    print(f"📋 TARGET INDUSTRIES : {', '.join(niche_info.get('target_industries', []))}")
    print(f"👥 HEADCOUNT BOUNDS : {niche_info.get('min_employees')} - {niche_info.get('max_employees')} employees")
    print("=" * 90 + "\n")

    # Step 1: Live Social Fetching
    print(f"🚀 [Phase 1] Executing live multi-platform social discovery for '{active_niche}'...")
    raw_posts = await fetch_social_micro_intent(triggers=[], topics=[])
    print(f"📥 Total Raw Posts Fetched: {len(raw_posts)} posts")

    # Step 2: Zero-Cost Regex Pre-Filter Audit
    passed_prefilter = []
    skipped_prefilter = []
    for idx, p in enumerate(raw_posts):
        text = str(p.get("content") or p.get("raw_text") or p.get("title") or "").strip()
        is_skip, matched_pattern = is_prefiltered(text, niche_id=active_niche)
        post_copy = dict(p)
        post_copy["_prefilter_status"] = "SKIPPED" if is_skip else "PASSED"
        post_copy["_matched_pattern"] = matched_pattern if is_skip else None

        if is_skip:
            skipped_prefilter.append(post_copy)
        else:
            passed_prefilter.append(post_copy)

    print(f"   • Passed Pre-Filter (Sent to LLM) : {len(passed_prefilter)} posts")
    print(f"   • Skipped by Regex Pre-Filter      : {len(skipped_prefilter)} posts")

    # Step 3: LLM Classification Phase
    print(f"\n🧠 [Phase 2] Classifying {len(passed_prefilter)} posts using LLM Classifier...")
    classified_leads, usage = await batch_classify_social_intent(raw_posts, return_usage=True)

    print(f"\n📊 LLM CLASSIFICATION RESULTS:")
    print(f"   • Qualified HOT/WARM Leads Matched : {len(classified_leads)} leads")
    print(f"   • Tokens Consumed                  : {usage.get('total_tokens', 0)} tokens")

    # Group qualified leads by classification
    hot_leads = [l for l in classified_leads if l.get("classification") == "HOT"]
    warm_leads = [l for l in classified_leads if l.get("classification") == "WARM"]

    print(f"   • HOT Leads  (High Intent)        : {len(hot_leads)}")
    print(f"   • WARM Leads (Moderate Intent)    : {len(warm_leads)}")

    print("\n" + "=" * 90)
    print("🔥 QUALIFIED LEAD SAMPLES (TOP 10)")
    print("=" * 90)
    for idx, lead in enumerate(classified_leads[:10], start=1):
        author = lead.get("author") or lead.get("company_name") or "Unknown Author"
        source = lead.get("source_api") or lead.get("platform") or "Social"
        cls = lead.get("classification")
        cat = lead.get("category", "social_intent")
        reason = lead.get("reason", "")
        summary = lead.get("summary", "")
        url = lead.get("url") or lead.get("post_url") or "No URL"

        print(f"\n[{idx}] [{cls}] [{cat}] [{source}] Author: {author}")
        print(f"    Reason  : {reason}")
        print(f"    Summary : {summary}")
        print(f"    URL     : {url}")

    # Step 4: Save JSON file with 2 separate objects
    output_filename = os.path.join(os.path.dirname(__file__), "test_social_classification_results.json")
    json_payload = {
        "metadata": {
            "active_niche": active_niche,
            "niche_label": niche_label,
            "total_raw_posts": len(raw_posts),
            "passed_prefilter_count": len(passed_prefilter),
            "skipped_prefilter_count": len(skipped_prefilter),
            "qualified_leads_count": len(classified_leads),
            "hot_leads_count": len(hot_leads),
            "warm_leads_count": len(warm_leads),
            "token_usage": usage
        },
        "raw_fetched_posts": raw_posts,
        "llm_classification_results": classified_leads
    }

    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(json_payload, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 90)
    print(f"💾 RESULTS SAVED TO: {output_filename}")
    print("=" * 90)

if __name__ == "__main__":
    asyncio.run(run_social_llm_test())

import os
import sys
import json
import asyncio

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.config_manager import load_intent_config
from backend.pipeline.social_classifier import batch_classify_social_intent

async def main():
    print("=" * 70)
    print("🧪 OFFLINE SOCIAL POST CLASSIFICATION TEST (USING SAVED POSTS)")
    print("=" * 70)

    results_file = os.path.join(PROJECT_ROOT, "backend", "test_social_posts_results.json")
    if not os.path.exists(results_file):
        print(f"❌ Could not find {results_file}")
        return

    with open(results_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    raw_posts = data.get("raw_posts", [])
    print(f"📦 Loaded {len(raw_posts)} saved raw posts from backend/test_social_posts_results.json")

    config = load_intent_config()
    current_niche = config.get("active_niche", "recruitment_agencies")
    current_subtype = config.get("active_subtype", "startup_tech")

    print(f"Current Configured Niche  : {current_niche}")
    print(f"Current Configured Subtype: {current_subtype}\n")

    # TEST 1: Classify under 'marketing_agencies' niche (since posts are asking for Marketing Agencies)
    print("⏳ Running LLM Classification under 'marketing_agencies' niche...")
    config["active_niche"] = "marketing_agencies"
    config["active_subtype"] = "startup_tech"
    # Temporarily save config to test
    with open(os.path.join(PROJECT_ROOT, "backend", "intent_config.json"), "w", encoding="utf-8") as cf:
        json.dump(config, cf, indent=2)

    marketing_leads = await batch_classify_social_intent(raw_posts[:50])
    print(f"✅ Marketing Agencies Niche Result: {len(marketing_leads)} Qualified HOT/WARM Leads!\n")

    for idx, lead in enumerate(marketing_leads[:5], start=1):
        print(f"{idx}. [{lead.get('platform', '').upper()}] @{lead.get('author_handle')}: {lead.get('classification')} (Confidence: {int(lead.get('confidence', 0)*100)}%)")
        print(f"   Reason: {lead.get('reason')}")
        print(f"   Quote : {lead.get('summary')}\n")

    # TEST 2: Classify under 'recruitment_agencies' niche to show why they were skipped
    print("-" * 70)
    print("⏳ Running LLM Classification under 'recruitment_agencies' niche...")
    config["active_niche"] = "recruitment_agencies"
    config["active_subtype"] = "startup_tech"
    with open(os.path.join(PROJECT_ROOT, "backend", "intent_config.json"), "w", encoding="utf-8") as cf:
        json.dump(config, cf, indent=2)

    recruitment_leads = await batch_classify_social_intent(raw_posts[:50])
    print(f"✅ Recruitment Agencies Niche Result: {len(recruitment_leads)} Qualified Leads (Marketing asks correctly skipped under recruitment ICP).\n")

    # Save summary output
    summary_path = os.path.join(PROJECT_ROOT, "backend", "test_social_classification_comparison.json")
    with open(summary_path, "w", encoding="utf-8") as sf:
        json.dump({
            "raw_posts_tested": min(len(raw_posts), 50),
            "marketing_niche_qualified_leads_count": len(marketing_leads),
            "marketing_niche_leads": marketing_leads,
            "recruitment_niche_qualified_leads_count": len(recruitment_leads),
            "recruitment_niche_leads": recruitment_leads
        }, sf, indent=2)

    print("=" * 70)
    print(f"💾 Full comparison test results saved to: backend/test_social_classification_comparison.json")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())

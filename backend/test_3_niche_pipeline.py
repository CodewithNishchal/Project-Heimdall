"""
Master pipeline verification test for the 3 Niche Architecture:
- Recruitment
- Marketing
- Appointment Setting
Tests Exa multi-query discovery, deterministic Agency Guard filter, Gemini Gatekeeper (Top 20 output), and hybrid scoring in scorer.py.
"""

import os
import sys
import json
import asyncio
import logging
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.config_manager import load_intent_config, save_intent_config
from backend.pipeline.discovery import fetch_exa_candidates_50, apply_deterministic_filter
from backend.pipeline.orchestrator import select_top_20_leads
from backend.pipeline.scorer import process_hybrid_lead_scoring

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Test3NichePipeline")


async def test_pipeline_for_niche(niche_name: str):
    print("=" * 85)
    print(f"🚀 TESTING 3-NICHE PIPELINE FOR: [{niche_name.upper()}]")
    print("=" * 85)

    # 1. Update config for active niche
    config = load_intent_config()
    config["active_niche"] = niche_name
    save_intent_config(config)

    niche_info = config.get("niches", {}).get(niche_name, {})
    print(f"📌 Active Niche Label : {niche_info.get('label')}")
    print(f"📌 Headcount Bounds   : {niche_info.get('min_employees')} - {niche_info.get('max_employees')} employees")
    print(f"📌 Target Industries  : {', '.join(niche_info.get('target_industries', []))}")
    print(f"📌 Agency Exclusions  : {', '.join(niche_info.get('exclude_terms', []))}")

    # Phase 1: Exa AI Multi-Query Discovery
    print("\n⏳ Phase 1: Running Exa AI Discovery Sweep...")
    start_t = time.time()
    candidates = await fetch_exa_candidates_50()
    exa_time = time.time() - start_t
    print(f"✅ Exa AI Discovery returned {len(candidates)} deduplicated candidates in {exa_time:.2f}s.")

    if not candidates:
        print("⚠️ No candidates returned from Exa. Skipping LLM stages.")
        return

    # Phase 2: Deterministic Pre-Filtering + Agency Guard
    print("\n⏳ Phase 2: Running Zero-Token Deterministic Filter & Agency Guard...")
    filter_config = {
        "target_industries": niche_info.get("target_industries", []),
        "min_employees": niche_info.get("min_employees", 20),
        "max_employees": niche_info.get("max_employees", 2000),
        "exclude_terms": niche_info.get("exclude_terms", [])
    }
    survivors = apply_deterministic_filter(candidates, icp_config=filter_config)
    print(f"✅ Filter Results: {len(candidates)} Raw Candidates -> {len(survivors)} SURVIVORS passed headcount, industry, & Agency Guard rules.")

    # Phase 3: Gemini Gatekeeper Top 20 Selection
    print("\n⏳ Phase 3: Running Gemini Gatekeeper Top 20 Selection...")
    gatekeeper_start = time.time()
    top_20 = await select_top_20_leads(survivors[:50], target_niche=niche_name)
    gk_time = time.time() - gatekeeper_start
    print(f"✅ Gemini Gatekeeper completed in {gk_time:.2f}s.")
    print(f"🏆 Top {len(top_20)} Ranked Leads:")
    for idx, lead in enumerate(top_20[:5], 1):
        print(f"   [{idx}] {lead.get('company_name')} | Domain: {lead.get('domain')} | Signal: {lead.get('primary_signal_category')}")

    # Phase 4: Hybrid Lead Scoring Verification (scorer.py)
    print("\n⏳ Phase 4: Verifying Hybrid Scoring Engine (Discrete Recency, Grants, Adjacent Hiring)...")
    mock_payload = {
        "company_name": "Test Scaleup Inc",
        "industry": "B2B SaaS",
        "intent_score": 75,
        "intent_classification": "HOT",
        "adjacent_hiring_gap": True,
        "signal_tags": [
            {"tag": "Series B Funding", "category": "FUNDING"},
            {"tag": "Hiring 10 Engineers", "category": "HIRING"}
        ],
        "signals": [
            {
                "signal_type": "Series B Round",
                "verbatim_quote": "Test Scaleup Inc raised $25M in Series B funding to expand operations.",
                "event_date": "2026-07-15T00:00:00Z",
                "is_grant": False
            },
            {
                "signal_type": "SBIR Innovation Grant",
                "verbatim_quote": "Awarded SBIR research grant for AI automation.",
                "event_date": "2026-07-01T00:00:00Z",
                "is_grant": True
            }
        ],
        "why_now": "Raised $25M Series B funding and active engineering hiring spike.",
        "ai_verdict": "Verified growth company with recent funding and scaling hiring."
    }

    scored_result = process_hybrid_lead_scoring(
        raw_extracted_payload=mock_payload,
        firmographics={"industry": "B2B SaaS", "employee_count": 250},
        raw_source_text="Test Scaleup Inc raised $25M in Series B funding to expand operations. Awarded SBIR research grant for AI automation."
    )

    print(f"✅ Scorer Output Score: {scored_result.get('intent_score')} / 100")
    print(f"   Tier Allocation:    {scored_result.get('tier')}")
    print(f"   ICP Fit Label:      {scored_result.get('icp_fit')}")
    print(f"   Processed Signals:  {len(scored_result.get('signals'))}")
    for sig in scored_result.get("signals"):
        print(f"     - {sig.get('signal_type')} | Recency: {sig.get('recency_label')} | Contribution: +{sig.get('score_contribution')}")

    return {
        "niche": niche_name,
        "exa_time": round(exa_time, 2),
        "gk_time": round(gk_time, 2),
        "raw_candidates": len(candidates),
        "survivors": len(survivors),
        "top_20_count": len(top_20),
        "sample_top_20": top_20[:5],
        "scorer_test": scored_result
    }


async def main():
    print("=" * 85)
    print("🚀 HEIMDALL 3-NICHE ARCHITECTURE MASTER PIPELINE TEST")
    print("=" * 85)

    niches = ["recruitment", "marketing", "appointment_setting"]
    results = {}

    for niche in niches:
        res = await test_pipeline_for_niche(niche)
        results[niche] = res
        print("\n")

    output_path = "backend/test_3_niche_pipeline_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("=" * 85)
    print(f"💾 Master pipeline test results saved to: {output_path}")
    print("=" * 85)


if __name__ == "__main__":
    asyncio.run(main())

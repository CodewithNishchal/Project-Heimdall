import os
import sys
import json
import asyncio

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.config_manager import load_intent_config
from backend.pipeline.discovery import fetch_exa_candidates_50, apply_deterministic_filter

async def main():
    print("=" * 70)
    print("🚀 EXA AI DISCOVERY TEST: HEALTHCARE RECRUITMENT SUB-TYPE")
    print("=" * 70)

    config = load_intent_config()
    niche = config.get("active_niche", "recruitment_agencies")
    subtype = config.get("active_subtype", "healthcare_recruitment")

    subtypes_dict = config.get(f"{niche.split('_')[0]}_subtypes", {}) or config.get("recruitment_subtypes", {})
    subtype_info = subtypes_dict.get(subtype, {})
    
    print(f"Active Niche      : {niche}")
    print(f"Active Sub-Type   : {subtype}")
    print(f"Target Industries : {subtype_info.get('target_industries')}")
    print(f"Headcount Bounds  : {subtype_info.get('min_employees')} - {subtype_info.get('max_employees')}")
    print("-" * 70)

    print("\n⏳ Executing Exa AI Discovery with Sub-Type Context Query Injection...")
    raw_candidates = await fetch_exa_candidates_50()
    print(f"✅ Exa AI returned {len(raw_candidates)} raw candidate company objects.\n")

    filter_config = {
        "allowed_categories": subtype_info.get("target_industries", ["Healthcare", "Biotech", "Pharma", "HealthTech"]),
        "headcount_min": subtype_info.get("min_employees", 50),
        "headcount_max": subtype_info.get("max_employees", 5000)
    }

    print("⏳ Running Phase 2 Deterministic Regex Pre-Filter...")
    survivors = apply_deterministic_filter(raw_candidates, icp_config=filter_config)
    print(f"✅ Filter Completed: {len(survivors)} / {len(raw_candidates)} candidates PASSED as Healthcare Survivors!\n")

    print("=" * 70)
    print(f"📋 TOP HEALTHCARE SURVIVORS (Displaying Top {min(10, len(survivors))}):")
    print("=" * 70)

    for idx, c in enumerate(survivors[:10], start=1):
        print(f"\n{idx}. Company/Title : {c.get('title') or c.get('company_name')}")
        print(f"   URL           : {c.get('url')}")
        print(f"   Category      : {c.get('extracted_category') or 'Matched Allowlist'}")
        print(f"   Headcount     : {c.get('parsed_headcount') or 'Default Bounds'}")
        print(f"   Snippet       : {str(c.get('text_snippet'))[:120]}...")

    output_path = os.path.join(PROJECT_ROOT, "backend", "test_exa_healthcare_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "active_niche": niche,
            "active_subtype": subtype,
            "raw_count": len(raw_candidates),
            "survivor_count": len(survivors),
            "survivors": survivors
        }, f, indent=2)

    print("\n" + "=" * 70)
    print(f"💾 Full test results saved to: backend/test_exa_healthcare_results.json")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())

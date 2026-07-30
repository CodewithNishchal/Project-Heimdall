import os
import json
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PipelineTest")

async def test_master_pipeline():
    print("\n" + "=" * 90)
    print("🚀 TEST: MASTER HEIMDALL PIPELINE UPGRADE (EXA 50 -> REGEX FILTER -> INDEXED GROQ)")
    print("=" * 90)

    from backend.pipeline.discovery import fetch_exa_candidates_50, apply_deterministic_filter
    from backend.pipeline.scorer import analyze_lead_intent_with_llm

    # 1. Exa 50 Candidates
    print("--> Step 1: Fetching 50 Exa AI rank-based candidates...")
    candidates = await fetch_exa_candidates_50()
    print(f"✅ Exa AI fetched {len(candidates)} raw candidates.")

    # 2. Deterministic Pre-Filter
    print("\n--> Step 2: Applying zero-token Regex Category & Headcount Filter...")
    survivors = apply_deterministic_filter(candidates)
    print(f"✅ Deterministic Filter Allowed {len(survivors)} SURVIVORS!")

    # 3. Test Bounded Gatekeeper Selection Logic
    if len(survivors) <= 5:
        print(f"\n--> Step 3: Bounded Gatekeeper: {len(survivors)} survivors <= 5. Bypassing Gemini!")
        winning_leads = survivors
    else:
        print(f"\n--> Step 3: Bounded Gatekeeper: {len(survivors)} survivors > 5. Truncating to Top 15 batch for selection.")
        winning_leads = survivors[:5]

    print("\n" + "=" * 90)
    print("🏆 WINNING TOP LEADS READY FOR ENRICHMENT:")
    print("=" * 90)
    for idx, lead in enumerate(winning_leads, start=1):
        print(f" {idx}. [Rank #{lead.get('original_rank')}] {lead.get('title')}")
        print(f"    Category:  {lead.get('extracted_category')}")
        print(f"    Headcount: {lead.get('parsed_headcount')}")
        print(f"    URL:       {lead.get('url')}\n")

    # 4. Test Indexed Groq Intent Extraction on Winning Lead #1
    if winning_leads:
        top_lead = winning_leads[0]
        company_name = top_lead.get("title") or "Pylon"
        print(f"--> Step 4: Testing Indexed Groq Intent Scoring for '{company_name}'...")
        
        sample_raw_signals = [
            {
                "url": top_lead.get("url"),
                "raw_text": f"Article Text: {top_lead.get('text_snippet') or top_lead.get('summary')}"
            },
            {
                "url": f"{top_lead.get('url')}blog/series-a-funding",
                "raw_text": f"{company_name} recently announced a $15.5 million Series A funding round to accelerate hiring of senior engineers."
            }
        ]

        cleaned_parts = [f"[POST_INDEX: {i}]\n{s['raw_text']}" for i, s in enumerate(sample_raw_signals)]
        cleaned_html = "\n\n---\n\n".join(cleaned_parts)

        firmographics = {
            "employee_count": top_lead.get("parsed_headcount", 50),
            "industry": top_lead.get("extracted_category", "Technology")
        }

        try:
            res = await analyze_lead_intent_with_llm(
                company_name=company_name,
                cleaned_html=cleaned_html,
                firmographics=firmographics,
                icp_fit_label="Strong",
                raw_signals=sample_raw_signals
            )
            print("\n🎉 GROQ INDEXED RESPONSE:")
            print(f"   Intent Score:    {res.get('intent_score')}")
            print(f"   Why Now:         {res.get('why_now')}")
            print(f"   Signals Fetched: {len(res.get('signals', []))}")
            for s in res.get("signals", []):
                print(f"   - Quote: \"{s.get('verbatim_quote')}\"")
                print(f"     Source URL: {s.get('source_url')} (Validated: {s.get('quote_validated')})")
        except Exception as e:
            print(f"⚠️ Groq test error: {e}")

if __name__ == "__main__":
    asyncio.run(test_master_pipeline())

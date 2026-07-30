import os
import sys
import json
import time
import asyncio
from google import genai
from google.genai import types

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.config import settings
from backend.config_manager import load_intent_config

async def run_gemini_gatekeeper(candidates: list[dict], use_grounding: bool = False) -> tuple[list[dict], float]:
    """Runs Gemini Gatekeeper with or without Google Search grounding and measures execution time."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        print("Error: GEMINI_API_KEY is not set.")
        return [], 0.0

    client = genai.Client(api_key=api_key)
    
    tools = [{"google_search": {}}] if use_grounding else []
    gen_config = types.GenerateContentConfig(
        temperature=0.1,
        tools=tools if tools else None
    )

    config_dict = load_intent_config()
    active_niche = config_dict.get("active_niche", "recruitment_agencies")
    active_subtype = config_dict.get("active_subtype", "healthcare_recruitment")
    subtypes_dict = config_dict.get("recruitment_subtypes", {})
    subtype_info = subtypes_dict.get(active_subtype, {})
    subtype_label = subtype_info.get("label", "Healthcare Recruitment")
    subtype_rules = subtype_info.get("rules", "Prioritize healthcare facility expansion.")
    exclude_terms = ", ".join(subtype_info.get("exclude_terms", ["staffing agency", "consultancy"]))

    candidate_blocks = "\n\n".join(
        f"Candidate: {c.get('title', c.get('company_name',''))}\n"
        f"Source URL: {c.get('url','')}\n"
        f"Summary: {c.get('summary', '')}\n"
        f"Snippet: {c.get('text_snippet', c.get('snippet_preview',''))}"
        for c in candidates
    )

    prompt = f"""You are a Lead Scoring AI and Senior B2B Sales Intelligence Analyst.

TASK:
Analyze the attached list of {len(candidates)} candidates along with their source evidence text blocks.
Verify candidates against the Active ICP Niche ('{active_niche}') and Active Sub-Type ('{subtype_label}').

ACTIVE ICP SUB-TYPE RULES & FOCUS:
- Target Sub-Type: {subtype_label}
- Core Evaluation Rule: {subtype_rules}
- Explicit Disqualifications: Discard companies matching any of: {exclude_terms}

OUTPUT FORMAT:
Return ONLY a valid JSON array containing exactly the TOP 5 ranked companies formatted as follows:
[
  {{
    "rank": 1,
    "company_name": "Exact Brand Name",
    "domain": "companydomain.com or null",
    "fits_icp": true,
    "primary_signal_category": "FUNDING | HIRING | EXPANSION",
    "signal_recency": 30
  }}
]

CANDIDATES WITH SOURCE EVIDENCE ({len(candidates)} Candidates):
{candidate_blocks}
"""

    start_time = time.perf_counter()
    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=gen_config
            )
        )
        elapsed = time.perf_counter() - start_time
        
        raw_text = response.text.strip()
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()

        parsed = json.loads(raw_text)
        return parsed, elapsed
    except Exception as e:
        elapsed = time.perf_counter() - start_time
        print(f"Error during execution (Grounding={use_grounding}): {e}")
        return [], elapsed

async def main():
    print("=" * 70)
    print("🚀 GEMINI GATEKEEPER PERFORMANCE BENCHMARK: Grounded vs Ungrounded")
    print("=" * 70)

    # Load mock or real candidate test data
    test_results_path = os.path.join(PROJECT_ROOT, "backend", "exa_regex_filter_test_results.json")
    if os.path.exists(test_results_path):
        with open(test_results_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            candidates = data.get("survivors", [])[:15]
    else:
        candidates = [
            {"title": "Memorial Hospital Systems", "url": "https://memorialhealth.org", "snippet_preview": "Opening 3 new regional clinics and hiring 150 nurses."},
            {"title": "Apex Staffing Agency", "url": "https://apexstaffing.com", "snippet_preview": "Leading healthcare recruitment agency providing temp staff."},
            {"title": "BioTech Innovations", "url": "https://biotech.io", "snippet_preview": "Raised $45M Series B for clinical trials hiring expansion."},
            {"title": "Sunrise Senior Living", "url": "https://sunrisesenior.com", "snippet_preview": "Expanding memory care facilities across Florida."},
            {"title": "HealthFirst Care", "url": "https://healthfirst.org", "snippet_preview": "Adding 50 new clinical staff positions in Q2 2026."}
        ]

    print(f"Loaded {len(candidates)} candidate companies for benchmark evaluation.\n")

    print("⏳ Pass 1: Running Grounded Gemini Gatekeeper (Google Search Tool ENABLED)...")
    grounded_res, grounded_time = await run_gemini_gatekeeper(candidates, use_grounding=True)
    print(f"✅ Grounded Pass Completed in {grounded_time:.2f} seconds.")

    print("\n⏳ Pass 2: Running Fast Ungrounded Gemini Gatekeeper (Google Search Tool DISABLED)...")
    ungrounded_res, ungrounded_time = await run_gemini_gatekeeper(candidates, use_grounding=False)
    print(f"✅ Ungrounded Pass Completed in {ungrounded_time:.2f} seconds.")

    # Calculate Speedup
    time_saved = grounded_time - ungrounded_time
    speedup_pct = (time_saved / grounded_time * 100) if grounded_time > 0 else 0

    print("\n" + "=" * 70)
    print("📊 BENCHMARK COMPARISON SUMMARY")
    print("=" * 70)
    print(f"🐢 Grounded Latency   : {grounded_time:.2f} seconds")
    print(f"⚡ Ungrounded Latency : {ungrounded_time:.2f} seconds")
    print(f"🔥 Time Saved         : {time_saved:.2f} seconds ({speedup_pct:.1f}% faster!)")

    print("\n📋 OUTPUT CONSISTENCY CHECK:")
    print("Top 5 Grounded Winners:")
    for item in grounded_res[:5]:
        print(f"  - Rank {item.get('rank')}: {item.get('company_name')} ({item.get('primary_signal_category')})")

    print("\nTop 5 Ungrounded Winners:")
    for item in ungrounded_res[:5]:
        print(f"  - Rank {item.get('rank')}: {item.get('company_name')} ({item.get('primary_signal_category')})")

    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())

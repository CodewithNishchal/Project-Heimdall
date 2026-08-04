import asyncio
import json
import os
import sys
import logging
from dotenv import load_dotenv

# Ensure root import path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestGeminiMainPipeline")

from backend.pipeline.scorer import analyze_lead_intent_with_llm
from backend.pipeline.orchestrator import _select_top_n_category_reservation, _clean_and_truncate_per_source

# Sample Real-World Evidence Payload (Teliolabs Target)
TEST_COMPANY_NAME = "Teliolabs Communications"
TEST_DOMAIN = "teliolabs.com"
TEST_FIRMOGRAPHICS = {
    "headcount": 180,
    "industry": "Information Technology / IT Services",
    "company_segment": "Scale-up"
}

# Load harvested Exa results if test_exa_current_prompt_output.json exists
EXA_OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "test_exa_current_prompt_output.json")
if os.path.exists(EXA_OUTPUT_FILE):
    with open(EXA_OUTPUT_FILE, "r", encoding="utf-8") as f:
        exa_data = json.load(f)
    
    RAW_PIPELINE_SIGNALS = []
    canonical = exa_data.get("canonical_results", [])
    deep = exa_data.get("deep_signal_results", [])
    
    for item in canonical + deep:
        RAW_PIPELINE_SIGNALS.append({
            "title": item.get("title", "Signal Source"),
            "url": item.get("url", f"https://{TEST_DOMAIN}"),
            "source_type": "Exa Evidence",
            "published_date": item.get("publishedDate") or "2026-06-15T00:00:00.000Z",
            "summary": item.get("summary", ""),
            "text": item.get("text") or item.get("summary") or ""
        })
else:
    RAW_PIPELINE_SIGNALS = [
        {
            "title": "Teliolabs Communications Inc. Overview",
            "url": "https://teliolabs.com/",
            "source_type": "Canonical Website",
            "published_date": "2026-06-15T00:00:00.000Z",
            "summary": "Teliolabs Communications is a privately held IT services company headquartered in South San Francisco, CA, with global teams in US, UK, UAE, and India. Offers AI-driven digital transformation, TelioQuantAI platform, cloud, IoT, and telecom IT services. Headcount ~140 employees.",
            "text": "Teliolabs Communications employs 140 people (+10.6% YoY). Headquartered in South San Francisco, CA, with a presence in the UK and distributed global workforce (India, UAE, UK, US)."
        },
        {
            "title": "TelioLabs appoints Piyush Sarwal as Chief Technology & AI Officer",
            "url": "https://www.expresscomputer.in/news/teliolabs-appoints-piyush-sarwal-as-chief-technology-ai-officer/135873/",
            "source_type": "Press Release / News",
            "published_date": "2026-06-10T10:04:31.000Z",
            "summary": "TelioLabs has appointed Dr. Piyush Sarwal as Chief Technology & AI Officer in June 2026 to lead AI, cloud-native platforms, and oversee product management for TelioQuantAI.",
            "text": "TelioLabs appoints Dr. Piyush Sarwal as Chief Technology & AI Officer in June 2026. Sarwal brings 27+ years telecom/IT experience including CTO role at IBM and VP at Oracle."
        },
        {
            "title": "Jobs & Career Opportunities at Teliolabs",
            "url": "https://teliolabs.com/job-openings/",
            "source_type": "Job Board",
            "published_date": "2026-08-01T00:00:00.000Z",
            "summary": "Teliolabs Communications Inc. has 10+ open IT roles across AI/ML Data Scientist, Data Platform Architect, Oracle BRM Developer, Front End Developer, and Data Engineer.",
            "text": "Active job openings as of August 2026 include AI/ML Data Scientist, Data Platform Architect, Data Engineer, Front End Web Developer, and Oracle BRM Developer across US, Remote, and India."
        },
        {
            "title": "Tracxn TelioLabs Funding & Investor Profile",
            "url": "https://tracxn.com/d/companies/teliolabs/__A5jlsxylx7XC-KZ4gBTBcDPqYNbZvL33V4eko8ouGrg",
            "source_type": "Financial Database",
            "published_date": "2022-04-05T00:00:00.000Z",
            "summary": "TelioLabs raised $133K Angel funding round on April 05, 2022.",
            "text": "Funding history shows $133K total raised across Angel rounds, latest in April 2022."
        }
    ]

async def run_main_pipeline_gemini_test():
    print("\n" + "=" * 75)
    print("🚀 MAIN PIPELINE GEMINI 2.5 FLASH INTEGRATION TEST")
    print(f"Company: {TEST_COMPANY_NAME} ({TEST_DOMAIN})")
    print(f"Loaded {len(RAW_PIPELINE_SIGNALS)} input signals.")
    print("=" * 75 + "\n")

    # Step 1: Simulate Orchestrator Phase 4.5 Top-N Signal Selection
    selected_signals = _select_top_n_category_reservation(RAW_PIPELINE_SIGNALS, max_n=4)
    print(f"1️⃣  Phase 4.5 Top-N Selection Complete:")
    print(f"   • Selected {len(selected_signals)} signals out of {len(RAW_PIPELINE_SIGNALS)} input signals.\n")

    # Step 2: Combine text using exact main pipeline [S0], [S1] formatting (from orchestrator.py)
    cleaned_html_parts = []
    for idx, s in enumerate(selected_signals):
        raw_t = s.get("raw_text") or s.get("text") or s.get("summary") or ""
        src = s.get("source_api") or s.get("source_type") or "Social"
        text = _clean_and_truncate_per_source(raw_t, src)
        cleaned_html_parts.append(f"--- [S{idx}] ---\n{text}")
    cleaned_html = "\n\n---\n\n".join(cleaned_html_parts)

    print("2️⃣  Evidence Text Block Formatted (Orchestrator Standard):")
    print("-" * 50)
    print(cleaned_html[:600] + "\n...[truncated for display]")
    print("-" * 50 + "\n")

    # Step 3: Call Phase 5 Main Pipeline Intent Scoring with Gemini 2.5 Flash
    print("3️⃣  Calling backend.pipeline.scorer.analyze_lead_intent_with_llm (Gemini 2.5 Flash)...")
    scored_result = await analyze_lead_intent_with_llm(
        company_name=TEST_COMPANY_NAME,
        cleaned_html=cleaned_html,
        firmographics=TEST_FIRMOGRAPHICS,
        icp_fit_label="Strong",
        raw_signals=selected_signals
    )

    # Extract pristine raw Gemini output & token metadata
    raw_gemini = scored_result.pop("raw_gemini_output", {})
    token_usage = raw_gemini.get("gemini_token_usage", {})

    output_payload = {
        "raw_gemini_output": raw_gemini,
        "final_scored_output": scored_result
    }

    # Step 4: Output & Save Results
    print("\n" + "=" * 75)
    print("📊 COMPLETE FINAL OUTPUT JSON (RAW GEMINI + HYBRID SCORED)")
    print("=" * 75 + "\n")
    print(json.dumps(output_payload, indent=2, ensure_ascii=False))

    out_file = os.path.join(os.path.dirname(__file__), "test_gemini_pipeline_output.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2, ensure_ascii=False)

    p_toks = token_usage.get("prompt_tokens", "N/A")
    c_toks = token_usage.get("completion_tokens", "N/A")
    th_toks = token_usage.get("thinking_tokens", "N/A")
    t_toks = token_usage.get("total_tokens", "N/A")
    raw_meta = token_usage.get("raw_usage_metadata", {})

    print("\n" + "=" * 75)
    print("📈 GEMINI TOKEN USAGE AUDIT SUMMARY")
    print("=" * 75)
    print(f"  • Prompt Tokens:     {p_toks}")
    print(f"  • Completion Tokens: {c_toks}")
    print(f"  • Thinking Tokens:   {th_toks}")
    print(f"  • Total Tokens:      {t_toks}")
    print("\n🔍 RAW GEMINI API usageMetadata OBJECT:")
    print(json.dumps(raw_meta, indent=2, default=str))
    print("=" * 75)
    print(f"\n✅ Output saved successfully to: {out_file}\n")

if __name__ == "__main__":
    asyncio.run(run_main_pipeline_gemini_test())

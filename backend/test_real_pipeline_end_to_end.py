import asyncio
import json
import os
import sys
import logging
import httpx
from datetime import datetime, timezone
from dotenv import load_dotenv

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from backend.pipeline.scorer import process_hybrid_lead_scoring, validate_quote
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("RealPipelineEndToEndTest")

EXA_API_KEY = os.getenv("EXA_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

async def run_end_to_end_pipeline_test(company_name: str = "Drata", domain: str = "drata.com"):
    print("\n" + "=" * 75)
    print(f"🚀 PROJECT HEIMDALL: END-TO-END PIPELINE AUDIT TESTER")
    print(f"Target Company: {company_name} | Domain: {domain}")
    print("=" * 75 + "\n")

    if not EXA_API_KEY:
        print("❌ ERROR: EXA_API_KEY is not configured in backend/.env!")
        return

    if not GEMINI_API_KEY:
        print("❌ ERROR: GEMINI_API_KEY is not configured in backend/.env!")
        return

    audit_trail = {
        "metadata": {
            "company_name": company_name,
            "domain": domain,
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        "stage_1_exa_output": {},
        "stage_2_gemini_output": {},
        "stage_3_codebase_scorer_output": {},
        "final_pipeline_summary": {}
    }

    # =========================================================================
    # STAGE 1: EXA AI DEEP CONTENT & ARTICLE RETRIEVAL
    # =========================================================================
    print("-------------------------------------------------------------------------")
    print("🔍 STAGE 1: Executing Exa AI Deep Content & Article Retrieval...")
    print("-------------------------------------------------------------------------")

    exa_query = f"{company_name} {domain} company profile headcount funding valuation ARR hiring open positions 2025 2026"
    exa_payload = {
        "query": exa_query,
        "type": "neural",
        "category": "company",
        "numResults": 5,
        "contents": {
            "text": True,
            "summary": True
        }
    }
    exa_headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": EXA_API_KEY
    }

    exa_results = []
    combined_raw_text = ""

    async with httpx.AsyncClient(timeout=45.0) as client:
        try:
            res = await client.post("https://api.exa.ai/search", json=exa_payload, headers=exa_headers)
            res.raise_for_status()
            exa_data = res.json()
            exa_results = exa_data.get("results", [])
            print(f"✅ STAGE 1 SUCCESS: Exa AI returned {len(exa_results)} search results.")

            extracted_items = []
            for item in exa_results:
                title = item.get("title", "No Title")
                url = item.get("url", "")
                summary = item.get("summary", "")
                text_snippet = item.get("text", "")
                
                extracted_items.append({
                    "title": title,
                    "url": url,
                    "summary": summary,
                    "text_snippet_len": len(text_snippet),
                    "text_snippet": text_snippet[:500] + "..." if len(text_snippet) > 500 else text_snippet
                })

                combined_raw_text += f"\n--- SOURCE: {title} ({url}) ---\n"
                if summary:
                    combined_raw_text += f"SUMMARY: {summary}\n"
                if text_snippet:
                    combined_raw_text += f"TEXT: {text_snippet}\n"

            audit_trail["stage_1_exa_output"] = {
                "status": "SUCCESS",
                "query": exa_query,
                "total_results": len(exa_results),
                "harvested_sources": extracted_items,
                "combined_text_character_length": len(combined_raw_text)
            }

        except Exception as e:
            print(f"❌ STAGE 1 FAILED: {e}")
            audit_trail["stage_1_exa_output"] = {"status": "FAILED", "error": str(e)}
            return

    # =========================================================================
    # STAGE 2: GEMINI 2.5 FLASH SIGNAL EXTRACTION & SUMMARIZATION
    # =========================================================================
    print("\n-------------------------------------------------------------------------")
    print("🧠 STAGE 2: Executing Gemini 2.5 Flash Signal Extraction...")
    print("-------------------------------------------------------------------------")

    gemini_system_prompt = """You are a Senior B2B Sales Intelligence Analyst for Tech Recruitment.

CONTEXT:
The input company has already been verified as a valid ICP target. Your job is to analyze the provided search evidence and extract high-value recruitment intent signals.

SIGNAL EXTRACTION RULES:
Classify each signal into one of these exact categories:
1. 'SOCIAL_INTENT': Explicit buyer asks (e.g. "looking for a recruitment firm", "need a headhunter", "need staffing help").
2. 'HIRING_SPIKE': Active hiring surges or open hard-to-fill tech roles (DevOps, Staff Engineer, AI/ML Engineer, SRE).
3. 'FUNDING_RAISE': Recent venture funding, Series A/B/C/D rounds, or debt financing.
4. 'REVENUE_MILESTONE': ARR milestones ($10M+, $50M+, $100M+ ARR, 50%+ YoY revenue growth).
5. 'EXECUTIVE_EXPANSION': C-suite, VP of Engineering, or VP of Talent hires.
6. 'PRODUCT_LAUNCH': Major platform, AI model, or enterprise product launches.

STRICT VERBATIM QUOTE RULE:
- 'verbatim_quote' MUST BE AN EXACT WORD-FOR-WORD SUBSTRING of the provided evidence text. Zero paraphrasing allowed!

REQUIRED JSON OUTPUT FORMAT:
Return a JSON object with:
{
  "company_name": "Exact Brand Name",
  "intent_score": 85,
  "tier": "HOT",
  "ai_verdict": "Executive summary pitch hook...",
  "adjacent_hiring_gap": boolean,
  "signal_tags": [{"category": "FUNDING_RAISE"}, {"category": "HIRING_SPIKE"}],
  "signals": [
    {
      "signal_type": "FUNDING_RAISE",
      "verbatim_quote": "exact word for word quote",
      "source_url": "https://...",
      "event_date": "YYYY-MM-DD"
    }
  ]
}"""

    gemini_user_prompt = f"""Target Company: {company_name}
Target Domain: {domain}

EXA RESEARCH EVIDENCE:
{combined_raw_text[:12000]}

Analyze the evidence and output strictly valid JSON matching the required schema."""

    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    config = types.GenerateContentConfig(
        system_instruction=gemini_system_prompt,
        temperature=0.1,
        response_mime_type="application/json"
    )

    max_retries = 4
    retry_delay = 2.0
    res = None

    for attempt in range(1, max_retries + 1):
        try:
            print(f"Sending Gemini prompt (Attempt {attempt}/{max_retries})...")
            res = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=gemini_user_prompt,
                config=config
            )
            break
        except Exception as err:
            err_msg = str(err)
            if ("503" in err_msg or "UNAVAILABLE" in err_msg or "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg) and attempt < max_retries:
                print(f"⚠️ Gemini 503 High Demand / Capacity error. Retrying in {retry_delay}s... (Attempt {attempt}/{max_retries})")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2.0
            else:
                print(f"❌ STAGE 2 FAILED after {attempt} attempts: {err}")
                audit_trail["stage_2_gemini_output"] = {"status": "FAILED", "error": err_msg}
                return

    try:
        gemini_raw_json = json.loads(res.text)
        print("✅ STAGE 2 SUCCESS: Gemini 2.5 Flash parsed signals successfully.")
        print(f"   -> Gemini Base Score: {gemini_raw_json.get('intent_score')}")
        print(f"   -> Gemini Tier:       {gemini_raw_json.get('tier')}")
        print(f"   -> AI Verdict:        {gemini_raw_json.get('ai_verdict')}")
        print(f"   -> Signals Extracted: {len(gemini_raw_json.get('signals', []))}")

        token_usage = {}
        if hasattr(res, "usage_metadata") and res.usage_metadata:
            token_usage = {
                "prompt_tokens": res.usage_metadata.prompt_token_count,
                "output_tokens": res.usage_metadata.candidates_token_count,
                "total_tokens": res.usage_metadata.total_token_count
            }
            print(f"   -> Tokens Consumed:   Prompt={token_usage['prompt_tokens']} | Output={token_usage['output_tokens']} | Total={token_usage['total_tokens']}")

        audit_trail["stage_2_gemini_output"] = {
            "status": "SUCCESS",
            "model_used": "gemini-2.5-flash",
            "raw_payload": gemini_raw_json,
            "token_usage": token_usage
        }

    except Exception as e:
        print(f"❌ STAGE 2 JSON PARSE FAILED: {e}")
        audit_trail["stage_2_gemini_output"] = {"status": "FAILED", "error": str(e)}
        return


    # =========================================================================
    # STAGE 3: CODEBASE MATH ENGINE (`scorer.py`)
    # =========================================================================
    print("\n-------------------------------------------------------------------------")
    print("⚙️ STAGE 3: Executing Codebase Math Engine (`scorer.py`)...")
    print("-------------------------------------------------------------------------")

    try:
        math_result = process_hybrid_lead_scoring(
            raw_source_text=combined_raw_text,
            raw_extracted_payload=gemini_raw_json,
            firmographics={"industry": "B2B SaaS / Tech", "company_segment": "Scale-up"},
            icp_fit_label="Strong"
        )

        final_score = math_result.get("intent_score")
        assigned_tier = math_result.get("tier")
        intent_class = math_result.get("intent_classification")
        breakdown = math_result.get("scoring_breakdown", {})
        processed_signals = math_result.get("signals", [])

        print("✅ STAGE 3 SUCCESS: Codebase Math Engine complete.")
        print(f"   ► FINAL PIPELINE MATH SCORE: {final_score}")
        print(f"   ► ASSIGNED TIER:            {assigned_tier} ({intent_class})")
        print(f"   ► MATH BREAKDOWN:           {json.dumps(breakdown)}")

        valid_quotes = sum(1 for s in processed_signals if s.get("quote_validated"))
        total_quotes = len(processed_signals)
        print(f"   ► QUOTE ACCURACY:           {valid_quotes}/{total_quotes} Verified Exact Substrings")

        audit_trail["stage_3_codebase_scorer_output"] = {
            "status": "SUCCESS",
            "processed_lead_result": math_result,
            "quotes_accuracy": f"{valid_quotes}/{total_quotes} Verified Substrings"
        }

        # Final Summary
        audit_trail["final_pipeline_summary"] = {
            "company_name": company_name,
            "domain": domain,
            "final_math_score": final_score,
            "tier": assigned_tier,
            "intent_classification": intent_class,
            "stream_to_dashboard": final_score >= 80,
            "ai_verdict": math_result.get("ai_verdict")
        }

    except Exception as e:
        print(f"❌ STAGE 3 FAILED: {e}")
        audit_trail["stage_3_codebase_scorer_output"] = {"status": "FAILED", "error": str(e)}
        return

    # Save full audit trail object to JSON file
    clean_domain_name = domain.replace(".", "_").replace("https://", "").replace("http://", "").strip("/")
    out_file = os.path.join(os.path.dirname(__file__), f"test_real_pipeline_results_{clean_domain_name}.json")
    with open(out_file, "w") as f:
        json.dump(audit_trail, f, indent=2)

    print("\n" + "=" * 75)
    print(f"🎉 END-TO-END REAL PIPELINE TEST COMPLETED SUCCESSFULLY!")
    print(f"📁 Full audit object saved to: {out_file}")
    print("=" * 75 + "\n")

async def main():
    company_name = sys.argv[1] if len(sys.argv) > 1 else "Vanta"
    domain = sys.argv[2] if len(sys.argv) > 2 else "vanta.com"
    await run_end_to_end_pipeline_test(company_name, domain)

if __name__ == "__main__":
    asyncio.run(main())


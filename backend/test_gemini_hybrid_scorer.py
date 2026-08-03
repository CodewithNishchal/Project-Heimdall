import asyncio
import json
import os
import sys
import logging
from datetime import datetime, timezone

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from backend.pipeline.scorer import process_hybrid_lead_scoring
from backend.validation.quote_validator import validate_quote

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestGeminiScorer")

# ======================================================================
# Load Production ICP Rules from intent_config.json
# ======================================================================
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "intent_config.json")
with open(CONFIG_PATH, "r") as f:
    INTENT_CONFIG = json.load(f)

RECRUITMENT_ICP = INTENT_CONFIG["niches"]["recruitment"]


# ======================================================================
# Flattened Schema Structure compatible with Google GenAI SDK
# ======================================================================
class ExtractedSignal(BaseModel):
    signal_type: str = Field(
        description="Must be one of: SOCIAL_INTENT, HIRING_SPIKE, FUNDING_RAISE, REVENUE_MILESTONE, EXECUTIVE_EXPANSION, PRODUCT_LAUNCH, ACQUISITION"
    )
    verbatim_quote: str = Field(
        description="EXACT word-for-word substring quote copied from the source text. Zero hallucination allowed."
    )
    source_url: str = Field(default="")
    event_date: str = Field(default="")

class GeminiScoringPayload(BaseModel):
    company_name: str
    intent_score: int = Field(description="Base AI intent score from 0 to 100")
    tier: str = Field(description="HOT, WARM, or COLD")
    signals: list[ExtractedSignal]
    ai_verdict: str = Field(description="1-2 sentence executive verdict for outreach angle")


# ======================================================================
# Comprehensive Test Companies (Real, Competitor Agency, & Fake/Noisy Posts)
# ======================================================================
TEST_COMPANIES = [
    {
        "name": "Vanta",
        "description": "HIGH INTENT (HOT) — $150M Series D, $300M ARR, 1608 employees (within 50-2000 ICP), hiring 102 roles",
        "firmographics": {"employee_count": 1608, "industry": "B2B SaaS", "company_segment": "Scale-up"},
        "evidence_text": """
=== SOURCE EVIDENCE 0: EXA DISCOVERY ===
Vanta is an automated security compliance and trust management SaaS platform based in San Francisco, CA with 1,608 employees.

=== SOURCE EVIDENCE 1: PRESS RELEASE (BUSINESSWIRE) ===
Date: 2025-07-23
San Francisco, CA — Vanta announced today it has raised $150 Million in Series D funding led by Wellington Management, reaching a $4.15 Billion valuation.
Vanta also reported crossing $300 Million in Annual Recurring Revenue (ARR) in June 2026, representing 69% year-over-year revenue growth.

=== SOURCE EVIDENCE 2: LINKEDIN CAREERS POST ===
Date: 2026-07-28
Title: Vanta is actively hiring for 102 open engineering and product positions!
Text: Vanta is actively recruiting for Senior Software Engineer, Developer Experience (CI/CD, AWS, ECS/Fargate), Staff Engineer, Core Platform, and Senior AI GRC Engineer.

=== SOURCE EVIDENCE 3: REDDIT POST (r/recruitment) ===
Date: 2026-07-30
Text: Looking for a tech recruitment firm to help fill 5 Senior AI Engineer roles at Vanta. Our internal talent team is struggling to keep up with scaling velocity.
"""
    },
    {
        "name": "Apex Staffing Agency",
        "description": "COMPETITOR DISQUALIFICATION (AGENCY GUARD) — Direct Staffing Agency",
        "firmographics": {"employee_count": 45, "industry": "Staffing & Recruiting", "company_segment": "Agency"},
        "evidence_text": """
=== SOURCE EVIDENCE 0: EXA DISCOVERY ===
Apex Staffing Agency is a recruitment firm based in Chicago, IL.

=== SOURCE EVIDENCE 1: WEBSITE ABOUT PAGE ===
Date: 2026-06-01
Text: We are a recruitment agency specializing in IT staffing, executive headhunting, and contract placements. Contact us to hire our recruiters for your hiring needs.
"""
    },
    {
        "name": "Nexus Talent Solutions",
        "description": "FAKE DISGUISED POST — Disguised self-promoting headhunter firm trying to look like a client post",
        "firmographics": {"employee_count": 15, "industry": "HR & Staffing", "company_segment": "Agency"},
        "evidence_text": """
=== SOURCE EVIDENCE 0: LINKEDIN POST ===
Date: 2026-07-15
Text: Scaling your DevOps team fast? As a leading recruitment firm and staffing agency, our talent acquisition firm helps tech companies hire top 1% engineers. DM us for staffing partner services!
"""
    },
    {
        "name": "Generic Cloud Tools",
        "description": "NOISY / LOW INTENT POST — Company with generic social posts, no active hiring or funding",
        "firmographics": {"employee_count": 120, "industry": "Cloud Software", "company_segment": "Growth"},
        "evidence_text": """
=== SOURCE EVIDENCE 0: EXA DISCOVERY ===
Generic Cloud Tools produces internal workflow software for SMBs. Based in Denver, CO.

=== SOURCE EVIDENCE 1: X / TWITTER POST ===
Date: 2026-07-01
Text: Happy Friday from the Generic Cloud Tools team! We love remote work and building great software together.

=== SOURCE EVIDENCE 2: LINKEDIN POST ===
Date: 2026-07-10
Text: Check out our latest blog post on 5 tips for organizing your workspace digitally. No open positions currently available.
"""
    }
]


# ======================================================================
# Gemini Scoring Function with Token Usage Tracking
# ======================================================================
async def test_evaluate_company_with_gemini(company: dict) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not set in environment!")
        return {"error": "Missing GEMINI_API_KEY"}

    client = genai.Client(api_key=api_key)

    system_prompt = f"""You are a Senior B2B Sales Intelligence Analyst specializing in RECRUITMENT AGENCY CLIENT PROSPECTING.

TARGET ICP PROFILE & BOUNDARIES:
- Niche Label: {RECRUITMENT_ICP['label']}
- Target Subvertical: {RECRUITMENT_ICP['target_subvertical']}
- Company Size Target: {RECRUITMENT_ICP['min_employees']} to {RECRUITMENT_ICP['max_employees']} employees.
- Target Industries: {', '.join(RECRUITMENT_ICP['target_industries'])}

HIGH-INTENT BUYER SIGNALS (BOOST SCORE):
- Direct Asks: Mentions of {', '.join(RECRUITMENT_ICP['direct_ask_keywords'][:6])} (Tag as 'SOCIAL_INTENT')
- Pain Points: Signals like {', '.join(RECRUITMENT_ICP['pain_signal_keywords'][:6])} (Tag as 'HIRING_SPIKE')
- Capital & Revenue Milestones: Recent Series A/B/C/D funding or ARR milestones (Tag as 'FUNDING_RAISE' / 'REVENUE_MILESTONE')

COMPETITOR DISQUALIFICATION RULES (LOCK SCORE TO 0):
- Disqualify any company that self-identifies as a competitor staffing firm, recruitment agency, or headhunter: {', '.join(RECRUITMENT_ICP['negative_keywords'][:6])}.
- If disqualified as a competitor agency, set intent_score to 0, tier to COLD, and return empty signals list.

STRICT VERBATIM QUOTE RULE:
- 'verbatim_quote' MUST BE AN EXACT WORD-FOR-WORD SUBSTRING of the evidence text. Zero paraphrasing allowed!

REQUIRED JSON OUTPUT FORMAT:
Return a JSON object with:
- "company_name": string
- "intent_score": integer (0 to 100)
- "tier": "HOT" | "WARM" | "COLD"
- "ai_verdict": string
- "signals": list of objects, each containing ("signal_type", "verbatim_quote", "source_url", "event_date")
"""

    user_content = f"""Evaluate Company: {company['name']}
Firmographics: {json.dumps(company['firmographics'])}

RAW SOURCE EVIDENCE TEXT:
{company['evidence_text']}
"""

    logger.info(f"Sending Gemini prompt for '{company['name']}'...")

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{system_prompt}\n\n{user_content}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
        )

        raw_json = json.loads(response.text)

        # -------------------------------------------------------------
        # Extract Token Usage Metadata
        # -------------------------------------------------------------
        prompt_tokens = 0
        output_tokens = 0
        total_tokens = 0

        if hasattr(response, "usage_metadata") and response.usage_metadata:
            prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
            output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
            total_tokens = getattr(response.usage_metadata, "total_token_count", 0) or (prompt_tokens + output_tokens)

        token_summary = {
            "prompt_tokens": prompt_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens
        }

        # -------------------------------------------------------------
        # Verbatim Quote Validation Step
        # -------------------------------------------------------------
        valid_quotes_count = 0
        signals_list = raw_json.get("signals", [])
        total_quotes = len(signals_list)

        for sig in signals_list:
            quote = sig.get("verbatim_quote", "")
            is_valid = validate_quote(quote, company["evidence_text"])
            sig["quote_verified"] = is_valid
            if is_valid:
                valid_quotes_count += 1
            else:
                logger.warning(f"❌ Hallucinated quote detected: '{quote}'")

        # -------------------------------------------------------------
        # Post-Processing Math Scorer Step
        # -------------------------------------------------------------
        final_score_result = process_hybrid_lead_scoring(
            raw_extracted_payload=raw_json,
            firmographics=company["firmographics"],
            raw_source_text=company["evidence_text"],
            icp_fit_label="Strong"
        )

        return {
            "company_name": company["name"],
            "gemini_raw_payload": raw_json,
            "quotes_accuracy": f"{valid_quotes_count}/{total_quotes} Verified Substrings" if total_quotes > 0 else "N/A (No signals)",
            "token_usage": token_summary,
            "post_processed_result": final_score_result
        }

    except Exception as e:
        logger.error(f"Error calling Gemini for '{company['name']}': {e}", exc_info=True)
        return {"error": str(e)}


# ======================================================================
# Main Execution Runner
# ======================================================================
async def main():
    print("==================================================================")
    print("   PROJECT HEIMDALL: GEMINI RECRUITMENT ICP SCORER TEST SUITE    ")
    print("==================================================================\n")

    results = []
    total_prompt_tokens = 0
    total_output_tokens = 0
    total_all_tokens = 0

    for comp in TEST_COMPANIES:
        print(f"\nEvaluating Company: {comp['name']}...")
        res = await test_evaluate_company_with_gemini(comp)
        results.append(res)
        
        print("-" * 65)
        print(f"Company: {comp['name']} ({comp['description']})")
        if "gemini_raw_payload" in res:
            usage = res.get("token_usage", {})
            prompt_toks = usage.get("prompt_tokens", 0)
            out_toks = usage.get("output_tokens", 0)
            tot_toks = usage.get("total_tokens", 0)

            total_prompt_tokens += prompt_toks
            total_output_tokens += out_toks
            total_all_tokens += tot_toks

            print(f"Base AI Score: {res['gemini_raw_payload'].get('intent_score')}")
            print(f"Quote Verification: {res['quotes_accuracy']}")
            print(f"Final Post-Processed Score: {res['post_processed_result'].get('final_score')}")
            print(f"Final Tier: {res['post_processed_result'].get('tier')}")
            print(f"Tokens Used: Input={prompt_toks} | Output={out_toks} | Total={tot_toks}")
            print(f"AI Verdict: {res['gemini_raw_payload'].get('ai_verdict')}")
        else:
            print(f"Error: {res.get('error')}")
        print("-" * 65)

    # -------------------------------------------------------------
    # Aggregate Token Usage Summary Log
    # -------------------------------------------------------------
    num_companies = len(TEST_COMPANIES)
    avg_tokens = round(total_all_tokens / num_companies, 1) if num_companies > 0 else 0

    # Pricing estimation (Gemini 2.5 Flash: ~$0.075 / 1M input, ~$0.30 / 1M output)
    est_cost_input = (total_prompt_tokens / 1_000_000) * 0.075
    est_cost_output = (total_output_tokens / 1_000_000) * 0.30
    est_total_cost = est_cost_input + est_cost_output

    print("\n" + "=" * 65)
    print("                📊 TOKEN USAGE LOG & COST SUMMARY               ")
    print("=" * 65)
    print(f"Total Companies Evaluated:   {num_companies}")
    print(f"Total Input (Prompt) Tokens: {total_prompt_tokens:,}")
    print(f"Total Output (Gen) Tokens:   {total_output_tokens:,}")
    print(f"Total Combined Tokens:       {total_all_tokens:,}")
    print(f"Average Tokens / Company:    {avg_tokens:,} tokens")
    print(f"Estimated Execution Cost:    ${est_total_cost:.6f} USD")
    print("=" * 65 + "\n")

    # Save summary results
    output_filepath = os.path.join(os.path.dirname(__file__), "test_gemini_hybrid_results.json")
    with open(output_filepath, "w") as f:
        json.dump(results, f, indent=2)
    print(f"✅ Full test results saved to: {output_filepath}")

if __name__ == "__main__":
    asyncio.run(main())

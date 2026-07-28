import json
from google import genai
from google.genai import types
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from backend.pipeline.time_decay import calculate_time_decay
from backend.pipeline.icp_filter import apply_icp_filters
from backend.validation.quote_validator import validate_quote
from backend.config import settings
import logging

logger = logging.getLogger(__name__)


# ======================================================================
# Pydantic data interface structures
# Keys align with the Strict Data Contract Protocol
# ======================================================================

class ExtractedSignal(BaseModel):
    signal_type: str
    verbatim_quote: str
    source_url: str = ""
    event_date: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class GeminiScoringPayload(BaseModel):
    company_name: str
    intent_score: int
    tier: str
    signals: list[ExtractedSignal]
    ai_verdict: str


def process_hybrid_lead_scoring(
    raw_extracted_payload: dict,
    firmographics: dict,
    raw_source_text: str = ""
) -> dict:
    """
    Combines LLM data extractions with mathematical operational
    adjustments and structural filter rules.

    Returns a dict with keys aligned to the Strict Data Contract Protocol.
    """
    base_ai_score = raw_extracted_payload.get("intent_score", 50)
    running_score = 0.0
    signals_processed = []
    total_multipliers = 0.0

    # Calculate signal weights combined with individual time decays
    for sig in raw_extracted_payload.get("signals", []):
        sig_type = sig.get("signal_type")

        # Dynamic base weight (since keywords are custom now, we give a solid baseline)
        base_weight = 25.0

        decay_mult, recency_label = calculate_time_decay(
            sig.get("event_date", "")
        )
        total_multipliers += decay_mult

        contribution = base_weight * decay_mult
        running_score += contribution

        # Build signal dict matching the Strict Data Contract
        is_valid, sim_score = validate_quote(
            sig.get("verbatim_quote", ""), raw_source_text
        )
        if not is_valid:
            running_score -= 10

        signals_processed.append({
            "signal_type": sig_type,
            "verbatim_quote": sig.get("verbatim_quote", ""),
            "quote_validated": is_valid,
            "similarity_score": round(sim_score, 1),
            "source_url": sig.get("source_url", ""),
            "recency_label": recency_label,
            "score_contribution": round(contribution, 1),
        })

    # Compute systemic baseline score (Direct Gemini AI score pass-through)
    aggregated_base = float(base_ai_score)

    # Social Intelligence Boost (Segment B protection: 0 ads is a buying trigger for Paid Ads)
    if "Scrape Creators Ad & Social Audit" in raw_source_text:
        aggregated_base += 10.0  # Reward verified social intelligence data

    # Apply transactional structural filter modifiers (Fix 3)
    final_intent_score, icp_fit_label = apply_icp_filters(
        base_score=aggregated_base,
        employee_count=firmographics.get("employee_count"),
        funding_stage=firmographics.get("funding_stage"),
        industry=firmographics.get("industry", "Unknown")
    )

    # Enforce algorithmic score categorization bands
    if final_intent_score >= 70:
        assigned_tier = "High"
    elif final_intent_score >= 40:
        assigned_tier = "Medium"
    else:
        assigned_tier = "Low"

    avg_freshness = (
        int((total_multipliers / len(signals_processed) * 100))
        if signals_processed else 100
    )

    ai_verdict = raw_extracted_payload.get("ai_verdict", "Review signals for outreach context.")
    if isinstance(ai_verdict, list):
        ai_verdict = " ".join([str(v) for v in ai_verdict])

    extracted_industry = raw_extracted_payload.get("industry") or firmographics.get("industry", "Technology & Services")

    return {
        "company_name": raw_extracted_payload.get("company_name"),
        "industry": extracted_industry,
        "intent_score": final_intent_score,
        "signal_freshness": min(avg_freshness, 100),
        "tier": assigned_tier,
        "icp_fit": icp_fit_label,
        "signals": signals_processed,
        "why_now": raw_extracted_payload.get("why_now", "Intent signals detected"),
        "ai_verdict": ai_verdict
    }


async def analyze_lead_intent_with_llm(
    company_name: str,
    cleaned_html: str,
    firmographics: dict
) -> dict:
    """
    Calls Groq API to extract signals and then applies hybrid scoring.
    """
    import os
    import httpx
    from dotenv import dotenv_values
    
    env_vars = dotenv_values("backend/.env")
    groq_key = env_vars.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", "")

    if groq_key:
        for attempt in range(2):
            try:
                config_path = os.path.join(os.path.dirname(__file__), "..", "intent_config.json")
                keywords = ["growth", "hiring", "funding", "expansion"]
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        intent_cfg = json.load(f)
                        keywords = intent_cfg.get("extraction_keywords", keywords)
                    
                keywords_str = ", ".join(keywords)

                prompt = f"""
Analyze {company_name} using the provided text below.

=== INPUT TEXT ===
{cleaned_html}
==================

TARGET KEYWORDS: [{keywords_str}]

TASK:
Extract intent signals matching the TARGET KEYWORDS and calculate a composite intent score.

STRICT EXTRACTION RULES:
1. verbatim_quote: MUST be a 100% exact, contiguous word-for-word substring copied directly from the INPUT TEXT. Do NOT paraphrase, fix typos, reformat, or alter capitalization/punctuation, or validation will fail.
2. source_url: Copy the exact URL from the `[Source URL: ...]` tag immediately preceding the text block where the quote was found.
3. Zero Signals Handling: If NO text matches the target keywords, return `"signals": []` and `"intent_score": 0`. Do NOT force or invent quotes if no match exists.
4. intent_score: Calculate an integer from 0-100 based on this strict rubric:
   - 0: No matching keywords or intent found.
   - 1-40: Weak, indirect, or generic brand mentions.
   - 41-75: Moderate intent (general hiring, active feature discussions, growth chatter).
   - 76-100: High actionable intent (recent funding rounds, direct vendor/agency requests, C-level expansion announcements).

OUTPUT JSON SCHEMA:
{{
  "company_name": "{company_name}",
  "industry": "Specific Industry Name (e.g. EdTech, B2B SaaS, E-Commerce, Healthcare, FinTech, Retail)",
  "intent_score": 85,
  "signals": [
    {{
      "signal_type": "Exact keyword or topic matched",
      "verbatim_quote": "Exact word-for-word string copied directly from text",
      "source_url": "https://example.com/source-link",
      "event_date": "YYYY-MM-DD"
    }}
  ],
  "ai_verdict": "A highly specific 2-3 sentence summary. Sentence 1: explicitly state the verified intent triggers (e.g. funding amount, exact hiring roles, growth metrics) found in the text. Sentence 2-3: propose a specific, actionable sales outreach strategy tailored to the target keywords."
}}
"""

                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {
                            "role": "system", 
                            "content": (
                                "You are a strict, ultra-precise JSON data extraction engine. "
                                "Output raw JSON ONLY. Do not include markdown code blocks (```json), preambles, reasoning, or explanatory text."
                            )
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"}
                }

                async with httpx.AsyncClient(timeout=45.0) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    
                resp_data = response.json()
                raw_text = resp_data["choices"][0]["message"].get("content")
                if not raw_text:
                    raise ValueError("Groq returned empty content")
                # Clean up potential markdown formatting from the response
                if raw_text.startswith("```json"):
                    raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                elif raw_text.startswith("```"):
                    raw_text = raw_text.split("```")[1].split("```")[0].strip()
                    
                token_usage = resp_data.get("usage", {}).get("total_tokens", "Unknown")
                logger.info(f"Groq Token Usage for {company_name}: {token_usage}")
                
                raw_payload = json.loads(raw_text)
                raw_payload["company_name"] = company_name
                return process_hybrid_lead_scoring(raw_payload, firmographics, cleaned_html)

            except Exception as e:
                logger.warning(f"[Scorer] Groq API attempt {attempt + 1} failed: {e}.")
                if attempt == 1:
                    logger.warning("[Scorer] Falling back to rule-based scoring.")

    # Rule-Based Fallback when API key is missing or fails
    extracted_signals = []
    text_lower = cleaned_html.lower()
    kw_list = ["hiring", "sdr", "series a", "seed", "funding", "raised", "expansion", "redesign", "meta ads", "shopify"]
    found_matches = [kw for kw in kw_list if kw in text_lower]
    
    for match in found_matches[:4]:
        extracted_signals.append({
            "signal_type": f"{match}_detected",
            "verbatim_quote": f"Detected high-intent indicator '{match}' in public brand signals.",
            "source_url": f"https://{company_name.lower().replace(' ', '')}.com",
            "event_date": datetime.now(timezone.utc).isoformat()
        })

    fallback_score = min(50 + (len(found_matches) * 12), 95)
    fallback_payload = {
        "company_name": company_name,
        "intent_score": fallback_score,
        "signals": extracted_signals,
        "why_now": f"Matched {len(found_matches)} core intent triggers in public discovery sweeps.",
        "ai_verdict": f"[Groq API limit exhausted] Public intent signals detected for {company_name} (including {', '.join(found_matches[:2]) if found_matches else 'general growth'}). Recommend targeted outreach highlighting how your services can support their recent growth."
    }

    return process_hybrid_lead_scoring(fallback_payload, firmographics, cleaned_html)

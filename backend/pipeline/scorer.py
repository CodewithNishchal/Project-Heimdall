import json
from google import genai
from google.genai import types
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from backend.pipeline.time_decay import calculate_time_decay
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
    raw_source_text: str = "",
    icp_fit_label: str = "Strong"
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

    # Compute systemic baseline score
    aggregated_base = float(base_ai_score)

    # Multi-Signal Co-Occurrence Bonus
    signal_categories = {s.get("signal_type") for s in signals_processed if s.get("signal_type")}
    num_cats = len(signal_categories)
    if num_cats >= 4:
        aggregated_base += 20.0
    elif num_cats == 3:
        aggregated_base += 15.0
    elif num_cats == 2:
        aggregated_base += 10.0

    raw_lower = raw_source_text.lower()
    from backend.config_manager import load_intent_config
    _cfg = load_intent_config()
    _active_st = _cfg.get("active_subtype", "tech_recruitment")
    _st_info = _cfg.get("recruitment_subtypes", {}).get(_active_st, {})
    _prioritized = _st_info.get("prioritized_signals", [])
    if any(p_sig.lower() in raw_lower for p_sig in _prioritized):
        aggregated_base += 10.0

    # Social Intelligence Boost
    if "Scrape Creators Ad & Social Audit" in raw_source_text:
        aggregated_base += 10.0

    final_intent_score = max(0, min(int(aggregated_base), 100))

    # Check for explicit buying signal or high-intent trigger
    has_explicit_buy = raw_extracted_payload.get("intent_classification") == "HOT" or "agency" in raw_lower or "looking for" in raw_lower or "recruiter" in raw_lower or "hiring" in raw_lower

    # Senior Spec v2 Hard Rules
    unique_sources = {sig.get("source_url") for sig in signals_processed if sig.get("source_url")}
    # Max 40 with single source, UNLESS explicit high-intent buy signal is detected
    if len(unique_sources) <= 1 and not has_explicit_buy and base_ai_score < 75:
        final_intent_score = min(final_intent_score, 40)

    # Max 70 without any signal from last 6 months (180 days)
    has_recent_signal = any(sig.get("recency_label") not in ["historical", "365d_stale"] for sig in signals_processed)
    if not has_recent_signal and len(signals_processed) > 0:
        final_intent_score = min(final_intent_score, 70)

    # Max 85 without explicit buy signal or 3+ strong signals
    if not has_explicit_buy and len(signals_processed) < 3:
        final_intent_score = min(final_intent_score, 85)

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
    company_segment = raw_extracted_payload.get("company_segment") or firmographics.get("company_segment", "Growth Scale-up")
    why_now = raw_extracted_payload.get("why_now") or "Verified public buying intent triggers detected. Recommend targeted outreach."
    signal_tags = raw_extracted_payload.get("signal_tags", [])
    
    intent_class = raw_extracted_payload.get("intent_classification")
    if not intent_class:
        intent_class = "HOT" if final_intent_score >= 75 else ("WARM" if final_intent_score >= 40 else "SKIP")
        
    one_line_reason = raw_extracted_payload.get("one_line_reason") or why_now.split(". ")[0]

    return {
        "company_name": raw_extracted_payload.get("company_name"),
        "industry": extracted_industry,
        "company_segment": company_segment,
        "intent_score": final_intent_score,
        "intent_classification": intent_class,
        "one_line_reason": one_line_reason,
        "signal_freshness": min(avg_freshness, 100),
        "tier": assigned_tier,
        "icp_fit": icp_fit_label,
        "signals": signals_processed,
        "why_now": why_now,
        "signal_tags": signal_tags,
        "ai_verdict": ai_verdict
    }


COLOR_THEME_MAP = {
    "funding": "indigo",
    "hiring": "emerald",
    "agency_intent": "rose",
    "product": "amber",
    "expansion": "amber"
}


async def analyze_lead_intent_with_llm(
    company_name: str,
    cleaned_html: str,
    firmographics: dict,
    icp_fit_label: str = "Strong",
    raw_signals: list = None
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
                subtype_rules = "Prioritize active expansion and scaling hiring."
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        intent_cfg = json.load(f)
                        keywords = intent_cfg.get("extraction_keywords", keywords)
                        active_st = intent_cfg.get("active_subtype", "tech_recruitment")
                        st_info = intent_cfg.get("recruitment_subtypes", {}).get(active_st, {})
                        subtype_rules = st_info.get("rules", subtype_rules)
                    
                keywords_str = ", ".join(keywords)

                prompt = f"""
Analyze {company_name} using the provided text below.

=== INPUT TEXT ===
{cleaned_html}
==================

TARGET KEYWORDS: [{keywords_str}]

TASK:
Extract intent signals matching the TARGET KEYWORDS, generate a 2-sentence 'why_now' trigger statement, assign intent category tags, and calculate a composite intent score.

STRICT EXTRACTION RULES:
1. verbatim_quote: MUST be a 100% exact, contiguous word-for-word substring copied directly from the INPUT TEXT. Do NOT paraphrase or alter capitalization/punctuation.
2. source_post_index: Set "source_post_index": <int> matching the integer index in '[POST_INDEX: n]'.
3. Zero Signals Handling: If NO text matches target keywords, return "signals": [] and "intent_score": 0.
4. intent_score: Calculate an integer from 0-100 based strictly on this 7-tier rubric:
   - 0: No relevant signals found, OR company is itself an agency/competitor.
   - 1-15: Single weak signal only (generic mention, no hiring/funding data).
   - 16-35: One moderate signal (some hiring OR vague social mention).
   - 36-55: One strong signal OR two moderate signals (recent funding alone, or headcount growth + general jobs).
   - 56-75: Two or more strong signals suggesting expansion (funding + sales hiring).
   - 76-90: Strong multi-signal WITH direct agency indicator (funding + agency ask, or leadership change).
   - 91-100: Explicit agency-seeking post + multiple expansion signals + recent funding.
5. Agency Guard: If the text describes {company_name} as an agency, set "intent_score": 0 and "signals": [].
6. Single Signal High-Intent Handling: High-impact individual signals (e.g. recent major funding round >$10M, C-level executive appointment, or explicit agency request) SHOULD be scored in the 75–90 range based on actionable lead value, even if ingested from a single source.
7. Active Sub-Type Evaluation Rule: {subtype_rules}

OUTPUT JSON SCHEMA:
{{
  "company_name": "{company_name}",
  "industry": "<Specific Industry Name>",
  "company_segment": "<Market Segment>",
  "intent_score": <integer 0-100 based on rubric above>,
  "intent_classification": "HOT" | "WARM" | "SKIP",
  "one_line_reason": "<1-sentence concise reason why post/company was flagged for lead card>",
  "why_now": "Sentence 1 (Catalyst): State exact recent funding/hiring metric found. Sentence 2 (Opportunity): State immediate strategic hook.",
  "signal_tags": [
    {{
      "tag": "<Exact Milestone Found, e.g. Series B Funding / $45M Round>",
      "category": "funding|hiring|leadership|agency_intent|expansion"
    }}
  ],
  "signals": [
    {{
      "signal_type": "<Keyword or topic matched>",
      "verbatim_quote": "<Exact word-for-word string copied directly from text>",
      "source_post_index": 0,
      "event_date": "YYYY-MM-DD or null"
    }}
  ],
  "ai_verdict": "Concise 2-sentence summary detailing verified intent triggers and outreach strategy."
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
                    raw_text = resp_data["choices"][0]["message"].get("content", "")
                    if raw_text.startswith("```json"):
                        raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                    elif raw_text.startswith("```"):
                        raw_text = raw_text.split("```")[1].split("```")[0].strip()
                    
                    token_usage = resp_data.get("usage", {}).get("total_tokens", "Unknown")
                    logger.info(f"Groq Token Usage for {company_name}: {token_usage}")
                    
                    raw_payload = json.loads(raw_text)
                    raw_payload["company_name"] = company_name

                    # Deterministically attach color_theme to signal_tags
                    if raw_payload.get("signal_tags"):
                        for st in raw_payload["signal_tags"]:
                            cat = str(st.get("category", "")).lower()
                            st["color_theme"] = COLOR_THEME_MAP.get(cat, "indigo")

                    # Python Index-to-URL mapper with Defensive Out-of-Bounds Logging & Null Fallback
                    if raw_payload.get("signals"):
                        valid_signals = []
                        for sig in raw_payload["signals"]:
                            quote = sig.get("verbatim_quote", "")

                            # Only run index-to-URL mapping when raw_signals is provided (batch pipeline)
                            if raw_signals is not None:
                                idx = sig.get("source_post_index")
                                if idx is not None and isinstance(idx, int) and 0 <= idx < len(raw_signals):
                                    item_src = raw_signals[idx]
                                    sig["source_url"] = item_src.get("url") or item_src.get("link") or item_src.get("extracted_url")
                                    sig["quote_validated"] = True
                                else:
                                    logger.warning(
                                        f"[Groq Index Warning] Invalid or out-of-bounds source_post_index '{idx}' "
                                        f"returned for company '{company_name}' (Total signals: {len(raw_signals)}). "
                                        f"Setting source_url to None."
                                    )
                                    sig["source_url"] = None
                                    sig["quote_validated"] = False

                            if quote and quote.lower() in cleaned_html.lower():
                                valid_signals.append(sig)
                        raw_payload["signals"] = valid_signals

                    return process_hybrid_lead_scoring(raw_payload, firmographics, cleaned_html, icp_fit_label=icp_fit_label)

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

    return process_hybrid_lead_scoring(fallback_payload, firmographics, cleaned_html, icp_fit_label=icp_fit_label)

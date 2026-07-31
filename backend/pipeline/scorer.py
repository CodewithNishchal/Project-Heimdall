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
    Applies exact mathematical score post-processing:
    - Discrete recency multipliers (1.5x down to 0.1x)
    - Grant 0.6x weight vs equity funding
    - Adjacent Hiring Bonus (+10)
    - Multi-Signal Bonus (+10, +15, +20)
    - Funding recency degradation (85 -> 60 -> 35)
    - Hard Rules caps (40, 70, 85)
    """
    base_ai_score = raw_extracted_payload.get("intent_score", 50)
    running_score = float(base_ai_score)
    signals_processed = []

    import re
    date_match = re.search(r'Date:\s*(\d{4}-\d{2}-\d{2})', raw_source_text)
    fallback_date_str = date_match.group(1) if date_match else None

    # Pre-normalize text for robust position matching
    clean_source = re.sub(r'\s+', ' ', raw_source_text.strip().lower()) if raw_source_text else ""
    raw_lower = raw_source_text.lower() if raw_source_text else ""

    # 1. Discrete Recency Multipliers & Grant Weighting
    for sig in raw_extracted_payload.get("signals", []):
        sig_type = sig.get("signal_type", "")
        quote = sig.get("verbatim_quote", "")
        
        # FIX 3: Per-signal date resolution with robust short quote position lookup
        sig_date_str = sig.get("event_date")
        if not sig_date_str and quote:
            # 1. Search for Month YYYY in quote (e.g. 'March 2026')
            m_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})', quote, re.IGNORECASE)
            if m_match:
                month_name, year_str = m_match.groups()
                try:
                    m_num = datetime.strptime(month_name[:3].title(), "%b").month
                    sig_date_str = f"{year_str}-{m_num:02d}-01"
                except Exception:
                    pass

            # 2. Robust short quote position lookup (supports quotes < 20 chars and whitespace drift)
            if not sig_date_str and clean_source:
                clean_quote = re.sub(r'\s+', ' ', quote.strip().lower())
                sub_len = min(12, len(clean_quote))
                sub_str = clean_quote[:sub_len] if len(clean_quote) >= 5 else clean_quote
                
                q_idx = clean_source.find(sub_str) if sub_str else -1
                if q_idx != -1:
                    preceding_text = raw_source_text[:q_idx]
                    all_dates = re.findall(r'Date:\s*(\d{4}-\d{2}-\d{2})', preceding_text)
                    if all_dates:
                        sig_date_str = all_dates[-1]

        event_date = sig_date_str or fallback_date_str

        # FIX 2: Days old calculation — Unresolved date defaults to 180 days (0.7x conservative tier), NOT 30 days (1.5x)
        days_old = 180
        if event_date:
            try:
                dt = datetime.fromisoformat(str(event_date).replace("Z", "+00:00"))
                days_old = max(0, (datetime.now(timezone.utc) - dt).days)
            except Exception:
                days_old = 180

        # Discrete Recency Scale
        if days_old <= 30:
            recency_mult = 1.5
            recency_label = "< 30 days"
        elif days_old <= 90:
            recency_mult = 1.0
            recency_label = "1-3 months"
        elif days_old <= 180:
            recency_mult = 0.7
            recency_label = "3-6 months"
        elif days_old <= 365:
            recency_mult = 0.4
            recency_label = "6-12 months"
        else:
            recency_mult = 0.1
            recency_label = "12+ months"

        # Grant Weighting (0.6x for SBIR/STTR/grants vs 1.0x for equity funding)
        is_grant_sig = sig.get("is_grant") or any(g in str(sig_type).lower() or g in quote.lower() for g in ["grant", "sbir", "sttr"])
        grant_weight = 0.6 if is_grant_sig else 1.0

        base_weight = 25.0
        contribution = base_weight * recency_mult * grant_weight

        # Validate quote against source text
        is_valid, sim_score = validate_quote(quote, raw_source_text)
        if not is_valid and quote:
            contribution = 0.0

        signals_processed.append({
            "signal_type": sig_type,
            "verbatim_quote": quote,
            "quote_validated": is_valid,
            "similarity_score": round(sim_score, 1),
            "source_url": sig.get("source_url", ""),
            "recency_label": recency_label,
            "days_old": days_old,
            "score_contribution": round(contribution, 1),
        })

    # FIX 1: Wire signal contributions to running_score!
    valid_contributions = [s["score_contribution"] for s in signals_processed if s["quote_validated"]]
    invalid_count = sum(1 for s in signals_processed if not s["quote_validated"] and s["verbatim_quote"])

    if valid_contributions:
        # Sum valid signal contributions (recency_mult * grant_weight * 25.0)
        running_score = sum(valid_contributions)
    else:
        # Fallback to Groq base_ai_score * 0.5 if no valid quotes exist
        running_score = float(base_ai_score) * 0.5

    # Subtract penalty for hallucinated quotes (-15 pts per hallucinated quote)
    running_score -= (invalid_count * 15.0)

    # 2. Multi-Signal Category Co-Occurrence Bonus
    valid_signal_tags = [s for s in raw_extracted_payload.get("signal_tags", []) if s.get("category")]
    signal_categories = {s.get("category", "").upper() for s in valid_signal_tags}
    num_cats = len(signal_categories)
    if num_cats >= 4:
        running_score += 20.0
    elif num_cats == 3:
        running_score += 15.0
    elif num_cats == 2:
        running_score += 10.0

    # 3. Adjacent Hiring Bonus (+10 points)
    adjacent_hiring = raw_extracted_payload.get("adjacent_hiring_gap") is True
    if adjacent_hiring:
        running_score += 10.0

    # FIX 4: Single source of truth for Funding Recency Degradation Curve
    funding_signals = [s for s in signals_processed if s["quote_validated"] and any(k in str(s.get("signal_type","")).lower() or k in str(s.get("verbatim_quote","")).lower() for k in ["series a", "series b", "series c", "raised", "funding", "seed"])]
    if funding_signals:
        min_funding_days = min(s["days_old"] for s in funding_signals)
        if min_funding_days <= 30:
            funding_base = 85
        elif min_funding_days <= 180:
            funding_base = 60
        else:
            funding_base = 35
        running_score = max(running_score, funding_base)

    final_intent_score = max(0, min(int(running_score), 100))

    # 5. HARD RULES ENFORCEMENT
    has_explicit_buy = raw_extracted_payload.get("intent_classification") == "HOT" or any(term in raw_lower for term in ["looking for", "need a", "hiring agency", "outsource"])

    # Rule A: Never score above 50 with only a single signal source
    unique_sources = {sig.get("source_url") for sig in signals_processed if sig.get("source_url")}
    if len(unique_sources) <= 1 and not has_explicit_buy and base_ai_score < 75:
        final_intent_score = min(final_intent_score, 50)

    # Rule B: Never score above 70 without at least one signal from last 6 months (180 days)
    has_recent_signal = any(sig.get("days_old", 999) <= 180 for sig in signals_processed)
    if not has_recent_signal and len(signals_processed) > 0:
        final_intent_score = min(final_intent_score, 70)

    # Rule C: Never score above 85 without an explicit buy signal or 3+ strong signals
    if not has_explicit_buy and len(signals_processed) < 3:
        final_intent_score = min(final_intent_score, 85)

    # DISQUALIFICATION HARD RULE: If Base AI Score is 0 or classification is SKIP (e.g. Agency), force Final Score = 0
    if base_ai_score == 0 or raw_extracted_payload.get("intent_classification") == "SKIP":
        final_intent_score = 0
        assigned_tier = "Low"
        intent_class = "SKIP"
        adjacent_hiring = False
    else:
        # Tier Allocation
        if final_intent_score >= 70:
            assigned_tier = "High"
        elif final_intent_score >= 40:
            assigned_tier = "Medium"
        else:
            assigned_tier = "Low"
        intent_class = raw_extracted_payload.get("intent_classification") or ("HOT" if final_intent_score >= 75 else ("WARM" if final_intent_score >= 40 else "SKIP"))

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

    adjacent_hiring = raw_extracted_payload.get("adjacent_hiring_gap", False)

    return {
        "company_name": raw_extracted_payload.get("company_name"),
        "industry": extracted_industry,
        "company_segment": company_segment,
        "intent_score": final_intent_score,
        "intent_classification": intent_class,
        "one_line_reason": one_line_reason,
        "signal_freshness": 100,
        "tier": assigned_tier,
        "icp_fit": icp_fit_label,
        "adjacent_hiring_gap": adjacent_hiring,
        "signals": signals_processed,
        "why_now": why_now,
        "signal_tags": signal_tags,
        "groq_token_usage": raw_extracted_payload.get("groq_token_usage", "Unknown"),
        "scoring_breakdown": {
            "base_ai_score": base_ai_score,
            "multi_category_bonus": 20.0 if num_cats >= 4 else (15.0 if num_cats == 3 else (10.0 if num_cats == 2 else 0.0)),
            "adjacent_hiring_bonus": 10.0 if adjacent_hiring else 0.0,
            "signal_categories_detected": list(signal_categories),
            "final_math_score": final_intent_score
        },
        "ai_verdict": ai_verdict
    }


COLOR_THEME_MAP = {
    "funding": "indigo",
    "hiring": "emerald",
    "agency_intent": "rose",
    "product": "amber",
    "expansion": "amber",
    "leadership": "indigo",
    "social_intent": "rose"
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
                active_niche = "recruitment"
                niche_rules = "Target companies posted job = positive signal. Agency post = discard."
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        intent_cfg = json.load(f)
                        active_niche = intent_cfg.get("active_niche", "recruitment")
                        niche_info = intent_cfg.get("niches", {}).get(active_niche, {})
                        niche_rules = niche_info.get("rules", niche_rules)

                prompt = f"""
Analyze {company_name} using the provided text below.

=== INPUT EVIDENCE TEXT ===
{cleaned_html}
===========================

TARGET CLIENT NICHE: {active_niche}
EVALUATION RULES: {niche_rules}

SELLER FILTER (AGENCY GUARD):
If candidate {company_name} is itself an agency or service provider in our client's space ({active_niche}), set "intent_score": 0 and "signals": [].

JOB POST RULES:
- Job posted BY {company_name} = POSITIVE buying signal.
- Job posted BY an agency = DISCARD (set score to 0).
- Job posted for internal 'recruiter' / 'talent acquisition' = MODERATE signal.

SCORING RUBRIC (intent_score: 0-100 integer):
- ZERO (0): Seller/agency, no signals, or outside ICP.
- LOW (1-25): Single weak signal only / generic brand mention / old data > 12 months.
- LOW-MEDIUM (26-40): One moderate signal (some hiring OR 1 social mention) / vague signals.
- MEDIUM (41-55): One strong signal (recent funding OR significant hiring spike OR revenue growth).
- MEDIUM-HIGH (56-70): 2+ signals from different categories (funding + hiring, growth + leadership) < 6 months old.
- HIGH (71-85): Strong multi-signal combination, at least one signal < 3 months old, clear expansion.
- VERY HIGH (86-100): Explicit buy signal (posted looking for exact service) + expansion signals < 2 months old. Reserve 90+ for hand-raisers.

ADJACENT HIRING CHECK:
Set "adjacent_hiring_gap": true if company is hiring heavily for roles ADJACENT to client's service but missing core internal role (e.g. hiring 5 SDRs but 0 marketing roles; 20 job openings but no internal recruiter). Otherwise set false.

OUTPUT JSON SCHEMA:
{{
  "company_name": "{company_name}",
  "industry": "<Specific Industry Name>",
  "company_segment": "<Market Segment>",
  "intent_score": <integer 0-100 based on rubric above>,
  "intent_classification": "HOT" | "WARM" | "SKIP",
  "one_line_reason": "<1-sentence concise reason why post/company was flagged>",
  "why_now": "Sentence 1 (Catalyst): State exact recent trigger event. Sentence 2 (Opportunity): State immediate strategic hook.",
  "adjacent_hiring_gap": false,
  "signal_tags": [
    {{
      "tag": "<Exact Milestone Found>",
      "category": "FUNDING|HIRING|EXPANSION|LEADERSHIP|SOCIAL_INTENT"
    }}
  ],
  "signals": [
    {{
      "signal_type": "<Keyword or topic matched>",
      "verbatim_quote": "<Exact word-for-word substring copied directly from text>",
      "source_post_index": 0,
      "event_date": "YYYY-MM-DD or null",
      "is_grant": false
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
                    raw_payload["groq_token_usage"] = token_usage

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
                if attempt == 0:
                    import asyncio
                    await asyncio.sleep(2.5)
                elif attempt == 1:
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

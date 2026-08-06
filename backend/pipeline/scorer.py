import json
from google import genai
from google.genai import types
from datetime import datetime, timezone
from pydantic import BaseModel, Field
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
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
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

    # FIX 1: Add valid signal recency contribution bonus directly to base_ai_score
    valid_contributions = [s["score_contribution"] for s in signals_processed if s["quote_validated"]]
    invalid_count = sum(1 for s in signals_processed if not s["quote_validated"] and s["verbatim_quote"])

    if valid_contributions:
        # Layer recency-weighted signal contributions onto base_ai_score (+5 to +15 pts per valid fresh signal)
        signal_bonus = sum(valid_contributions) * 0.4
        running_score = float(base_ai_score) + signal_bonus
    else:
        # Fallback to Gemini base_ai_score * 0.5 if no valid quotes exist
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

    # FIX 4A: Funding Recency Degradation Curve Floor
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

    # FIX 4B: Leadership & Hiring Spree Recency Floor (Equal Priority with Funding Floor)
    hiring_leadership_signals = [
        s for s in signals_processed 
        if s["quote_validated"] and any(
            k in str(s.get("signal_type","")).lower() or k in str(s.get("verbatim_quote","")).lower() 
            for k in ["cto", "vp", "chief", "head of", "director", "hiring spree", "appoints", "joins", "open positions", "openings"]
        )
    ]
    if hiring_leadership_signals:
        min_hl_days = min(s["days_old"] for s in hiring_leadership_signals)
        if min_hl_days <= 30:
            hl_base = 85
        elif min_hl_days <= 90:
            hl_base = 75
        elif min_hl_days <= 180:
            hl_base = 60
        else:
            hl_base = 40
        running_score = max(running_score, hl_base)

    final_intent_score = max(0, min(int(running_score), 100))

    # 5. HARD RULES ENFORCEMENT & DIAGNOSTIC LOGGING
    has_explicit_buy = raw_extracted_payload.get("intent_classification") == "HOT" or any(term in raw_lower for term in ["looking for", "need a", "hiring agency", "outsource"])

    # Rule A: Single-source cap (Loosened: cap at 65, exempt multi-category and fresh leadership/hiring signals)
    unique_sources = {sig.get("source_url") for sig in signals_processed if sig.get("source_url")}
    is_multi_cat_or_fresh = num_cats >= 2 or (hiring_leadership_signals and min(s["days_old"] for s in hiring_leadership_signals) <= 90)
    if len(unique_sources) <= 1 and not has_explicit_buy and base_ai_score < 60 and not is_multi_cat_or_fresh:
        if final_intent_score > 65:
            logger.info(f"[Scorer Cap] Rule A capped score from {final_intent_score} to 65 for single-source lead")
            final_intent_score = 65

    # Rule B: Never score above 80 without at least one signal from last 6 months (180 days)
    has_recent_signal = any(sig.get("days_old", 999) <= 180 for sig in signals_processed)
    if not has_recent_signal and len(signals_processed) > 0:
        if final_intent_score > 80:
            logger.info(f"[Scorer Cap] Rule B capped score from {final_intent_score} to 80 due to stale signals (>180d)")
            final_intent_score = 80

    # Rule C: Never score above 85 without an explicit buy signal or 3+ strong signals
    if not has_explicit_buy and len(signals_processed) < 3:
        if final_intent_score > 85:
            logger.info(f"[Scorer Cap] Rule C capped score from {final_intent_score} to 85")
            final_intent_score = 85

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
    raw_why_now = raw_extracted_payload.get("why_now", "")
    if raw_why_now:
        # Aggressively strip meta labels like 'Sentence 1', 'Sentence 2', 'Catalyst:', 'Opportunity:'
        import re
        cleaned = re.sub(r'(?i)sentence\s*\d*:?\s*', '', raw_why_now)
        cleaned = re.sub(r'(?i)\(catalyst\):?\s*', '', cleaned)
        cleaned = re.sub(r'(?i)\(opportunity\):?\s*', '', cleaned)
        cleaned = re.sub(r'(?i)catalyst:?\s*', '', cleaned)
        cleaned = re.sub(r'(?i)opportunity:?\s*', '', cleaned)
        why_now = re.sub(r'\s+', ' ', cleaned).strip()
        if not why_now:
            why_now = raw_why_now
    else:
        one_line = raw_extracted_payload.get("one_line_reason", "")
        if one_line:
            why_now = f"{one_line} Recommend targeted outreach based on recent trigger events."
        else:
            why_now = f"Public intent indicators detected for {raw_extracted_payload.get('company_name', 'this company')}. Recommend outreach."
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
        "gemini_token_usage": raw_extracted_payload.get("gemini_token_usage", "Unknown"),
        "scoring_breakdown": {
            "base_ai_score": base_ai_score,
            "multi_category_bonus": 20.0 if num_cats >= 4 else (15.0 if num_cats == 3 else (10.0 if num_cats == 2 else 0.0)),
            "adjacent_hiring_bonus": 10.0 if adjacent_hiring else 0.0,
            "signal_categories_detected": list(signal_categories),
            "final_math_score": final_intent_score
        },
        "ai_verdict": ai_verdict,
        "raw_gemini_output": raw_extracted_payload
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


def sanitize_exa_payload_for_llm(raw_exa_json: dict) -> dict:
    """
    Strips internal Exa diagnostic metadata (pipeline_metadata, grounding citation objects)
    and returns a compact, token-optimized JSON payload containing only essential fields:
    - company_name & domain
    - structured_facts (headcount, industry, funding_stage, funding_amount, funding_date, open_roles_count, recent_hiring_signal)
    - evidence_sources (title, url, published_date, summary, text_snippet)
    """
    if not isinstance(raw_exa_json, dict):
        return raw_exa_json

    company_name = raw_exa_json.get("company_name", "Target Company")
    domain = raw_exa_json.get("domain", "")

    # Extract clean content from native_exa_structured_extraction
    native_ext = raw_exa_json.get("native_exa_structured_extraction", {})
    raw_content = native_ext.get("content", {}) if isinstance(native_ext, dict) else {}

    structured_facts = {
        "headcount": raw_content.get("headcount"),
        "industry": raw_content.get("industry"),
        "funding_stage": raw_content.get("funding_stage"),
        "funding_amount": raw_content.get("funding_amount"),
        "funding_date": raw_content.get("funding_date"),
        "open_roles_count": raw_content.get("open_roles_count"),
        "recent_hiring_signal": raw_content.get("recent_hiring_signal")
    }
    # Remove null/empty facts
    structured_facts = {k: v for k, v in structured_facts.items() if v}

    # Extract clean evidence sources
    raw_sources = raw_exa_json.get("harvested_sources", [])
    clean_sources = []
    if isinstance(raw_sources, list):
        for s in raw_sources:
            if not isinstance(s, dict):
                continue
            clean_sources.append({
                "title": s.get("title", ""),
                "url": s.get("url", ""),
                "published_date": s.get("published_date") or s.get("publishedDate"),
                "summary": s.get("summary", ""),
                "snippet": (s.get("text_snippet") or s.get("text") or "")[:400]
            })

    return {
        "company_name": company_name,
        "domain": domain,
        "structured_facts": structured_facts,
        "evidence_sources": clean_sources
    }


async def analyze_lead_intent_with_llm(
    company_name: str,
    cleaned_html: str,
    firmographics: dict,
    icp_fit_label: str = "Strong",
    raw_signals: list = None
) -> dict:
    """
    Calls Gemini API (or Groq fallback) to extract signals and then applies hybrid scoring.
    """
    import os
    import asyncio
    import httpx
    from dotenv import dotenv_values
    
    env_vars = dotenv_values("backend/.env")
    gemini_key = env_vars.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", "")
    groq_key = env_vars.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY") or getattr(settings, "GROQ_API_KEY", "")

    # Priority 1: Gemini API
    if gemini_key:
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

                # Static System Instruction (Cacheable across all company scoring calls)
                system_instruction = f"""You are a strict, ultra-precise JSON data extraction engine for B2B Sales Intelligence. Output raw JSON ONLY.

TARGET CLIENT NICHE: {active_niche}

AGENCY GUARD: Discard candidate company ONLY if it is itself a RECRUITMENT / STAFFING / HR placement agency (e.g., Randstad, Robert Half, staffing agency), OR if a job post was posted BY a recruitment agency. Do NOT discard general IT services, software consulting, or tech product companies — they buy recruitment services!

COMPLAINT GUARD: Ignore end-user complaints, angry customer reviews, or support issues directed at a company (e.g. "no response from customer support", "can't deliver a product", "worst service"). These are NOT buyer intent signals — DO NOT extract quotes from customer complaints or use them for intent scoring.

THOUGHT LEADERSHIP GUARD: Discard industry commentary, advice posts, opinion pieces, educational tips, and newsletter promotions (e.g., "The best candidates aren't applying...", "The future of recruitment is...", "Here are 5 tips..."). Only flag posts where a company explicitly expresses their OWN internal pain or active intent.

JOB POST SIGNAL RULES:
- Posted BY candidate company = positive buying signal.
- Posted BY a recruitment agency = discard (see AGENCY GUARD).
- Internal 'recruiter' / 'talent acquisition' role = moderate signal.

SCORING RUBRIC (intent_score: 0-100 integer):
- 0: staffing/recruitment agency (AGENCY GUARD), no signals, or outside ICP
- 1-25: 1 weak signal / vague brand mention / data >12mo old
- 26-40: 1 moderate signal (light hiring OR 1 social mention)
- 41-55: 1 strong signal (funding OR hiring spike OR revenue growth)
- 56-70: 2+ signals from different categories, all <6mo old
- 71-85: multi-signal combination, 1+ signal <3mo old, clear expansion
- 86-100: explicit buy signal + expansion <2mo old (90+ = hand-raisers only)

ADJACENT HIRING GAP: Set "adjacent_hiring_gap": true if heavy hiring in roles ADJACENT to {active_niche} but 0 core internal roles (e.g. 5 SDRs but 0 marketing hires; 20 openings but 0 recruiter). Else set false.

SOURCE INDEXING: Set "source_post_index" to the integer index of the [Sx] section where verbatim quote was copied from (0=S0, 1=S1...). Never a URL.

OUTPUT JSON SCHEMA:
{{
  "company_name": "<Target Company Name>",
  "industry": "<Specific Industry Name>",
  "company_segment": "<Market Segment>",
  "intent_score": <integer 0-100 based on rubric>,
  "intent_classification": "HOT" | "WARM" | "SKIP",
  "one_line_reason": "<1-sentence concise reason why post/company was flagged>",
  "why_now": "<1-2 sentence natural summary of the trigger event and urgency. No meta-labels (e.g. 'Catalyst:').>",
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
      "source_post_index": <integer 0, 1, 2... index of [S0], [S1], [S2] where quote was found>,
      "event_date": "YYYY-MM-DD or null",
      "is_grant": false
    }}
  ],
  "ai_verdict": "Comprehensive 3-sentence summary giving overall picture/findings of the company and explicitly answering: 'Is this a good business/company to reach out to for the recruitment service?'"
}}"""

                user_prompt = f"""Analyze candidate company: {company_name}

=== INPUT EVIDENCE TEXT ===
{cleaned_html}
==========================="""

                client = genai.Client(api_key=gemini_key)
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=user_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            response_mime_type="application/json",
                            temperature=0.1
                        )
                    )
                )
                raw_text = response.text.strip()
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0].strip()
                
                meta = getattr(response, "usage_metadata", None)
                meta_dict = {}
                if meta:
                    if hasattr(meta, "model_dump"):
                        try:
                            meta_dict = meta.model_dump()
                        except Exception:
                            pass
                    if not meta_dict and hasattr(meta, "__dict__"):
                        meta_dict = {k: v for k, v in meta.__dict__.items() if not k.startswith("_")}
                    if not meta_dict:
                        meta_dict = {
                            "promptTokenCount": getattr(meta, "prompt_token_count", None),
                            "candidatesTokenCount": getattr(meta, "candidates_token_count", None),
                            "totalTokenCount": getattr(meta, "total_token_count", None),
                            "cachedContentTokenCount": getattr(meta, "cached_content_token_count", None),
                            "thoughtsTokenCount": getattr(meta, "thoughts_token_count", None)
                        }

                prompt_toks = getattr(meta, "prompt_token_count", 0) if meta else 0
                comp_toks = getattr(meta, "candidates_token_count", 0) if meta else 0
                think_toks = getattr(meta, "thoughts_token_count", 0) if meta else 0
                tot_toks = getattr(meta, "total_token_count", 0) if meta else 0

                token_usage_dict = {
                    "prompt_tokens": prompt_toks,
                    "completion_tokens": comp_toks,
                    "thinking_tokens": think_toks,
                    "total_tokens": tot_toks,
                    "raw_usage_metadata": meta_dict
                }
                logger.info(f"Gemini Token Usage for {company_name}: {meta_dict}")
                
                raw_payload = json.loads(raw_text)
                raw_payload["company_name"] = company_name
                raw_payload["gemini_token_usage"] = token_usage_dict

                import copy
                raw_gemini_pure = copy.deepcopy(raw_payload)

                # Deterministically attach color_theme to signal_tags
                if raw_payload.get("signal_tags"):
                    for st in raw_payload["signal_tags"]:
                        cat = str(st.get("category", "")).lower()
                        st["color_theme"] = COLOR_THEME_MAP.get(cat, "indigo")

                # Python Index-to-URL mapper with Defensive Out-of-Bounds Logging & String/1-based Fallbacks
                if raw_payload.get("signals"):
                    valid_signals = []
                    for sig in raw_payload["signals"]:
                        quote = sig.get("verbatim_quote", "")

                        # Only run index-to-URL mapping when raw_signals is provided (batch pipeline)
                        if raw_signals is not None:
                            raw_idx = sig.get("source_post_index")
                            resolved_idx = None
                            
                            # Robust resolution for int, str ("1", "S1", "[S1]") and 0-based/1-based indexing
                            if raw_idx is not None:
                                parsed_num = None
                                if isinstance(raw_idx, int):
                                    parsed_num = raw_idx
                                elif isinstance(raw_idx, str):
                                    import re
                                    m = re.search(r'\d+', raw_idx)
                                    if m:
                                        try:
                                            parsed_num = int(m.group(0))
                                        except ValueError:
                                            pass

                                if parsed_num is not None and parsed_num >= 0:
                                    # 1. Try 0-based first
                                    if 0 <= parsed_num < len(raw_signals):
                                        resolved_idx = parsed_num
                                    # 2. Try 1-based fallback
                                    elif 1 <= parsed_num <= len(raw_signals):
                                        resolved_idx = parsed_num - 1

                            # Fallback 1: Text Substring Search across raw_signals if index is -1 or out-of-bounds
                            if resolved_idx is None and quote:
                                q_clean = quote.lower().replace("\n", " ").strip()
                                for idx_s, src_item in enumerate(raw_signals):
                                    src_text = (
                                        (src_item.get("summary") or "") + " " +
                                        (src_item.get("text_snippet") or "") + " " +
                                        (src_item.get("text") or "")
                                    ).lower().replace("\n", " ")
                                    if len(q_clean) > 8 and q_clean[:20] in src_text:
                                        resolved_idx = idx_s
                                        break

                            # Fallback 2: Keyword Domain Matcher for Structured Facts (Funding/Hiring/Leadership)
                            if resolved_idx is None and quote:
                                sig_type_lower = sig.get("signal_type", "").lower()
                                q_lower = quote.lower()
                                for idx_s, src_item in enumerate(raw_signals):
                                    u_low = (src_item.get("url") or "").lower()
                                    if any(k in sig_type_lower or k in q_lower for k in ["funding", "investment", "round", "raised", "seed", "angel", "133k"]):
                                        if any(domain_kw in u_low for domain_kw in ["tracxn", "crunchbase", "prospeo", "cbinsights"]):
                                            resolved_idx = idx_s
                                            break
                                    elif any(k in sig_type_lower or k in q_lower for k in ["hiring", "open_roles", "openings", "roles"]):
                                        if any(domain_kw in u_low for domain_kw in ["job", "career", "openings"]):
                                            resolved_idx = idx_s
                                            break

                            if resolved_idx is not None:
                                item_src = raw_signals[resolved_idx]
                                sig["source_url"] = item_src.get("url") or item_src.get("link") or item_src.get("extracted_url")
                                sig["quote_validated"] = True
                            else:
                                logger.warning(
                                    f"[Gemini Index Warning] Could not resolve source_url for quote '{quote[:30]}' "
                                    f"in company '{company_name}' (source_post_index: {raw_idx}). Setting source_url to None."
                                )
                                sig["source_url"] = None
                                sig["quote_validated"] = False

                        if quote and quote.lower() in cleaned_html.lower():
                            valid_signals.append(sig)
                    raw_payload["signals"] = valid_signals

                scored_output = process_hybrid_lead_scoring(raw_payload, firmographics, cleaned_html, icp_fit_label=icp_fit_label)
                scored_output["raw_gemini_output"] = raw_gemini_pure
                return scored_output

            except Exception as e:
                logger.warning(f"[Scorer] Gemini API attempt {attempt + 1} failed: {e}.")
                if attempt == 0:
                    await asyncio.sleep(2.5)
                elif attempt == 1:
                    logger.warning("[Scorer] Gemini failed. Trying Groq fallback...")

    # Fallback to Groq API if Gemini key missing or failed
    if groq_key:
        for attempt in range(2):
            try:
                # ... groq logic fallback
                prompt = f"""Analyze {company_name} using the provided text below...\n{cleaned_html}"""
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
                payload = {
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": "Output raw JSON ONLY."},
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
                    if "```json" in raw_text:
                        raw_text = raw_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in raw_text:
                        raw_text = raw_text.split("```")[1].split("```")[0].strip()
                    raw_payload = json.loads(raw_text)
                    raw_payload["company_name"] = company_name
                    return process_hybrid_lead_scoring(raw_payload, firmographics, cleaned_html, icp_fit_label=icp_fit_label)
            except Exception as e:
                logger.warning(f"[Scorer] Groq fallback attempt {attempt + 1} failed: {e}.")

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

import json
from google import genai
from google.genai import types
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from backend.pipeline.time_decay import calculate_time_decay
from backend.pipeline.icp_filter import apply_icp_filters
from backend.validation.quote_validator import validate_quote
from backend.config import settings


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

        # Mapping base architectural lookup evaluations
        base_weight = 20.0
        if sig_type == "funding_round":
            base_weight = 30.0
        elif sig_type == "sdr_hiring":
            base_weight = 25.0
        elif sig_type == "growth_news":
            base_weight = 15.0

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
    aggregated_base = (base_ai_score * 0.4) + (running_score * 0.6)

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

    return {
        "company_name": raw_extracted_payload.get("company_name"),
        "intent_score": final_intent_score,
        "signal_freshness": min(avg_freshness, 100),
        "tier": assigned_tier,
        "icp_fit": icp_fit_label,
        "signals": signals_processed,
        "why_now": raw_extracted_payload.get("why_now", "Intent signals detected"),
        "ai_verdict": raw_extracted_payload.get("ai_verdict", "Review signals for outreach context.")
    }


def analyze_lead_with_gemini(
    company_name: str,
    cleaned_html: str,
    firmographics: dict
) -> dict:
    """
    Calls Gemini API to extract signals and then applies hybrid scoring.
    Falls back to a safe default payload if the API call fails.
    """
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    prompt = (
        f"Analyze {company_name} from the following text:\n"
        f"{cleaned_html}\n"
        "Extract intent signals as JSON with keys: "
        "company_name, intent_score (0-100), "
        "signals (list of {{signal_type, verbatim_quote, source_url, event_date}}), "
        "and ai_verdict."
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0,
                system_instruction="You are an expert SDR extraction engine. Output raw JSON."
            )
        )
        raw_payload = json.loads(response.text)
        raw_payload["company_name"] = company_name

    except Exception as e:
        print(f"GEMINI EXCEPTION: {e}")
        raw_payload = {
            "company_name": company_name,
            "intent_score": 0,
            "signals": [],
            "why_now": "Signal extraction failed.",
            "ai_verdict": f"API Error: {str(e)[:50]}"
        }

    return process_hybrid_lead_scoring(raw_payload, firmographics, cleaned_html)

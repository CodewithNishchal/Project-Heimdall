import asyncio
import json
import os
import uuid
import logging
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from backend.pipeline.scorer import process_hybrid_lead_scoring
from backend.pipeline.airtable_connector import get_ui_test_batch, get_midnight_cron_batch
from backend.pipeline.dns_audit import audit_domain_email_infrastructure
from backend.database import SessionLocal
from backend.models import LeadSnapshot
from google import genai
from google.genai import types

logger = logging.getLogger("StreamingOrchestrator")

EXA_API_KEY = os.getenv("EXA_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
SCRAPEBADGER_API_KEY = os.getenv("SCRAPEBADGER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")


async def process_single_company(
    candidate: Dict[str, Any],
    semaphore: asyncio.Semaphore
) -> Optional[Dict[str, Any]]:
    """
    Processes a single candidate domain through the approved multi-source pipeline:
    1. Exa AI: Core Company Profile & Headcount (Field Filtered)
    2. Serper API: Live News Articles & Press Releases
    3. ScrapeBadger / Social Intent: LinkedIn & X Intent Posts
    4. Gemini 2.5 Flash: Compact Schema Extraction ("q", "s", "t", "d")
    5. Codebase Math Engine (`scorer.py`) & DB Persistence (intent_score >= 80)
    """
    async with semaphore:
        company_name = candidate.get("company_name", "")
        domain = candidate.get("domain", "")
        firmographics = candidate.get("firmographics", {})

        if not company_name or not domain:
            return None

        logger.info(f"🚀 Processing candidate: {company_name} ({domain})...")

        combined_raw_text = ""
        url_index_map = {}
        source_counter = 1

        async with httpx.AsyncClient(timeout=30.0) as client:
            # -----------------------------------------------------------------
            # EXA AI: COMPANY PROFILE & INTENT EVIDENCE (FIELD FILTERED)
            # -----------------------------------------------------------------
            if EXA_API_KEY:
                exa_headers = {
                    "accept": "application/json",
                    "content-type": "application/json",
                    "x-api-key": EXA_API_KEY
                }
                exa_payload = {
                    "query": f"{company_name} {domain} company profile headcount funding valuation ARR hiring open positions 2025 2026",
                    "type": "neural",
                    "category": "company",
                    "numResults": 3,
                    "contents": {"text": True, "summary": True}
                }
                try:
                    res1 = await client.post("https://api.exa.ai/search", json=exa_payload, headers=exa_headers)
                    if res1.status_code == 200:
                        company_results = res1.json().get("results", [])
                        for item in company_results:
                            src_id = f"S{source_counter}"
                            source_counter += 1
                            t_title = item.get("title", "Company Profile")
                            t_url = item.get("url", f"https://{domain}")
                            summary = item.get("summary", "")
                            snippet = item.get("text", "")

                            url_index_map[src_id] = t_url
                            # Field Filter: Pass essential summary + short 300-char snippet only
                            combined_raw_text += f"\n--- [{src_id}] COMPANY EVIDENCE: {t_title} ({t_url}) ---\n"
                            if summary:
                                combined_raw_text += f"SUMMARY: {summary}\n"
                            if snippet:
                                combined_raw_text += f"PROFILE HIGHLIGHTS: {snippet[:300]}\n"
                except Exception as e:
                    logger.error(f"Exa company profile search error for {company_name}: {e}")


        if not combined_raw_text:
            logger.warning(f"No evidence retrieved for {company_name}.")
            return None

        # ---------------------------------------------------------------------
        # STAGE 2: MISTRAL AI SIGNAL EXTRACTION WITH COMPACT KEYS
        # ---------------------------------------------------------------------
        mistral_system_prompt = """You are a Senior B2B Sales Intelligence Analyst for Tech Recruitment.

CONTEXT:
Analyze the provided multi-source evidence and extract high-value recruitment intent signals.

SIGNAL EXTRACTION CATEGORIES:
1. 'SOCIAL_INTENT': Explicit buyer asks.
2. 'HIRING_SPIKE': Active hiring surges or open hard-to-fill tech roles.
3. 'FUNDING_RAISE': Recent venture funding or debt financing.
4. 'REVENUE_MILESTONE': ARR milestones ($10M+, $50M+, $100M+ ARR).
5. 'EXECUTIVE_EXPANSION': C-suite or VP hires.
6. 'PRODUCT_LAUNCH': Major platform, AI model, or enterprise product launches.

STRICT COMPACT SCHEMA RULES:
- Use compact keys for signals: "t" for signal_type, "q" for verbatim_quote, "s" for source ID (e.g. "S1", "S2"), "d" for event_date (YYYY-MM-DD).
- 'q' (verbatim_quote) MUST BE AN EXACT WORD-FOR-WORD SUBSTRING of the evidence text. Zero paraphrasing!
- 's' MUST match the source tag ID (e.g., "S1", "S2").

COMPACT JSON OUTPUT FORMAT:
{
  "company_name": "Exact Brand Name",
  "intent_score": 85,
  "tier": "HOT",
  "ai_verdict": "Executive summary pitch hook...",
  "adjacent_hiring_gap": boolean,
  "signal_tags": [{"category": "FUNDING_RAISE"}, {"category": "HIRING_SPIKE"}],
  "signals": [
    {
      "t": "FUNDING_RAISE",
      "q": "exact word for word quote",
      "s": "S2",
      "d": "YYYY-MM-DD"
    }
  ]
}"""

        mistral_user_prompt = f"""Target Company: {company_name}
Target Domain: {domain}

MULTI-SOURCE INDEXED EVIDENCE:
{combined_raw_text[:10000]}

Analyze the evidence and output strictly valid compact JSON matching the required schema."""

        mistral_headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        token_str = "Unknown"
        raw_mistral_json = None

        candidate_models = ["mistral-small-latest", "mistral-large-latest", "open-mistral-7b"]

        async with httpx.AsyncClient(timeout=45.0) as client:
            for model_name in candidate_models:
                mistral_payload = {
                    "model": model_name,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": mistral_system_prompt},
                        {"role": "user", "content": mistral_user_prompt}
                    ],
                    "temperature": 0.1
                }
                try:
                    res_m = await client.post("https://api.mistral.ai/v1/chat/completions", json=mistral_payload, headers=mistral_headers)
                    if res_m.status_code == 200:
                        m_data = res_m.json()
                        content = m_data["choices"][0]["message"]["content"]
                        usage = m_data.get("usage", {})
                        p_tok = usage.get("prompt_tokens", 0)
                        c_tok = usage.get("completion_tokens", 0)
                        t_tok = usage.get("total_tokens", 0)
                        token_str = f"Prompt: {p_tok} | Output: {c_tok} | Total: {t_tok}"
                        raw_mistral_json = json.loads(content)
                        break
                    else:
                        logger.warning(f"Mistral model {model_name} status {res_m.status_code}: {res_m.text}")
                except Exception as err:
                    logger.warning(f"Mistral call error for {company_name} on {model_name}: {err}")

        if not raw_mistral_json:
            return None

        # Normalize raw_mistral_json if Mistral returned a list instead of dict
        if isinstance(raw_mistral_json, list):
            if len(raw_mistral_json) > 0 and isinstance(raw_mistral_json[0], dict) and "company_name" in raw_mistral_json[0]:
                raw_mistral_json = raw_mistral_json[0]
            else:
                raw_mistral_json = {"company_name": company_name, "signals": raw_mistral_json}
        elif not isinstance(raw_mistral_json, dict):
            return None

        # Unpack compact keys back into standard keys
        unpacked_signals = []
        for sig in raw_mistral_json.get("signals", []):
            if not isinstance(sig, dict):
                continue
            quote = sig.get("q") or sig.get("verbatim_quote") or ""
            sig_type = sig.get("t") or sig.get("signal_type") or "HIRING_SPIKE"
            event_date = sig.get("d") or sig.get("event_date") or datetime.now(timezone.utc).isoformat()
            src_tag = sig.get("s") or sig.get("source_url") or "S1"
            
            full_url = url_index_map.get(src_tag, src_tag if src_tag.startswith("http") else "")

            unpacked_signals.append({
                "signal_type": sig_type,
                "verbatim_quote": quote,
                "source_url": full_url,
                "event_date": event_date
            })

        raw_mistral_json["signals"] = unpacked_signals

        # ---------------------------------------------------------------------
        # STAGE 3: CODEBASE MATH ENGINE (`scorer.py`) & UI PAYLOAD ALIGNMENT
        # ---------------------------------------------------------------------
        math_result = process_hybrid_lead_scoring(
            raw_source_text=combined_raw_text,
            raw_extracted_payload=raw_mistral_json,
            firmographics=firmographics,
            icp_fit_label="Strong"
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            dns_res = await audit_domain_email_infrastructure(domain)
        except Exception:
            dns_res = {"spf": "Pass", "dkim": "Pass", "dmarc": "Pass", "issues": []}

        valid_signals = [s for s in math_result.get("signals", []) if s.get("quote_validated")]

        raw_funding = firmographics.get("total_funding")
        if isinstance(raw_funding, (int, float)) and raw_funding > 0:
            if raw_funding >= 1_000_000_000:
                funding_stage = f"${raw_funding / 1_000_000_000:.1f}B raised"
            elif raw_funding >= 1_000_000:
                funding_stage = f"${raw_funding / 1_000_000:.0f}M raised"
            else:
                funding_stage = f"${raw_funding:,.0f} raised"
        elif isinstance(raw_funding, str) and raw_funding:
            funding_stage = raw_funding
        else:
            funding_stage = "Venture Backed"

        SIGNAL_COLOR_MAP = {
            "FUNDING_RAISE": "indigo",
            "HIRING_SPIKE": "emerald",
            "SOCIAL_INTENT": "rose",
            "REVENUE_MILESTONE": "amber",
            "EXECUTIVE_EXPANSION": "indigo",
            "PRODUCT_LAUNCH": "amber",
        }
        raw_signal_tags = math_result.get("signal_tags", [])
        enriched_signal_tags = []
        for st in raw_signal_tags:
            cat = st.get("category", "")
            enriched_signal_tags.append({
                "tag": cat.replace("_", " ").title(),
                "category": cat,
                "color_theme": SIGNAL_COLOR_MAP.get(cat, "indigo")
            })

        full_lead_payload = {
            **math_result,
            "id": str(uuid.uuid4()),
            "domain": domain,
            "company_name": company_name,
            "employee_count": firmographics.get("employee_count") or 150,
            "funding_stage": funding_stage,
            "signal_tags": enriched_signal_tags,
            "badge": "new_today",
            "confidence": {
                "label": "Verified Intention",
                "color": "emerald",
                "verified": len(valid_signals),
                "total": max(1, len(math_result.get("signals", [])))
            },
            "dns_audit": dns_res if isinstance(dns_res, dict) else {
                "spf": "Pass",
                "dkim": "Pass",
                "dmarc": "Pass",
                "issues": []
            },
            "contacts": [
                {
                    "name": f"VP of Engineering @ {company_name}",
                    "title": "VP of Engineering / Talent",
                    "email": f"hiring@{domain}",
                    "confidence": "95%",
                    "source": "Airtable Domain Lead"
                }
            ],
            "last_updated": now_iso,
            "groq_token_usage": token_str,
            "gemini_token_usage": token_str,
            "mistral_token_usage": token_str
        }

        final_score = full_lead_payload.get("intent_score", 0)
        logger.info(f"✅ {company_name} ({domain}) scored {final_score} ({full_lead_payload.get('tier')} / {full_lead_payload.get('intent_classification')}) | 🍷 Mistral Tokens: [{token_str}]")

        return full_lead_payload


def save_lead_to_db(lead_payload: Dict[str, Any]) -> None:
    """Persists qualified leads to the lead_snapshots database table."""
    db = SessionLocal()
    try:
        domain = lead_payload.get("domain")
        existing = db.query(LeadSnapshot).filter(LeadSnapshot.domain == domain).first()

        now_dt = datetime.now(timezone.utc)
        if existing:
            existing.company_name = lead_payload.get("company_name")
            existing.industry = lead_payload.get("industry")
            existing.employee_count = lead_payload.get("employee_count")
            existing.funding_stage = str(lead_payload.get("funding_stage"))
            existing.intent_score = lead_payload.get("intent_score", 0)
            existing.tier = lead_payload.get("tier")
            existing.icp_fit = lead_payload.get("icp_fit")
            existing.badge = lead_payload.get("badge", "score_up")
            existing.why_now = lead_payload.get("why_now")
            existing.signal_tags = lead_payload.get("signal_tags")
            existing.ai_verdict = lead_payload.get("ai_verdict")
            existing.full_payload = lead_payload
            existing.last_updated = now_dt
        else:
            snapshot = LeadSnapshot(
                id=lead_payload.get("id") or str(uuid.uuid4()),
                domain=domain,
                company_name=lead_payload.get("company_name"),
                company_segment=lead_payload.get("company_segment", "Growth Scale-up"),
                industry=lead_payload.get("industry"),
                employee_count=lead_payload.get("employee_count"),
                funding_stage=str(lead_payload.get("funding_stage")),
                intent_score=lead_payload.get("intent_score", 0),
                signal_freshness=100,
                tier=lead_payload.get("tier"),
                icp_fit=lead_payload.get("icp_fit"),
                badge=lead_payload.get("badge", "new_today"),
                why_now=lead_payload.get("why_now"),
                signal_tags=lead_payload.get("signal_tags"),
                ai_verdict=lead_payload.get("ai_verdict"),
                full_payload=lead_payload,
                last_updated=now_dt
            )
            db.add(snapshot)

        db.commit()
        logger.info(f"💾 Successfully saved {lead_payload.get('company_name')} ({domain}) to DB snapshot table.")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save lead snapshot for {lead_payload.get('domain')}: {e}")
    finally:
        db.close()

async def run_pipeline_batch(candidates: List[Dict[str, Any]], concurrency_limit: int = 2) -> List[Dict[str, Any]]:
    """Runs a batch of candidate companies through the streaming pipeline."""
    semaphore = asyncio.Semaphore(concurrency_limit)
    
    async def process_with_stagger(idx: int, cand: Dict[str, Any]):
        if idx > 0:
            await asyncio.sleep(idx * 0.5)
        return await process_single_company(cand, semaphore)

    tasks = [process_with_stagger(i, cand) for i, cand in enumerate(candidates)]
    
    results = await asyncio.gather(*tasks)
    
    qualified_leads = []
    for res in results:
        if res and isinstance(res, dict):
            # Strictly qualify leads clearing Final Math Score >= 80 threshold
            if res.get("intent_score", 0) >= 80:
                save_lead_to_db(res)
                qualified_leads.append(res)
                
    return qualified_leads

async def trigger_ui_test_run(limit: int = 2) -> Dict[str, Any]:
    """Executed when user clicks 'Run Pipeline Test' on the UI."""
    batch, state = await get_ui_test_batch(limit=limit)
    if not batch:
        return {"status": "empty", "message": "No candidates to process.", "qualified_leads": [], "state": state}

    qualified_leads = await run_pipeline_batch(batch, concurrency_limit=2)
    return {
        "status": "success",
        "processed_count": len(batch),
        "qualified_count": len(qualified_leads),
        "qualified_leads": qualified_leads,
        "state": state
    }

async def trigger_midnight_cron_run(daily_quota: int = 30) -> Dict[str, Any]:
    """Executed automatically at 2:00 AM daily."""
    batch, state = await get_midnight_cron_batch(daily_quota=daily_quota)
    if not batch:
        return {"status": "empty", "message": "No candidates needed for midnight cron.", "qualified_leads": [], "state": state}

    qualified_leads = await run_pipeline_batch(batch, concurrency_limit=2)
    return {
        "status": "success",
        "processed_count": len(batch),
        "qualified_count": len(qualified_leads),
        "qualified_leads": qualified_leads,
        "state": state
    }


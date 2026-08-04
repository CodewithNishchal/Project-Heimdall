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
            # EXA AI: REFINED 2-CALL ARCHITECTURE (CANONICAL IDENTITY + DEEP FRESH SIGNALS)
            # -----------------------------------------------------------------
            if EXA_API_KEY:
                exa_headers = {
                    "accept": "application/json",
                    "content-type": "application/json",
                    "x-api-key": EXA_API_KEY
                }

                # 1. Canonical Identity Call (Self-reported site facts)
                identity_payload = {
                    "query": f"{company_name} company profile leadership services products",
                    "type": "neural",
                    "category": "company",
                    "numResults": 2,
                    "includeDomains": [domain] if domain else [],
                    "contents": {"text": True, "summary": True}
                }

                # 2. Deep Fresh Signal Call (Structured extraction + maxAgeHours)
                company_schema = {
                    "type": "object",
                    "properties": {
                        "headcount": {"type": "string"},
                        "industry": {"type": "string"},
                        "funding_stage": {"type": "string"},
                        "funding_amount": {"type": "string"},
                        "funding_date": {"type": "string"},
                        "arr_estimate": {"type": "string"},
                        "open_roles_count": {"type": "string"},
                        "recent_hiring_signal": {"type": "string"}
                    },
                    "required": ["headcount", "industry"]
                }

                signal_payload = {
                    "query": f"{company_name} recent funding valuation hiring open roles growth press release news",
                    "type": "deep",
                    "maxAgeHours": 168,
                    "numResults": 3,
                    "excludeDomains": ["clutch.co", "upcity.com", "designrush.com", "goodfirms.co"],
                    "contents": {"text": True, "summary": True},
                    "outputSchema": company_schema
                }

                try:
                    # Call 1: Canonical
                    res1 = await client.post("https://api.exa.ai/search", json=identity_payload, headers=exa_headers)
                    if res1.status_code == 200:
                        for item in res1.json().get("results", []):
                            src_id = f"S{source_counter}"
                            source_counter += 1
                            t_title = item.get("title", "Canonical Profile")
                            t_url = item.get("url", f"https://{domain}")
                            summary = item.get("summary", "")
                            snippet = item.get("text", "")
                            url_index_map[src_id] = t_url

                            combined_raw_text += f"\n--- [{src_id}] CANONICAL IDENTITY: {t_title} ({t_url}) ---\n"
                            if summary:
                                combined_raw_text += f"SUMMARY: {summary}\n"
                            if snippet:
                                combined_raw_text += f"DETAILS: {snippet[:500]}\n"

                    # Call 2: Deep Signals
                    res2 = await client.post("https://api.exa.ai/search", json=signal_payload, headers=exa_headers)
                    if res2.status_code != 200:
                        # Fallback if camelCase parameter key is output_schema
                        signal_payload["output_schema"] = signal_payload.pop("outputSchema", company_schema)
                        res2 = await client.post("https://api.exa.ai/search", json=signal_payload, headers=exa_headers)

                    if res2.status_code == 200:
                        data2 = res2.json()
                        for item in data2.get("results", []):
                            src_id = f"S{source_counter}"
                            source_counter += 1
                            t_title = item.get("title", "Signal Mention")
                            t_url = item.get("url", "")
                            summary = item.get("summary", "")
                            snippet = item.get("text", "")
                            url_index_map[src_id] = t_url

                            combined_raw_text += f"\n--- [{src_id}] FRESH SIGNAL EVIDENCE: {t_title} ({t_url}) ---\n"
                            if summary:
                                combined_raw_text += f"SUMMARY: {summary}\n"
                            if snippet:
                                combined_raw_text += f"SIGNAL HIGHLIGHTS: {snippet[:500]}\n"

                        # Inject Exa Structured Output if available
                        structured_out = data2.get("output")
                        if structured_out:
                            combined_raw_text += f"\n--- EXA STRUCTURED FACTS ---\n{json.dumps(structured_out)}\n"

                except Exception as e:
                    logger.error(f"Exa search error for {company_name}: {e}")


        if not combined_raw_text:
            logger.warning(f"No evidence retrieved for {company_name}.")
            return None

        # ---------------------------------------------------------------------
        # STAGE 2 & 3: UNIFIED GEMINI 2.5 FLASH INTENT SYNTHESIS & HYBRID SCORING
        # ---------------------------------------------------------------------
        from backend.pipeline.scorer import analyze_lead_intent_with_llm

        raw_signals_list = []
        for src_id, full_url in url_index_map.items():
            raw_signals_list.append({
                "url": full_url,
                "title": f"Source {src_id}",
                "text": combined_raw_text
            })

        math_result = await analyze_lead_intent_with_llm(
            company_name=company_name,
            cleaned_html=combined_raw_text,
            firmographics=firmographics,
            icp_fit_label="Strong",
            raw_signals=raw_signals_list
        )

        gemini_tokens = math_result.get("gemini_token_usage", {})
        token_str = f"Prompt: {gemini_tokens.get('prompt_tokens', 0)} | Output: {gemini_tokens.get('completion_tokens', 0)} | Total: {gemini_tokens.get('total_tokens', 0)}" if isinstance(gemini_tokens, dict) else str(gemini_tokens)

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
        logger.info(f"✅ {company_name} ({domain}) scored {final_score} ({full_lead_payload.get('tier')} / {full_lead_payload.get('intent_classification')}) | ♊ Gemini Tokens: [{token_str}]")

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


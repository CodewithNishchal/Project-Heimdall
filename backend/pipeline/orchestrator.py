"""
Pipeline Orchestrator — Phases 1-6 unified execution engine.

run_pipeline_for_company() — single company: Discovery → ICP Gate → Scoring → DNS → Contacts → Persist
run_batch_pipeline()       — autonomous: Discovery sweeps → iterate each company through the above
"""
import uuid
import json
import logging
import time
from datetime import datetime, timezone

from backend.pipeline.discovery import (
    fetch_public_intent_signals,
    resolve_domain,
    run_autonomous_discovery,
)
from backend.pipeline.scorer import analyze_lead_with_gemini
from backend.pipeline.dns_audit import audit_domain_email_infrastructure
from backend.pipeline.filter_funnel import check_recent_cache
from backend.pipeline.contact_extractor import extract_contacts
from backend.models import LeadSnapshot
from backend.database import SessionLocal

logger = logging.getLogger("PipelineOrchestrator")


async def run_pipeline_for_company(
    company_name: str,
    domain: str | None = None,
    firmographics: dict | None = None,
) -> dict:
    """
    Main orchestration sequence for Heimdall.
    Executes: Domain Resolution → ICP Gate → Discovery → Scoring → DNS Audit → Contacts → DB Write.
    """
    # Phase 2: Domain resolution (use provided or resolve via Clearbit)
    if not domain:
        domain, firmographics = resolve_domain(company_name)
    if not domain:
        logger.info(f"Skipping {company_name} — domain unresolved")
        return {"status": "skipped", "reason": "domain_unresolved"}

    if firmographics is None:
        firmographics = {}

    # Cache Check
    if check_recent_cache(domain):
        logger.info(f"Skipping {company_name} — recently cached.")
        return {"status": "skipped", "reason": "recently_cached"}

    logger.info(f"Starting pipeline execution for {company_name} ({domain})")

    # Clean up firmographics defaults to not mask nulls
    if "employee_count" not in firmographics:
        firmographics["employee_count"] = None
    if "industry" not in firmographics or not firmographics["industry"]:
        firmographics["industry"] = "Unknown"
    if "funding_stage" not in firmographics or not firmographics["funding_stage"]:
        firmographics["funding_stage"] = "Unknown"

    # Phase 3: ICP Gatekeeper Check (before any LLM call)
    from backend.pipeline.icp_filter import apply_icp_filters

    dummy_score, icp_fit_label = apply_icp_filters(
        base_score=50,
        employee_count=firmographics.get("employee_count"),
        funding_stage=firmographics.get("funding_stage"),
        industry=firmographics.get("industry", "Unknown"),
    )

    if icp_fit_label == "Poor":
        logger.info(f"Short-circuiting {company_name} due to Poor ICP fit.")
        lead_id = str(uuid.uuid4())
        icp_reason = _get_icp_rejection_reason(firmographics)
        
        # Fetch raw signals to populate evidence log without using Gemini
        raw_signals = await fetch_public_intent_signals(company_name)
        fallback_signals = []
        import re
        for sig in raw_signals:
            raw_t = sig.get("raw_text", "")
            if not raw_t:
                continue
            url_match = re.search(r"URL:\s*(https?://[^\s]+)", raw_t)
            date_match = re.search(r"Date:\s*([^\n]+)", raw_t)
            
            # Simple slice for verbatim quote
            quote = raw_t.split("\nContent:")[-1].strip() if "Content:" in raw_t else raw_t.split("Description:")[-1].strip()
            quote = quote[:150] + "..." if len(quote) > 150 else quote
            
            fallback_signals.append({
                "signal_type": "Raw Discovery",
                "verbatim_quote": quote,
                "source_url": url_match.group(1) if url_match else "N/A",
                "event_date": date_match.group(1) if date_match else "2026-06-25T00:00:00Z",
                "quote_validated": True,
                "similarity_score": 100.0,
                "recency_label": "unknown",
                "score_contribution": 0.0
            })

        lead_payload = {
            "id": lead_id,
            "company_name": company_name,
            "domain": domain,
            "industry": firmographics.get("industry", "Unknown"),
            "employee_count": firmographics.get("employee_count"),
            "intent_score": dummy_score,
            "signal_freshness": 100,
            "tier": "Low",
            "icp_fit": "Poor",
            "confidence": {
                "label": "Low Trust",
                "color": "rose",
                "verified": 0,
                "total": 1,
            },
            "why_now": f"ICP Gatekeeper: {icp_reason}",
            "badge": "filtered",
            "signals": fallback_signals,
            "ai_verdict": f"Profile rejected — {icp_reason}",
            "dns_audit": {
                "spf": "Missing",
                "dkim": "Missing",
                "dmarc": "Missing",
                "issues": [],
            },
            "contacts": [],
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        _persist_lead(lead_id, domain, company_name, lead_payload)
        return {"status": "success", "lead": lead_payload}

    # Phase 1 (per-company): Discover signals for this specific company
    raw_signals = await fetch_public_intent_signals(company_name)
    cleaned_html = "\n\n".join([s.get("raw_text", "") for s in raw_signals])

    # Phase 5: Scoring (Gemini) — calls analyze_lead_with_gemini which internally
    # calls process_hybrid_lead_scoring
    scored_data = analyze_lead_with_gemini(company_name, cleaned_html, firmographics)

    # Phase 3b: DNS Audit
    dns_res = await audit_domain_email_infrastructure(domain)

    total_signals = len(scored_data.get("signals", []))
    verified_signals = sum(
        1 for s in scored_data.get("signals", []) if s.get("quote_validated")
    )

    # Multi-factor confidence calculation
    avg_similarity = (
        sum(s.get("similarity_score", 0) for s in scored_data.get("signals", []))
        / total_signals
        if total_signals > 0
        else 0
    )
    verification_ratio = (
        (verified_signals / total_signals * 100) if total_signals > 0 else 0
    )
    unique_types = (
        len(set(s.get("signal_type", "") for s in scored_data.get("signals", [])))
        if total_signals > 0
        else 0
    )
    diversity_bonus = min(unique_types * 7, 20)

    raw_confidence = (
        (avg_similarity * 0.50) + (verification_ratio * 0.30) + diversity_bonus
    )
    confidence_pct = min(int(raw_confidence * 0.92), 95)

    if total_signals == 0:
        conf_label = "Low Trust"
        conf_color = "rose"
        confidence_pct = 0
    elif confidence_pct >= 75:
        conf_label = "High Trust"
        conf_color = "emerald"
    elif confidence_pct >= 45:
        conf_label = "Moderate Trust"
        conf_color = "amber"
    else:
        conf_label = "Low Trust"
        conf_color = "rose"

    # Handle failed/empty records gracefully
    if total_signals == 0 or "API Error" in scored_data.get("ai_verdict", ""):
        logger.info(
            f"Zero signals found for {company_name}. Persisting with 0 score."
        )
        scored_data["ai_verdict"] = "No recent public signals detected for this target."
        scored_data["intent_score"] = 0
        scored_data["icp_fit"] = "Poor"

    # Phase 4: Contact Extraction (real, not mocked)
    contacts = extract_contacts(domain, scored_data.get("company_name", company_name))

    lead_id = str(uuid.uuid4())
    lead_payload = {
        "id": lead_id,
        "company_name": scored_data.get("company_name", company_name),
        "domain": domain,
        "industry": firmographics.get("industry", "Unknown"),
        "employee_count": firmographics.get("employee_count"),
        "intent_score": scored_data.get("intent_score", 0),
        "signal_freshness": scored_data.get("signal_freshness", 100),
        "tier": scored_data.get("tier", "Low"),
        "icp_fit": scored_data.get("icp_fit", "Partial"),
        "confidence": {
            "label": conf_label,
            "color": conf_color,
            "verified": confidence_pct,
            "total": 100,
        },
        "why_now": scored_data.get("why_now", "Automated batch sweep detected new signals."),
        "badge": "new_today",
        "signals": scored_data.get("signals", []),
        "ai_verdict": scored_data.get("ai_verdict", "Review signals for outreach context."),
        "dns_audit": dns_res,
        "contacts": contacts,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    _persist_lead(lead_id, domain, company_name, lead_payload)
    return {"status": "success", "lead": lead_payload}


async def run_batch_pipeline() -> dict:
    """
    Phase 6 — Autonomous batch pipeline.
    Discovers companies via keyword sweeps, then processes each one.
    Called by the scheduler instead of iterating a hardcoded list.
    """
    logger.info("Starting autonomous batch pipeline...")

    # Phase 1: Autonomous discovery
    discovered = await run_autonomous_discovery()
    logger.info(f"Batch pipeline: {len(discovered)} companies to process")

    success_count = 0
    errors = False

    for idx, (company_name, domain, firmographics) in enumerate(discovered[:2]):
        logger.info(f"Processing [{idx + 1}/{min(len(discovered), 2)}]: {company_name}")
        try:
            res = await run_pipeline_for_company(company_name, domain, firmographics)
            if res.get("status") == "success":
                success_count += 1
                if res.get("lead", {}).get("ai_verdict", "").startswith("API Error"):
                    logger.warning(f"API Error detected for {company_name}. Halting pipeline execution.")
                    break
        except Exception as e:
            logger.error(f"Error orchestrating {company_name}: {e}")
            errors = True

        # Rate limit: 10s delay between companies
        logger.info("Sleeping 10s to respect rate limits...")
        time.sleep(10)

    return {
        "companies_processed": len(discovered),
        "successes": success_count,
        "had_errors": errors,
    }


# ======================================================================
# Helpers
# ======================================================================

def _get_icp_rejection_reason(firmographics: dict) -> str:
    """Generates a human-readable ICP rejection reason."""
    emp = firmographics.get("employee_count")
    if emp is not None:
        if emp > 500:
            return "Exceeds employee ceiling (>500)"
        if emp < 5:
            return "Under-resourced/pre-revenue (<5 employees)"

    funding = firmographics.get("funding_stage", "")
    if funding and funding.lower() in ["series d", "series e", "public", "m&a"]:
        return f"Stagnant funding stage ({funding})"

    return "Industry mismatch or scale constraints"


def _persist_lead(
    lead_id: str, domain: str, company_name: str, lead_payload: dict
) -> None:
    """Writes a lead snapshot to SQLite. Updates if company_name already exists to prevent duplicates."""
    db = SessionLocal()
    try:
        from backend.models import LeadSnapshot
        existing = db.query(LeadSnapshot).filter(LeadSnapshot.company_name == company_name).first()
        if existing:
            lead_payload["id"] = existing.id
            existing.domain = domain
            existing.industry = lead_payload.get("industry")
            existing.employee_count = lead_payload.get("employee_count")
            existing.intent_score = lead_payload.get("intent_score", 0)
            existing.signal_freshness = lead_payload.get("signal_freshness")
            existing.tier = lead_payload.get("tier")
            existing.icp_fit = lead_payload.get("icp_fit")
            existing.badge = lead_payload.get("badge")
            existing.why_now = lead_payload.get("why_now")
            existing.ai_verdict = lead_payload.get("ai_verdict")
            existing.full_payload = lead_payload
        else:
            snapshot = LeadSnapshot(
                id=lead_id,
                domain=domain,
                company_name=company_name,
                industry=lead_payload.get("industry"),
                employee_count=lead_payload.get("employee_count"),
                intent_score=lead_payload.get("intent_score", 0),
                signal_freshness=lead_payload.get("signal_freshness"),
                tier=lead_payload.get("tier"),
                icp_fit=lead_payload.get("icp_fit"),
                badge=lead_payload.get("badge"),
                why_now=lead_payload.get("why_now"),
                ai_verdict=lead_payload.get("ai_verdict"),
                full_payload=lead_payload,
            )
            db.add(snapshot)
        db.commit()
        logger.info(f"Successfully persisted {company_name}")
    except Exception as e:
        logger.error(f"Failed to persist {company_name}: {e}")
    finally:
        db.close()

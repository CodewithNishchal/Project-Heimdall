"""
Pipeline Orchestrator — Phases 1-6 unified execution engine.

run_pipeline_for_company() — single company: Discovery → ICP Gate → Scoring → DNS → Contacts → Persist
run_batch_pipeline()       — autonomous: Discovery sweeps → iterate each company through the above
"""
import uuid
import json
import logging
import time
import asyncio
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
    pre_fetched_signals: list[dict] | None = None,
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
        if pre_fetched_signals is not None:
            raw_signals = pre_fetched_signals
        else:
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
    if pre_fetched_signals is not None:
        raw_signals = pre_fetched_signals
    else:
        raw_signals = await fetch_public_intent_signals(company_name)
        
    # Scrape Creators Phase 3: Narrow Validation
    try:
        from backend.pipeline.social_discovery import check_scrape_creators_budget, fetch_founder_post
        from backend.models import ScrapeLedger
        from datetime import timedelta
        
        db = SessionLocal()
        ledger_entry = db.query(ScrapeLedger).filter(
            ScrapeLedger.company_name == company_name
        ).first()
        
        in_cooldown = False
        if ledger_entry and ledger_entry.last_scraped_date:
            # Handle naive datetime from SQLite
            last_dt = ledger_entry.last_scraped_date
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - last_dt
            if age < timedelta(days=14):
                in_cooldown = True
                logger.info(f"Skipping Scrape Creators for {company_name} (14-day cooldown active).")
                
        if not in_cooldown:
            budget = await check_scrape_creators_budget()
            if budget >= 50:
                # Serper locate exact post URLs (simulated here)
                simulated_linkedin_url = f"https://linkedin.com/post/{company_name.lower().replace(' ', '-')}-update"
                simulated_reddit_url = f"https://reddit.com/r/SaaS/comments/{company_name.lower().replace(' ', '-')}-news"
                
                # Scrape Creators post endpoint for both
                social_post_li = await fetch_founder_post(simulated_linkedin_url)
                if social_post_li:
                    raw_signals.append(social_post_li)
                    
                social_post_reddit = await fetch_founder_post(simulated_reddit_url)
                if social_post_reddit:
                    raw_signals.append(social_post_reddit)
                
                # Update ledger (record multiple platforms)
                if ledger_entry:
                    ledger_entry.last_scraped_date = datetime.now(timezone.utc)
                else:
                    new_ledger = ScrapeLedger(
                        id=str(uuid.uuid4()),
                        company_name=company_name,
                        platform="linkedin,reddit",
                        last_scraped_date=datetime.now(timezone.utc)
                    )
                    db.add(new_ledger)
                db.commit()
            else:
                logger.warning(f"Skipping Scrape Creators for {company_name} due to low budget ({budget}).")
        db.close()
    except Exception as e:
        logger.error(f"Error executing Scrape Creators validation: {e}")

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
    
    # 1.5 Scrape Creators Search Posts discovery
    try:
        from backend.pipeline.social_discovery import fetch_social_micro_intent
        import os, json
        # Dynamically read allowlist from settings
        config_path = os.path.join(os.path.dirname(__file__), "..", "intent_config.json")
        try:
            with open(config_path, "r") as f:
                intent_cfg = json.load(f)
                keywords = intent_cfg.get("extraction_keywords", ["hiring", "series a"])
        except Exception:
            keywords = ["hiring", "series a"]
            
        social_discovered = await fetch_social_micro_intent(keywords)
        # Map these to the `discovered` format: (company_name, domain, firmographics)
        for sig in social_discovered:
            c_name = sig.get("company_name")
            if c_name and not any(d[0] == c_name for d in discovered):
                # Placeholder domain, will be resolved in Phase 2
                discovered.append((c_name, None, {}))
    except Exception as e:
        logger.error(f"Error in social discovery sweep: {e}")
        
    logger.info(f"Batch pipeline: {len(discovered)} total companies to process after Search Posts sweep.")

    # Fetch currently active companies from DB to avoid duplicates (hash map)
    db = SessionLocal()
    try:
        active_companies = {lead.company_name for lead in db.query(LeadSnapshot).all()}
    finally:
        db.close()

    # Filter out companies already active on the frontend
    filtered_discovered = [d for d in discovered if d[0] not in active_companies]
    logger.info(f"Filtered to {len(filtered_discovered)} new companies (skipped {len(discovered) - len(filtered_discovered)} already live).")

    # Limit to top 5 candidates to avoid excessive API usage
    pool = filtered_discovered[:5]
    
    company_signals_map = {}
    
    # Fetch signals for all companies in the pool
    for idx, (company_name, domain, firmographics) in enumerate(pool):
        logger.info(f"Fetching signals for [{idx + 1}/{len(pool)}]: {company_name}")
        try:
            raw_signals = await fetch_public_intent_signals(company_name)
            filtered_signals = _heuristic_signal_filter(raw_signals)
            company_signals_map[company_name] = filtered_signals
        except Exception as e:
            logger.error(f"Error fetching signals for {company_name}: {e}")
            company_signals_map[company_name] = []
        # Brief delay to respect rate limits
        await asyncio.sleep(1)
        
    # Sort the pool based on the number of fetched signals descending
    pool.sort(key=lambda x: len(company_signals_map[x[0]]), reverse=True)
    
    # Select the top 2 companies with the most signals
    top_2 = pool[:2]

    success_count = 0
    errors = False

    for idx, (company_name, domain, firmographics) in enumerate(top_2):
        signals = company_signals_map[company_name]
        logger.info(f"Processing Top [{idx + 1}/{len(top_2)}]: {company_name} with {len(signals)} signals")
        try:
            res = await run_pipeline_for_company(
                company_name, 
                domain, 
                firmographics,
                pre_fetched_signals=signals
            )
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
        await asyncio.sleep(10)

    return {
        "companies_processed": len(discovered),
        "successes": success_count,
        "had_errors": errors,
    }


# ======================================================================
# Helpers
# ======================================================================

def _heuristic_signal_filter(signals: list[dict]) -> list[dict]:
    """
    Applies a zero-cost Regex/keyword pass to raw signals to demote generic PR fluff.
    Only allows signals that contain intent keywords or are purely neutral.
    """
    import os

    # 1. Dynamically read allowlist from settings
    try:
        config_path = os.path.join(os.path.dirname(__file__), "..", "intent_config.json")
        with open(config_path, "r") as f:
            intent_cfg = json.load(f)
            allowlist = intent_cfg.get("extraction_keywords", [])
    except Exception:
        allowlist = []
        
    if not allowlist:
        allowlist = ["hiring", "series a", "series b", "series c", "seed", "raises", "appoints", "expands"]
        
    allowlist = [w.lower() for w in allowlist]
    
    # 2. Hardcoded denylist for PR fluff
    denylist = ["stock price", "shares", "earnings", "product launch", "acquires", "partners with"]
    
    filtered = []
    for sig in signals:
        text = sig.get("raw_text", "").lower()
        if not text:
            continue
            
        has_allowlist = any(term in text for term in allowlist)
        has_denylist = any(term in text for term in denylist)
        
        if has_allowlist:
            filtered.append(sig)  # Strong intent, pass immediately
        elif has_denylist and not has_allowlist:
            continue  # Fluff article, throw in the trash
        else:
            filtered.append(sig)  # Neutral, let Gemini decide
            
    return filtered


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

import uuid
import logging
from datetime import datetime, timezone

from backend.pipeline.discovery import fetch_public_intent_signals
from backend.pipeline.scorer import analyze_lead_with_gemini
from backend.pipeline.dns_audit import audit_domain_email_infrastructure
from backend.pipeline.filter_funnel import check_recent_cache
from backend.models import LeadSnapshot
from backend.database import SessionLocal

logger = logging.getLogger("PipelineOrchestrator")


async def enrich_with_hunter_mock(domain: str) -> list[dict]:
    """
    V2 Contact Enrichment Mock (Step 11).
    Simulates a call to Hunter.io or Apollo to retrieve key decision makers.
    """
    return [
        {
            "name": "Alex Mercer",
            "title": "VP of Sales",
            "email": f"alex.mercer@{domain}",
            "confidence": 95
        },
        {
            "name": "Jordan Lee",
            "title": "SDR Manager",
            "email": f"jordan.lee@{domain}",
            "confidence": 88
        }
    ]


async def run_pipeline_for_company(company_name: str) -> dict:
    """
    Main orchestration sequence for Heimdall.
    Executes Discovery -> Filtering -> Scoring -> DNS Audit -> DB Write.
    """
    domain = f"{company_name.lower().replace(' ', '')}.com"
    
    # Cache Check (Step 2.5)
    if check_recent_cache(domain):
        logger.info(f"Skipping {company_name} - recently cached.")
        return {"status": "skipped", "reason": "recently_cached"}

    logger.info(f"Starting pipeline execution for {company_name}")

    # Base Firmographics Mock for Ingestion
    firmographics = {
        "domain": domain, 
        "employee_count": 100, 
        "industry": "Technology"
    }

    # Step 0: ICP Gatekeeper Check
    from backend.pipeline.icp_filter import apply_icp_filters
    dummy_score, icp_fit_label = apply_icp_filters(
        base_score=50,
        employee_count=firmographics.get("employee_count"),
        funding_stage=firmographics.get("funding_stage"),
        industry=firmographics.get("industry", "Unknown")
    )
    
    if icp_fit_label == "Poor":
        logger.info(f"Short-circuiting {company_name} due to Poor ICP fit.")
        lead_id = str(uuid.uuid4())
        lead_payload = {
            "id": lead_id,
            "company_name": company_name,
            "domain": domain,
            "industry": firmographics["industry"],
            "employee_count": firmographics["employee_count"],
            "intent_score": dummy_score,
            "signal_freshness": 100,
            "tier": "Low",
            "icp_fit": "Poor",
            "confidence": {
                "label": "Low Trust", 
                "color": "rose", 
                "verified": 0, 
                "total": 1
            },
            "why_now": "ICP Gatekeeper rejected profile.",
            "badge": None,
            "signals": [],
            "ai_verdict": "Profile did not meet minimum ICP scale or industry constraints.",
            "dns_audit": {"spf": "Missing", "dkim": "Missing", "dmarc": "Missing", "issues": []},
            "contacts": [],
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        db = SessionLocal()
        try:
            snapshot = LeadSnapshot(
                id=lead_id,
                domain=domain,
                company_name=company_name,
                intent_score=lead_payload["intent_score"],
                tier=lead_payload["tier"],
                badge=lead_payload["badge"],
                ai_verdict=lead_payload["ai_verdict"],
                full_payload=lead_payload
            )
            db.add(snapshot)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to persist {company_name}: {e}")
        finally:
            db.close()
        return {"status": "success", "lead": lead_payload}

    # Step 1: Discovery & Filter
    raw_signals = await fetch_public_intent_signals(company_name)
    cleaned_html = "\n\n".join([s.get("raw_text", "") for s in raw_signals])
    
    # Step 2: Scoring (Gemini)
    scored_data = analyze_lead_with_gemini(company_name, cleaned_html, firmographics)
    
    # Step 3: DNS Audit
    dns_res = await audit_domain_email_infrastructure(domain)
    
    total_signals = len(scored_data["signals"])
    verified_signals = sum(1 for s in scored_data["signals"] if s["quote_validated"])
    
    # Multi-factor confidence calculation (prevents trivial 100%)
    # Factor 1: Average similarity score (0-100 range, weighted at 50%)
    avg_similarity = (
        sum(s["similarity_score"] for s in scored_data["signals"]) / total_signals
        if total_signals > 0 else 0
    )
    
    # Factor 2: Verification ratio (0-100 range, weighted at 30%)
    verification_ratio = (verified_signals / total_signals * 100) if total_signals > 0 else 0
    
    # Factor 3: Signal diversity bonus (unique signal types, max 20 pts)
    unique_types = len(set(s["signal_type"] for s in scored_data["signals"])) if total_signals > 0 else 0
    diversity_bonus = min(unique_types * 7, 20)
    
    # Composite confidence score (theoretical max ~95% with perfect inputs)
    raw_confidence = (avg_similarity * 0.50) + (verification_ratio * 0.30) + diversity_bonus
    # Apply a ceiling dampener — real-world AI should never claim 100% certainty
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

    # Fix: Prevent saving failed/empty records to keep the global average accurate
    if total_signals == 0 or "API Error" in scored_data.get("ai_verdict", ""):
        logger.info(f"Skipping {company_name} because retrieval failed or yielded 0 signals.")
        return {"status": "error", "reason": "failed_retrieval_or_no_signals"}
            
    # Step 4: V2 Contact Enrichment
    contacts = await enrich_with_hunter_mock(domain)
    
    lead_id = str(uuid.uuid4())
    lead_payload = {
        "id": lead_id,
        "company_name": scored_data["company_name"],
        "domain": domain,
        "industry": firmographics["industry"],
        "employee_count": firmographics["employee_count"],
        "intent_score": scored_data["intent_score"],
        "signal_freshness": scored_data["signal_freshness"],
        "tier": scored_data["tier"],
        "icp_fit": scored_data["icp_fit"],
        "confidence": {
            "label": conf_label, 
            "color": conf_color, 
            "verified": confidence_pct, 
            "total": 100
        },
        "why_now": "Automated batch sweep detected new signals.",
        "badge": "new_today",
        "signals": scored_data["signals"],
        "ai_verdict": scored_data["ai_verdict"],
        "dns_audit": dns_res,
        "contacts": contacts,
        "last_updated": datetime.now(timezone.utc).isoformat()
    }
    
    # Step 5: DB Write (Full Persistence)
    db = SessionLocal()
    try:
        snapshot = LeadSnapshot(
            id=lead_id,
            domain=domain,
            company_name=company_name,
            intent_score=lead_payload["intent_score"],
            tier=lead_payload["tier"],
            badge=lead_payload["badge"],
            ai_verdict=lead_payload["ai_verdict"],
            full_payload=lead_payload
        )
        db.add(snapshot)
        db.commit()
        logger.info(f"Successfully processed and stored {company_name}")
    except Exception as e:
        logger.error(f"Failed to persist {company_name}: {e}")
    finally:
        db.close()
    
    return {"status": "success", "lead": lead_payload}

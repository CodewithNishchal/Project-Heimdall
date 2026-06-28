from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.database import engine, Base, get_db
from backend import models
from backend.pipeline.dns_audit import audit_domain_email_infrastructure
from backend.pipeline.filter_funnel import trim_html_for_llm, passes_keyword_gate
from backend.validation.quote_validator import validate_quote
from backend.pipeline.scorer import process_hybrid_lead_scoring
from backend.scheduler.pipeline_scheduler import run_pipeline_job
from backend.routers import pipeline, leads


# ======================================================================
# Database initialization — creates all ORM tables on startup
# ======================================================================
Base.metadata.create_all(bind=engine)


# ======================================================================
# Background scheduler — managed via FastAPI lifespan (audit fix)
# Prevents duplicate threads on uvicorn --reload
# ======================================================================
scheduler = BackgroundScheduler(timezone='UTC')

from datetime import timedelta

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Delayed start: wait 12 hours before first run
    start_date = datetime.now(timezone.utc) + timedelta(hours=12)
    scheduler.add_job(
        func=run_pipeline_job,
        trigger=IntervalTrigger(hours=12, start_date=start_date)
    )
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


# ======================================================================
# Application instance
# ======================================================================
app = FastAPI(
    title="Heimdall Intel Platform API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ======================================================================
# Mount routers from Stage 4 & 5
# ======================================================================
app.include_router(pipeline.router)
app.include_router(leads.router)


# ======================================================================
# Direct routes (cumulative from Stages 1-3)
# ======================================================================

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "stage": 5,
        "scheduler_status": "active_running"
    }


@app.get("/api/audit/dns")
def execute_dns_audit(domain: str):
    """Direct programmatic debugging route for infrastructure audits. (Stage 1)"""
    return audit_domain_email_infrastructure(domain)


class FilterRequest(BaseModel):
    raw_html: str


class ValidationPayload(BaseModel):
    quote: str
    source_text: str


@app.post("/api/filter/simulate")
def simulate_filter_funnel(payload: FilterRequest):
    """Programmatic staging endpoint evaluating structural data reduction. (Stage 2)"""
    cleaned_text = trim_html_for_llm(payload.raw_html)
    matches_gate = passes_keyword_gate(cleaned_text)

    return {
        "character_count_before": len(payload.raw_html),
        "character_count_after": len(cleaned_text),
        "passes_keyword_gate": matches_gate,
        "sample_preview": cleaned_text[:300]
    }


@app.post("/api/validation/verify-quote")
def verify_extracted_quote(payload: ValidationPayload):
    """Validates the alignment of an extracted quote against the source material. (Stage 2)"""
    success, score = validate_quote(payload.quote, payload.source_text)
    return {
        "is_valid": success,
        "similarity_score": score,
        "action_taken": "Proceed" if success else "Discard Signal"
    }


@app.get("/api/score/simulate")
def simulate_scoring_pipeline():
    """Simulates scoring and returns a full strict LeadDetailResponse payload."""
    mock_llm_json = {
        "company_name": "Crework Labs",
        "intent_score": 85,
        "signals": [
            {
                "signal_type": "sdr_hiring",
                "verbatim_quote": "Looking for high-velocity SDR leadership",
                "event_date": "2026-06-15T12:00:00Z"
            },
            {
                "signal_type": "growth_news",
                "verbatim_quote": "expanding its global B2B footprint",
                "event_date": "2026-02-10T12:00:00Z"
            }
        ],
        "ai_verdict": "High conversion potential for outbound agency services."
    }

    mock_firmographics = {
        "employee_count": 45,
        "funding_stage": "Seed",
        "industry": "Software Development"
    }

    scored_payload = process_hybrid_lead_scoring(
        mock_llm_json, mock_firmographics
    )
    verified_count = sum(
        1 for signal in scored_payload["signals"]
        if signal["quote_validated"]
    )

    return {
        "id": "score-sim-1",
        "company_name": scored_payload["company_name"],
        "domain": "creworklabs.com",
        "industry": mock_firmographics["industry"],
        "employee_count": mock_firmographics["employee_count"],
        "funding_stage": mock_firmographics["funding_stage"],
        "intent_score": scored_payload["intent_score"],
        "signal_freshness": scored_payload["signal_freshness"],
        "tier": scored_payload["tier"],
        "icp_fit": scored_payload["icp_fit"],
        "confidence": {
            "label": "High Trust" if verified_count else "Low Trust",
            "color": "emerald" if verified_count else "rose",
            "verified": verified_count,
            "total": len(scored_payload["signals"])
        },
        "why_now": "Validated SDR hiring and growth signals detected in the scoring simulation.",
        "badge": "signal_added",
        "signals": scored_payload["signals"],
        "ai_verdict": scored_payload["ai_verdict"],
        "dns_audit": audit_domain_email_infrastructure("creworklabs.com"),
        "last_updated": datetime.now(timezone.utc).isoformat()
    }

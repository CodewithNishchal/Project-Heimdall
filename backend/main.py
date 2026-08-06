from dotenv import load_dotenv
load_dotenv("backend/.env", override=True)
# Reload trigger: 2026-07-25 14:13

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.config import settings
from backend.database import engine, Base, get_db
from backend import models
from backend.pipeline.dns_audit import audit_domain_email_infrastructure
from backend.pipeline.filter_funnel import trim_html_for_llm, passes_keyword_gate
from backend.validation.quote_validator import validate_quote
from backend.pipeline.scorer import process_hybrid_lead_scoring
from backend.routers import pipeline, leads


# ======================================================================
# Database initialization — creates all ORM tables & auto-migrates columns
# ======================================================================
try:
    from sqlalchemy import text
    with engine.connect() as conn:
        if not settings.DATABASE_URL.startswith("sqlite"):
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS heimdall;"))
            conn.execute(text("ALTER TABLE lead_snapshots ADD COLUMN IF NOT EXISTS company_segment VARCHAR(255) DEFAULT 'Growth Scale-up';"))
            conn.execute(text("ALTER TABLE lead_snapshots ADD COLUMN IF NOT EXISTS why_now TEXT DEFAULT 'Verified public buying intent triggers detected.';"))
            conn.execute(text("ALTER TABLE lead_snapshots ADD COLUMN IF NOT EXISTS signal_tags JSONB DEFAULT '[]'::jsonb;"))
            conn.execute(text("ALTER TABLE lead_snapshots ADD COLUMN IF NOT EXISTS annual_revenue TEXT;"))
            conn.execute(text("ALTER TABLE social_posts ADD COLUMN IF NOT EXISTS summary TEXT;"))
        else:
            try:
                conn.execute(text("ALTER TABLE lead_snapshots ADD COLUMN company_segment TEXT DEFAULT 'Growth Scale-up';"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE lead_snapshots ADD COLUMN why_now TEXT DEFAULT 'Verified public buying intent triggers detected.';"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE lead_snapshots ADD COLUMN signal_tags JSON DEFAULT '[]';"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE social_posts ADD COLUMN summary TEXT;"))
            except Exception:
                pass
            try:
                conn.execute(text("ALTER TABLE lead_snapshots ADD COLUMN annual_revenue TEXT;"))
            except Exception:
                pass
        conn.commit()
    Base.metadata.create_all(bind=engine)
except Exception as e:
    import logging
    logging.getLogger("uvicorn").error(f"Database initialization warning: {e}")


# ======================================================================
# Background scheduler — managed via FastAPI lifespan (audit fix)
# Prevents duplicate threads on uvicorn --reload
# ======================================================================
scheduler = BackgroundScheduler(timezone='UTC')

def backfill_missing_timestamps():
    """Backfills missing last_updated timestamps in existing DB snapshots."""
    from backend.database import SessionLocal
    from backend.models import LeadSnapshot
    db = SessionLocal()
    try:
        leads = db.query(LeadSnapshot).all()
        now_dt = datetime.now(timezone.utc)
        updated_count = 0
        for lead in leads:
            if not lead.last_updated:
                lead.last_updated = now_dt
                updated_count += 1
            if lead.full_payload and isinstance(lead.full_payload, dict):
                if not lead.full_payload.get("last_updated"):
                    payload = dict(lead.full_payload)
                    payload["last_updated"] = (lead.last_updated or now_dt).isoformat()
                    lead.full_payload = payload
                    updated_count += 1
        if updated_count > 0:
            db.commit()
    except Exception as err:
        import logging
        logging.getLogger("uvicorn").error(f"Backfill timestamp warning: {err}")
    finally:
        db.close()

from apscheduler.triggers.cron import CronTrigger
import asyncio

def run_async_midnight_cron():
    asyncio.run(trigger_midnight_cron_run(daily_quota=30))

from backend.pipeline.streaming_orchestrator import trigger_midnight_cron_run

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Backfill timestamps for existing DB snapshots
    backfill_missing_timestamps()
    # Daily 2:00 AM Cron Execution
    scheduler.add_job(
        func=run_async_midnight_cron,
        trigger=CronTrigger(hour=2, minute=0, timezone='UTC')
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
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ======================================================================
# Mount routers from Stage 4 & 5
# ======================================================================
app.include_router(pipeline.router)
app.include_router(leads.router)

from backend.routers import settings, social_posts
app.include_router(settings.router)
app.include_router(social_posts.router)


# ======================================================================
# Direct routes (cumulative from Stages 1-3)
# ======================================================================

@app.get("/")
@app.head("/")
@app.get("/api/health")
@app.head("/api/health")
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

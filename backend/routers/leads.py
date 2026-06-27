from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal, Optional, List, cast
from datetime import datetime, timezone
import uuid

from backend.pipeline.discovery import fetch_public_intent_signals
from backend.pipeline.scorer import analyze_lead_with_gemini
from backend.pipeline.dns_audit import audit_domain_email_infrastructure
from backend.models import LeadSnapshot
from backend.database import SessionLocal

router = APIRouter(prefix="/api/leads", tags=["Lead Intelligence Operations"])


# ======================================================================
# Pydantic models — STRICT DATA CONTRACT PROTOCOL
# All keys match the contract exactly. Do not shorten or modify casing.
# ======================================================================

class SignalModel(BaseModel):
    """Extracted Signal Objective Object"""
    signal_type: str
    verbatim_quote: str
    quote_validated: bool
    similarity_score: float
    source_url: Optional[str] = None
    recency_label: str
    score_contribution: float


class DNSAuditModel(BaseModel):
    """DNS Audit Objective Object"""
    spf: str
    dkim: str
    dmarc: str
    issues: List[str]


class ConfidenceModel(BaseModel):
    """Confidence Evaluation Object"""
    label: str
    color: str
    verified: int
    total: int


class LeadDetailResponse(BaseModel):
    """
    Master Lead Object — Strict Data Contract Protocol.

    Fields:
        intent_score:      DO NOT use 'score'
        signal_freshness:  DO NOT use 'freshness'
        badge:             'new_today' | 'score_up' | 'score_down' | 'signal_added' | null
    """
    id: str
    company_name: str
    domain: str
    industry: str
    employee_count: Optional[int] = None
    funding_stage: Optional[str] = None
    intent_score: int
    signal_freshness: int
    tier: Literal["High", "Medium", "Low"]
    icp_fit: Literal["Strong", "Partial", "Poor"]
    confidence: ConfidenceModel
    why_now: str
    badge: Optional[Literal["new_today", "score_up", "score_down", "signal_added"]] = None
    signals: List[SignalModel]
    ai_verdict: str
    dns_audit: DNSAuditModel
    last_updated: str


# ======================================================================
# API Endpoints
# ======================================================================

@router.get("/", response_model=List[LeadDetailResponse])
def list_all_leads():
    """Returns a list of all processed leads from the database."""
    db = SessionLocal()
    try:
        leads = db.query(LeadSnapshot).all()
        return [lead.full_payload for lead in leads if lead.full_payload]
    finally:
        db.close()


@router.get("/{lead_id}", response_model=LeadDetailResponse)
def get_lead_profile_details(lead_id: str):
    """Fetches full analytical records along with data ledger validation quotes."""
    db = SessionLocal()
    try:
        lead = db.query(LeadSnapshot).filter(LeadSnapshot.id == lead_id).first()
        if not lead or not lead.full_payload:
            raise HTTPException(
                status_code=404,
                detail="Requested lead tracking index not found."
            )
        return lead.full_payload
    finally:
        db.close()


@router.delete("/{lead_id}")
def delete_lead_record(lead_id: str):
    """Removes a lead record from the persistent tracking database."""
    db = SessionLocal()
    try:
        lead = db.query(LeadSnapshot).filter(LeadSnapshot.id == lead_id).first()
        if not lead:
            raise HTTPException(
                status_code=404,
                detail="Lead tracking index not found."
            )
        db.delete(lead)
        db.commit()
        return {"status": "deleted", "id": lead_id}
    finally:
        db.close()


@router.post("/{lead_id}/verdict")
def get_lazy_loaded_pitch_verdict(lead_id: str):
    """
    Lazy-loads tailored target email copy on click via Gemini API. (POST to
    prevent browser/Next.js prefetching from triggering expensive AI calls.)
    """
    db = SessionLocal()
    try:
        lead_snap = db.query(LeadSnapshot).filter(LeadSnapshot.id == lead_id).first()
        if not lead_snap or not lead_snap.full_payload:
            raise HTTPException(
                status_code=404,
                detail="Requested lead target vector not found."
            )
        lead = LeadDetailResponse(**cast(dict, lead_snap.full_payload))
    finally:
        db.close()

    from google import genai
    from google.genai import types
    from backend.config import settings
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    signals_text = "\n".join(
        [f"- {s.signal_type}: {s.verbatim_quote}" for s in lead.signals]
    )
    prompt = (
        f"Write a short, punchy cold email to {lead.company_name} "
        f"referencing these signals:\n{signals_text}"
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                system_instruction="You are an expert SDR. Write cold emails."
            )
        )
        email_body = response.text
    except Exception:
        # Fallback if API fails or isn't configured
        sig_quote = (
            lead.signals[-1].verbatim_quote
            if lead.signals else "recent developments"
        )
        email_body = (
            f"Hi team,\n\n"
            f"I noticed that {lead.company_name} is currently focusing "
            f"heavily on {sig_quote[:40]}...\n\n"
            f"Building an internal team takes months. We can stand up an "
            f"outbound machine to support this pivot in 2 weeks.\n\n"
            f"Let's chat,\nSales Ops"
        )

    return {
        "lead_id": lead_id,
        "subject_line": (
            f"Outbound scaling infrastructure blueprint for "
            f"{lead.company_name}"
        ),
        "email_body": email_body
    }


class IngestRequest(BaseModel):
    company_name: str


@router.post("/ingest", response_model=LeadDetailResponse)
async def ingest_new_lead(req: IngestRequest):
    """
    Manually injects a company name into the pipeline by delegating to the 
    Orchestrator to standardize the LLM engines (Gemini) and full persistence.
    """
    from backend.pipeline.orchestrator import run_pipeline_for_company
    
    res = await run_pipeline_for_company(req.company_name)
    if res.get("status") == "success":
        return res["lead"]
    elif res.get("status") == "skipped":
        raise HTTPException(status_code=400, detail="Lead was recently cached.")
    
    raise HTTPException(status_code=500, detail="Failed to ingest lead.")

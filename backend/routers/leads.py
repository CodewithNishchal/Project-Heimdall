from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal, Optional, List, cast
from datetime import datetime, timezone
import uuid
import logging

logger = logging.getLogger("LeadsRouter")

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


class ContactModel(BaseModel):
    """Extracted Contact Object"""
    name: str
    title: str
    email: str
    confidence: str | int
    source: Optional[str] = None


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
    badge: Optional[Literal["new_today", "score_up", "score_down", "signal_added", "filtered"]] = None
    signals: List[SignalModel]
    ai_verdict: str
    dns_audit: DNSAuditModel
    contacts: List[ContactModel] = []
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
    Phase 5.5 — Pitcher Mode. Uses Claude Haiku for high-quality cold email
    generation. Falls back to Gemini if Claude API key is not configured.
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

    from backend.config import settings

    # Try Claude Haiku first (better prose quality for cold emails)
    if settings.CLAUDE_API_KEY:
        result = _generate_pitch_with_claude(lead, settings.CLAUDE_API_KEY)
        if result:
            return {"lead_id": lead_id, **result}

    # Fallback to Gemini
    result = _generate_pitch_with_gemini(lead)
    return {"lead_id": lead_id, **result}


def _generate_pitch_with_claude(lead: LeadDetailResponse, api_key: str) -> dict | None:
    """
    Claude Haiku pitcher — produces noticeably better short-form persuasive copy.
    Uses regex JSON extraction since Claude doesn't have native JSON mode.
    """
    import re
    import json

    try:
        import anthropic
        claude = anthropic.Anthropic(api_key=api_key)

        contact_title = "Founder"
        if hasattr(lead, "contacts") and lead.contacts:
            # contacts may be dicts in the payload
            first_contact = lead.contacts[0]
            if isinstance(first_contact, dict):
                contact_title = first_contact.get("title", "Founder")

        prompt = f"""Write a 3-line cold email opener for {lead.company_name}.
Signal: {lead.why_now}
Contact title: {contact_title}

CRITICAL INSTRUCTIONS:
1. The opening line MUST reference the specific signal type as the hook (e.g., if hiring two different roles, call out scaling two sales motions at once). Do NOT use generic openers like 'Saw you're building out the sales team'.
2. Quantify the specific pain that the signal creates (e.g., 'outside reps take 60-90 days to ramp while the pipeline gap compounds').
3. Make the value proposition concrete (e.g., 'We help bridge that by standing up outbound coverage from day one').

Tone: direct, no fluff, no 'Hope this finds you well'. Do not add a P.S. that introduces new concepts.
Return JSON: {{"subject_line": string, "email_body": string}}"""

        response = claude.messages.create(
            model="claude-haiku-4-5",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text
        # Safe Extraction: Strip any markdown code fences or conversational preambles
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            return {
                "subject_line": parsed.get("subject_line", f"Quick note about {lead.company_name}"),
                "email_body": parsed.get("email_body", raw),
            }
        return {"subject_line": f"Quick note about {lead.company_name}", "email_body": raw}
    except Exception as e:
        logger.warning(f"Claude pitcher failed for {lead.company_name}: {e}, falling back to Gemini")
        return None


def _generate_pitch_with_gemini(lead: LeadDetailResponse) -> dict:
    """Gemini fallback pitcher — used when Claude API key is not set or fails."""
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
                system_instruction="You are an expert SDR. Write cold emails.",
            ),
        )
        email_body = response.text
    except Exception:
        sig_quote = (
            lead.signals[-1].verbatim_quote
            if lead.signals
            else "recent developments"
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
        "subject_line": f"Outbound scaling infrastructure blueprint for {lead.company_name}",
        "email_body": email_body,
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

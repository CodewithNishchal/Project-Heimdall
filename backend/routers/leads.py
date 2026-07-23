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
    social_segment: Optional[str] = None
    meta_ads_active: Optional[bool] = False
    meta_ads_count: Optional[int] = 0
    bio_url: Optional[str] = None
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
    """Returns a list of all processed leads from the database with bounded confidence scores."""
    db = SessionLocal()
    try:
        leads = db.query(LeadSnapshot).all()
        results = []
        for lead in leads:
            if not lead.full_payload:
                continue
            payload = dict(lead.full_payload)
            if isinstance(payload.get("confidence"), dict):
                ver = payload["confidence"].get("verified", 0)
                if ver > 100:
                    payload["confidence"]["verified"] = min(100, max(0, ver // 40))
            results.append(payload)
        return results
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
        payload = dict(lead.full_payload)
        if isinstance(payload.get("confidence"), dict):
            ver = payload["confidence"].get("verified", 0)
            if ver > 100:
                payload["confidence"]["verified"] = min(100, max(0, ver // 40))
        return payload
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

    # Try Grok API first
    if settings.GROK_API_KEY:
        result = _generate_summary_with_grok(lead, settings.GROK_API_KEY)
        if result:
            return {"lead_id": lead_id, **result}
            
    # Fallback to Claude API
    if settings.CLAUDE_API_KEY:
        result = _generate_summary_with_claude(lead, settings.CLAUDE_API_KEY)
        if result:
            return {"lead_id": lead_id, **result}

    # Final Fallback to Gemini
    result = _generate_pitch_with_gemini(lead)
    return {"lead_id": lead_id, **result}

def _generate_summary_with_claude(lead: LeadDetailResponse, api_key: str) -> dict | None:
    """
    Uses Anthropic's Claude API to generate the intent summary.
    """
    import json
    import httpx
    import re

    try:
        signals_text = "\n".join([f"- {s.signal_type}: {s.verbatim_quote}" for s in lead.signals]) if lead.signals else "No specific signals extracted."
        
        prompt = f"""Generate a point-wise summary of intent signals for {lead.company_name}.

Main AI Verdict: {lead.ai_verdict}

Extracted Intent Signals:
{signals_text}

CRITICAL INSTRUCTIONS:
1. Do NOT write an email. Do NOT include greetings (e.g., 'Hi [Name]') or sign-offs (e.g., 'Best').
2. Create a perfect point-wise brief of all the intent layers fetched from the AI verdict and the extracted signals.
3. The output MUST be a bulleted summary report designed to be shown to a non-tech user.
4. Keep it clear, concise, and highly informative.
5. Your entire response must be a valid JSON object matching exactly this schema: {{"subject_line": "Intent Summary for [Company]", "email_body": "markdown bulleted summary text"}}"""

        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1024,
                "system": "You are an expert analyst. You always output raw JSON without markdown blocks.",
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=30.0
        )
        response.raise_for_status()
        raw = response.json()["content"][0]["text"]
        
        # Safe Extraction
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            return {
                "subject_line": parsed.get("subject_line", f"Intent Summary for {lead.company_name}"),
                "email_body": parsed.get("email_body", raw),
                "model_used": "Claude 3 Haiku"
            }
    except Exception as e:
        print(f"[Claude API Error] {e}")
    return None


def _generate_summary_with_grok(lead: LeadDetailResponse, api_key: str) -> dict | None:
    """
    Uses xAI's Grok API to generate the intent summary.
    """
    import json
    import httpx
    import re

    try:
        signals_text = "\n".join([f"- {s.signal_type}: {s.verbatim_quote}" for s in lead.signals]) if lead.signals else "No specific signals extracted."
        
        prompt = f"""Generate a point-wise summary of intent signals for {lead.company_name}.

Main AI Verdict: {lead.ai_verdict}

Extracted Intent Signals:
{signals_text}

CRITICAL INSTRUCTIONS:
1. Do NOT write an email. Do NOT include greetings (e.g., 'Hi [Name]') or sign-offs (e.g., 'Best').
2. Create a perfect point-wise brief of all the intent layers fetched from the AI verdict and the extracted signals.
3. The output MUST be a bulleted summary report designed to be shown to a non-tech user.
4. Keep it clear, concise, and highly informative.

Return JSON: {{"subject_line": "Intent Summary for {lead.company_name}", "email_body": string (the summary formatted in markdown bullet points)}}"""

        response = httpx.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "grok-beta",
                "messages": [
                    {"role": "system", "content": "You are an expert analyst. Always output valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"}
            },
            timeout=30.0
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        
        # Safe Extraction
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
            return {
                "subject_line": parsed.get("subject_line", f"Intent Summary for {lead.company_name}"),
                "email_body": parsed.get("email_body", raw),
            }
        return {"subject_line": f"Intent Summary for {lead.company_name}", "email_body": raw}
    except Exception as e:
        logger.warning(f"Grok summarizer failed for {lead.company_name}: {e}, falling back to Gemini")
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
        f"Generate a point-wise summary of intent signals for {lead.company_name}.\n\n"
        f"AI Verdict: {lead.ai_verdict}\n\n"
        f"Extracted Signals:\n{signals_text}\n\n"
        f"CRITICAL INSTRUCTIONS:\n"
        f"1. Do NOT write an email. Do NOT include greetings or sign-offs.\n"
        f"2. Create a perfect point-wise brief of all intent layers.\n"
        f"3. Output MUST be markdown bullet points without any conversational filler."
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                system_instruction="You are an expert SDR analyst. Generate objective summary reports.",
            ),
        )
        email_body = response.text
    except Exception:
        email_body = (
            f"### Intent Summary for {lead.company_name}\n\n"
            f"- **Verdict:** {lead.ai_verdict}\n"
            f"- **Signals:** {len(lead.signals)} intent signals processed."
        )

    return {
        "subject_line": f"Intent Summary for {lead.company_name}",
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

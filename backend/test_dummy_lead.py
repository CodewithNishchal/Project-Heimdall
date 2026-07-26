"""
Test: Insert a dummy lead via _persist_lead and leave it in the DB.
Refresh your website after running to see if it appears.

To clean up later, run:  uv run python backend/test_dummy_lead.py --cleanup

Usage:
  uv run python backend/test_dummy_lead.py
"""
import sys
import os
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal
from backend.models import LeadSnapshot
from backend.pipeline.orchestrator import _persist_lead
from datetime import datetime, timezone

# Fixed ID so we can clean it up later
DUMMY_LEAD_ID = "test-dummy-lead-00001"
DUMMY_COMPANY = "Zenith Test Corp"
DUMMY_DOMAIN = "zenith-test-corp.com"


def insert_dummy():
    print("=" * 60)
    print("🧪 Inserting Dummy Lead (will NOT be deleted)")
    print("=" * 60)

    lead_payload = {
        "id": DUMMY_LEAD_ID,
        "company_name": DUMMY_COMPANY,
        "domain": DUMMY_DOMAIN,
        "industry": "B2B SaaS",
        "employee_count": 120,
        "intent_score": 88,
        "signal_freshness": 92,
        "tier": "High",
        "icp_fit": "Strong",
        "confidence": {
            "label": "High Trust",
            "color": "emerald",
            "verified": 82,
            "total": 100,
        },
        "why_now": "Series B funding of $25M closed in July 2026, hiring 15+ marketing roles.",
        "badge": "new_today",
        "signals": [
            {
                "signal_type": "funding_round",
                "verbatim_quote": "Zenith Test Corp raises $25M Series B to expand go-to-market operations.",
                "quote_validated": True,
                "similarity_score": 0.92,
                "source_url": "https://techcrunch.com/2026/07/20/zenith-test-corp-series-b",
                "recency_label": "This Week",
                "score_contribution": 25.0,
                "event_date": "2026-07-20",
            },
            {
                "signal_type": "hiring_spike",
                "verbatim_quote": "Zenith is hiring 15 new marketing and growth roles across 3 regions.",
                "quote_validated": True,
                "similarity_score": 0.87,
                "source_url": "https://linkedin.com/company/zenith-test-corp/jobs",
                "recency_label": "This Month",
                "score_contribution": 20.0,
                "event_date": "2026-07-15",
            },
        ],
        "ai_verdict": "Zenith Test Corp just closed a $25M Series B and is aggressively hiring for marketing roles.\nStrong outreach candidate for growth marketing and paid media services.",
        "dns_audit": {
            "spf": "pass",
            "dkim": "pass",
            "dmarc": "v=DMARC1; p=reject",
            "issues": [],
        },
        "contacts": [
            {"name": "Alex Rivera", "title": "VP of Marketing", "email": "alex@zenith-test-corp.com", "confidence": "verified", "source": "regex"},
            {"name": "Sarah Chen", "title": "Head of Growth", "email": "sarah@zenith-test-corp.com", "confidence": "generated", "source": "linkedin"},
        ],
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    print(f"\n  Company:  {DUMMY_COMPANY}")
    print(f"  Domain:   {DUMMY_DOMAIN}")
    print(f"  Score:    {lead_payload['intent_score']}")
    print(f"  Tier:     {lead_payload['tier']}")
    print()

    _persist_lead(DUMMY_LEAD_ID, DUMMY_DOMAIN, DUMMY_COMPANY, lead_payload)

    # Verify
    db = SessionLocal()
    try:
        record = db.query(LeadSnapshot).filter(LeadSnapshot.id == DUMMY_LEAD_ID).first()
        if record and record.full_payload:
            print("✅ Lead inserted and verified in database!")
            print("👉 Refresh your website now to see it.\n")
        else:
            print("❌ Lead was NOT found after insert.\n")
    finally:
        db.close()


def cleanup():
    print("🧹 Cleaning up dummy lead...")
    db = SessionLocal()
    try:
        record = db.query(LeadSnapshot).filter(LeadSnapshot.id == DUMMY_LEAD_ID).first()
        if record:
            db.delete(record)
            db.commit()
            print(f"✅ Deleted '{DUMMY_COMPANY}' from database.\n")
        else:
            print("⚠️  Dummy lead not found — already cleaned up.\n")
    finally:
        db.close()


if __name__ == "__main__":
    if "--cleanup" in sys.argv:
        cleanup()
    else:
        insert_dummy()

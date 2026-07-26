"""
Test script: Verifies that _persist_lead correctly writes to the database.
Inserts a dummy lead, reads it back, prints the result, then cleans up.

Usage:
  cd "c:\IIITN\Semester 7\Z-Intern\Crework\Project Heimdial"
  uv run python backend/test_db_insert.py
"""
import sys
import os
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal
from backend.models import LeadSnapshot
from backend.pipeline.orchestrator import _persist_lead

SEPARATOR = "=" * 60

def run_test():
    test_lead_id = str(uuid.uuid4())
    test_domain = "test-heimdall-insert.com"
    test_company = f"Heimdall DB Test Co {uuid.uuid4().hex[:6]}"

    print(SEPARATOR)
    print("🧪 Heimdall DB Insert Test")
    print(SEPARATOR)
    print(f"  Lead ID:      {test_lead_id}")
    print(f"  Domain:       {test_domain}")
    print(f"  Company Name: {test_company}")
    print()

    # Build a realistic lead payload
    lead_payload = {
        "id": test_lead_id,
        "company_name": test_company,
        "domain": test_domain,
        "industry": "B2B SaaS",
        "employee_count": 75,
        "intent_score": 82,
        "signal_freshness": 95,
        "tier": "High",
        "icp_fit": "Strong",
        "confidence": {
            "label": "High Trust",
            "color": "emerald",
            "verified": 78,
            "total": 100,
        },
        "why_now": "Recent Series B funding + aggressive hiring spike.",
        "badge": "new_today",
        "signals": [
            {
                "signal_type": "funding_round",
                "verbatim_quote": "Company raised $20M in Series B",
                "source_url": "https://example.com/news/funding",
                "event_date": "2026-07-20",
            }
        ],
        "ai_verdict": "Strong growth signals detected. Ideal outreach target for marketing services.",
        "dns_audit": {"mx": "google", "spf": True},
        "contacts": [{"name": "Jane Doe", "title": "CMO", "email": "jane@test.com"}],
        "last_updated": "2026-07-26T14:00:00+00:00",
    }

    # --- Step 1: Insert ---
    print("📝 Step 1: Calling _persist_lead()...")
    try:
        _persist_lead(test_lead_id, test_domain, test_company, lead_payload)
        print("   ✅ _persist_lead() completed without error.\n")
    except Exception as e:
        print(f"   ❌ _persist_lead() FAILED: {e}\n")
        return

    # --- Step 2: Read back ---
    print("🔍 Step 2: Querying database for the inserted record...")
    db = SessionLocal()
    try:
        record = db.query(LeadSnapshot).filter(LeadSnapshot.id == test_lead_id).first()
        if record:
            print("   ✅ Record FOUND in database!")
            print(f"      Company:      {record.company_name}")
            print(f"      Domain:       {record.domain}")
            print(f"      Industry:     {record.industry}")
            print(f"      Employees:    {record.employee_count}")
            print(f"      Intent Score: {record.intent_score}")
            print(f"      Tier:         {record.tier}")
            print(f"      ICP Fit:      {record.icp_fit}")
            print(f"      AI Verdict:   {record.ai_verdict}")
            print(f"      Full Payload: {'Present (' + str(len(str(record.full_payload))) + ' chars)' if record.full_payload else 'MISSING'}")
            print()
            test_passed = True
        else:
            print("   ❌ Record NOT FOUND. Insert failed silently.")
            print()
            test_passed = False
    finally:
        db.close()

    # --- Step 3: Cleanup ---
    print("🧹 Step 3: Cleaning up test record...")
    db = SessionLocal()
    try:
        record = db.query(LeadSnapshot).filter(LeadSnapshot.id == test_lead_id).first()
        if record:
            db.delete(record)
            db.commit()
            print("   ✅ Test record deleted successfully.\n")
        else:
            print("   ⚠️  No record to clean up.\n")
    finally:
        db.close()

    # --- Result ---
    print(SEPARATOR)
    if test_passed:
        print("🎉 TEST PASSED: Database insert + read-back verified!")
    else:
        print("💥 TEST FAILED: Record was not persisted.")
    print(SEPARATOR)


if __name__ == "__main__":
    run_test()

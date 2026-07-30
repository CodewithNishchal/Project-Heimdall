import json
import httpx
import asyncio
from backend.database import SessionLocal
from backend.models import LeadSnapshot

async def test_fetch_backend_leads():
    print("=" * 80)
    print("🚀 FETCHING BACKEND LEADS & SIGNALS DATA TEST")
    print("=" * 80)

    # 1. Directly fetch from SQLite Database
    db = SessionLocal()
    try:
        db_leads = db.query(LeadSnapshot).all()
        print(f"--> Found {len(db_leads)} leads stored in SQLite database.\n")

        db_output = []
        for l in db_leads:
            payload = l.full_payload or {}
            db_output.append({
                "id": l.id,
                "company_name": l.company_name,
                "domain": l.domain,
                "score": l.intent_score,
                "funding_stage": l.funding_stage,
                "why_now": l.why_now,
                "ai_verdict": l.ai_verdict,
                "signals_count": len(payload.get("signals", [])),
                "signals": payload.get("signals", []),
                "signal_tags": payload.get("signal_tags", []),
                "social_segment": l.social_segment,
                "contacts": payload.get("contacts", [])
            })

        db_file = "backend/db_leads_output.json"
        with open(db_file, "w", encoding="utf-8") as f:
            json.dump(db_output, f, indent=2, ensure_ascii=False)
        print(f"✅ DB leads context saved to '{db_file}'")

    finally:
        db.close()

    # 2. Fetch from running FastAPI endpoint GET http://127.0.0.1:8000/api/leads/
    url = "http://127.0.0.1:8000/api/leads/"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                leads_data = resp.json()
                print(f"\n--> Successfully queried GET /api/leads/ ({len(leads_data)} leads returned)\n")

                print("=" * 80)
                print("📊 BACKEND LEADS SIGNALS SUMMARY")
                print("=" * 80)
                print(f"{'COMPANY':<25} | {'SCORE':<5} | {'SIGNALS COUNT':<14} | {'TOP SIGNAL VERBATIM QUOTE'}")
                print("-" * 100)

                for item in leads_data:
                    comp = item.get("company_name", "Unknown")[:24]
                    score = item.get("intent_score", 0)
                    signals = item.get("signals", [])
                    top_quote = signals[0].get("verbatim_quote", "")[:50] if signals else "No signals attached"
                    print(f"{comp:<25} | {score:<5} | {len(signals):<14} | {top_quote}")

                api_file = "backend/api_leads_output.json"
                with open(api_file, "w", encoding="utf-8") as f:
                    json.dump(leads_data, f, indent=2, ensure_ascii=False)
                print(f"\n✅ API response saved to '{api_file}'")
            else:
                print(f"❌ API returned status code: {resp.status_code}")

    except Exception as e:
        print(f"⚠️ Note: Backend API HTTP call skipped or failed ({e}). Check local DB output file.")

if __name__ == "__main__":
    asyncio.run(test_fetch_backend_leads())

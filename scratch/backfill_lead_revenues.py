import asyncio
import os
import sys
import json
import httpx
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join("backend", ".env"), override=True)

from backend.database import SessionLocal
from backend.models import LeadSnapshot
from backend.pipeline.streaming_orchestrator import extract_revenue_from_exa_text

EXA_API_KEY = os.getenv("EXA_API_KEY")

async def backfill_revenue_for_leads():
    db = SessionLocal()
    try:
        leads = db.query(LeadSnapshot).all()
        print(f"📋 Found {len(leads)} total lead snapshots in database.\n")

        async with httpx.AsyncClient(timeout=25.0) as client:
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "x-api-key": EXA_API_KEY
            } if EXA_API_KEY else {}

            for lead in leads:
                print(f"🏢 Checking {lead.company_name} ({lead.domain}). Current Revenue: {lead.annual_revenue or 'N/A'}")

                extracted_rev = None
                full_payload = lead.full_payload if isinstance(lead.full_payload, dict) else {}

                # 1. Check if annual_revenue already in full_payload
                if full_payload.get("annual_revenue"):
                    extracted_rev = full_payload.get("annual_revenue")

                # 2. Extract from existing full_payload raw text or signals
                if not extracted_rev:
                    raw_text = json.dumps(full_payload)
                    extracted_rev = extract_revenue_from_exa_text(raw_text)

                # 3. If still missing and EXA_API_KEY is available, fetch live from Exa AI
                if (not extracted_rev or extracted_rev == "N/A") and EXA_API_KEY:
                    print(f"  🔍 Fetching live revenue from Exa AI for {lead.company_name}...")
                    signal_payload = {
                        "query": f"{lead.company_name} {lead.domain or ''} annual revenue ARR valuation financial estimates",
                        "type": "deep",
                        "numResults": 3,
                        "contents": {"text": True, "summary": True},
                        "outputSchema": {
                            "type": "object",
                            "properties": {
                                "annual_revenue": {"type": "string"},
                                "arr_estimate": {"type": "string"}
                            }
                        }
                    }
                    try:
                        res = await client.post("https://api.exa.ai/search", json=signal_payload, headers=headers)
                        if res.status_code == 200:
                            data = res.json()
                            combined_text = ""
                            for item in data.get("results", []):
                                combined_text += f"{item.get('summary', '')}\n{item.get('text', '')}\n"
                            extracted_rev = extract_revenue_from_exa_text(combined_text, structured_out=data.get("output"))
                    except Exception as e:
                        print(f"  ⚠️ Exa live fetch error: {e}")

                if extracted_rev and extracted_rev != "N/A":
                    lead.annual_revenue = extracted_rev
                    if isinstance(lead.full_payload, dict):
                        lead.full_payload["annual_revenue"] = extracted_rev
                    print(f"  ✅ Updated Revenue for {lead.company_name}: {extracted_rev}\n")
                else:
                    print(f"  ℹ️ No revenue data found for {lead.company_name}\n")

        db.commit()
        print("🎉 Database revenue backfill complete!")

    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(backfill_revenue_for_leads())

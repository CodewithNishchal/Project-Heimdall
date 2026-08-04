import asyncio
import json
import os
import sys
import logging
import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestExaCurrentPrompt")

EXA_API_KEY = os.getenv("EXA_API_KEY")

async def test_exa_current_prompt(company_name: str = "Teliolabs Communications", domain: str = "teliolabs.com"):
    print("\n" + "=" * 75)
    print(f"🚀 TESTING EXA CURRENT PIPELINE PROMPT")
    print(f"Target Company : {company_name}")
    print(f"Target Domain  : {domain}")
    print("=" * 75 + "\n")

    if not EXA_API_KEY:
        print("❌ ERROR: EXA_API_KEY is missing from backend/.env!")
        return

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": EXA_API_KEY
    }

    # 1. Canonical Identity Call (Self-reported site facts)
    identity_payload = {
        "query": f"{company_name} company profile leadership services products",
        "type": "neural",
        "category": "company",
        "numResults": 2,
        "includeDomains": [domain] if domain else [],
        "contents": {"text": True, "summary": True}
    }

    # 2. Deep Fresh Signal Call (Structured extraction + maxAgeHours)
    company_schema = {
        "type": "object",
        "properties": {
            "headcount": {"type": "string"},
            "industry": {"type": "string"},
            "funding_stage": {"type": "string"},
            "funding_amount": {"type": "string"},
            "funding_date": {"type": "string"},
            "arr_estimate": {"type": "string"},
            "open_roles_count": {"type": "string"},
            "recent_hiring_signal": {"type": "string"}
        },
        "required": ["headcount", "industry"]
    }

    signal_payload = {
        "query": f"{company_name} recent funding valuation hiring open roles growth press release news",
        "type": "deep",
        "maxAgeHours": 168,
        "numResults": 3,
        "excludeDomains": ["clutch.co", "upcity.com", "designrush.com", "goodfirms.co"],
        "contents": {"text": True, "summary": True},
        "outputSchema": company_schema
    }

    print("📡 Call 1 Payload (Canonical Identity):")
    print(json.dumps(identity_payload, indent=2))
    print("\n📡 Call 2 Payload (Deep Signal + outputSchema + maxAgeHours):")
    print(json.dumps(signal_payload, indent=2) + "\n")

    async with httpx.AsyncClient(timeout=45.0) as client:
        try:
            print("1️⃣ Executing Canonical Identity Call...")
            res1 = await client.post("https://api.exa.ai/search", json=identity_payload, headers=headers)
            identity_results = res1.json().get("results", []) if res1.status_code == 200 else []
            print(f"   ✅ Received {len(identity_results)} canonical identity sources.")

            print("2️⃣ Executing Deep Signal Call (outputSchema)...")
            res2 = await client.post("https://api.exa.ai/search", json=signal_payload, headers=headers)
            if res2.status_code != 200:
                signal_payload["output_schema"] = signal_payload.pop("outputSchema", company_schema)
                res2 = await client.post("https://api.exa.ai/search", json=signal_payload, headers=headers)

            data2 = res2.json() if res2.status_code == 200 else {}
            signal_results = data2.get("results", [])
            structured_out = data2.get("output", {})
            print(f"   ✅ Received {len(signal_results)} deep signal sources.")
            if structured_out:
                print(f"   ✨ Exa Native Structured Schema Output:\n{json.dumps(structured_out, indent=4)}\n")

            out_path = os.path.join(os.path.dirname(__file__), "test_exa_current_prompt_output.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump({
                    "company_name": company_name,
                    "canonical_results": identity_results,
                    "deep_signal_results": signal_results,
                    "native_exa_structured_extraction": structured_out
                }, f, indent=2)
            print(f"💾 Saved full results to: {out_path}")
        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_exa_current_prompt())

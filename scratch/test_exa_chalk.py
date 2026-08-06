import asyncio
import json
import os
import sys
import httpx
from dotenv import load_dotenv

# Load env variables from backend/.env
backend_env = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")
load_dotenv(backend_env)

# Import extract_revenue_from_exa_text from streaming_orchestrator
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.pipeline.streaming_orchestrator import extract_revenue_from_exa_text

EXA_API_KEY = os.getenv("EXA_API_KEY")

async def test_exa_for_chalk():
    company_name = "Chalk"
    domain = "chalk.ai"

    print(f"🔍 Testing Exa AI API for: {company_name} ({domain})")
    if not EXA_API_KEY:
        print("❌ Error: EXA_API_KEY is not set in backend/.env!")
        return

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": EXA_API_KEY
    }

    # 1. Canonical Identity Call
    identity_payload = {
        "query": f"{company_name} company profile leadership services products annual revenue ARR",
        "type": "neural",
        "category": "company",
        "numResults": 3,
        "includeDomains": [domain],
        "contents": {"text": True, "summary": True}
    }

    # 2. Deep Fresh Signals & Financials Call
    company_schema = {
        "type": "object",
        "properties": {
            "headcount": {"type": "string"},
            "industry": {"type": "string"},
            "funding_stage": {"type": "string"},
            "funding_amount": {"type": "string"},
            "annual_revenue": {"type": "string"},
            "arr_estimate": {"type": "string"},
            "open_roles_count": {"type": "string"}
        }
    }

    signal_payload = {
        "query": f"{company_name} chalk.ai funding ARR annual revenue valuation hiring open roles expansion",
        "type": "deep",
        "numResults": 5,
        "contents": {"text": True, "summary": True},
        "outputSchema": company_schema
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        print("\n📡 1. Executing Canonical Identity Search...")
        res1 = await client.post("https://api.exa.ai/search", json=identity_payload, headers=headers)
        data1 = res1.json() if res1.status_code == 200 else {}
        print(f"Status Code: {res1.status_code}")

        print("\n📡 2. Executing Deep Financials & Signals Search...")
        res2 = await client.post("https://api.exa.ai/search", json=signal_payload, headers=headers)
        data2 = res2.json() if res2.status_code == 200 else {}
        print(f"Status Code: {res2.status_code}")

        combined_text = ""
        results_summary = []

        # Parse Call 1
        for idx, item in enumerate(data1.get("results", []), 1):
            title = item.get("title", "")
            url = item.get("url", "")
            summary = item.get("summary", "")
            snippet = item.get("text", "")
            combined_text += f"\n--- CANONICAL [{idx}]: {title} ({url}) ---\n"
            if summary:
                combined_text += f"SUMMARY: {summary}\n"
            if snippet:
                combined_text += f"TEXT: {snippet[:600]}\n"

            results_summary.append({
                "source": "Canonical",
                "title": title,
                "url": url,
                "summary": summary
            })

        # Parse Call 2
        for idx, item in enumerate(data2.get("results", []), 1):
            title = item.get("title", "")
            url = item.get("url", "")
            summary = item.get("summary", "")
            snippet = item.get("text", "")
            combined_text += f"\n--- DEEP SIGNAL [{idx}]: {title} ({url}) ---\n"
            if summary:
                combined_text += f"SUMMARY: {summary}\n"
            if snippet:
                combined_text += f"TEXT: {snippet[:600]}\n"

            results_summary.append({
                "source": "Deep Signal",
                "title": title,
                "url": url,
                "summary": summary
            })

        structured_out = data2.get("output")
        if structured_out:
            print("\n📊 Exa Structured Output:")
            print(json.dumps(structured_out, indent=2))
            combined_text += f"\n--- EXA STRUCTURED OUTPUT ---\n{json.dumps(structured_out)}\n"

        # Revenue Extraction Test
        extracted_rev = extract_revenue_from_exa_text(combined_text, structured_out=structured_out)

        print("\n========================================================")
        print("🎯 REVENUE EXTRACTION RESULT FOR CHALK.AI")
        print("========================================================")
        print(f"Extracted Annual Revenue / ARR: {extracted_rev or 'N/A'}")
        print("========================================================\n")

        print("📝 Combined Raw Snippets Preview:")
        print(combined_text[:1500])

if __name__ == "__main__":
    asyncio.run(test_exa_for_chalk())

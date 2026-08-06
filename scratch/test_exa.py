import os
import json
import asyncio
import httpx
from dotenv import load_dotenv

# Load environment variables from backend/.env
load_dotenv("backend/.env")

EXA_API_KEY = os.getenv("EXA_API_KEY")

async def test_exa_search():
    if not EXA_API_KEY:
        print("ERROR: EXA_API_KEY not found in backend/.env")
        return

    url = "https://api.exa.ai/search"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": EXA_API_KEY
    }

    company_name = "Modal"
    domain = "modal.com"

    # -----------------------------------------------------------------
    # EXA AI: EXACT 2-CALL ARCHITECTURE FROM LIVE ENRICHMENT ENGINE
    # -----------------------------------------------------------------

    # 1. Canonical Identity Call (Self-reported site facts + LinkedIn company ID / URL)
    identity_payload = {
        "query": f"{company_name} company profile leadership services products LinkedIn company ID profile URL",
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

    print(f"======================================================================")
    print(f"🚀 EXA AI TEST: 2-CALL ENRICHMENT ARCHITECTURE FOR '{company_name}' ({domain})")
    print(f"======================================================================\n")

    results_output = {
        "company_name": company_name,
        "domain": domain,
        "canonical_identity_results": [],
        "deep_signals_results": []
    }

    async with httpx.AsyncClient(timeout=35.0) as client:
        # Call 1: Canonical Identity
        print("🔹 CALL 1: Canonical Identity (Neural Search)...")
        res1 = await client.post(url, headers=headers, json=identity_payload)
        print(f"   HTTP Status: {res1.status_code}")
        if res1.status_code == 200:
            items1 = res1.json().get("results", [])
            print(f"   Received {len(items1)} canonical identity items")
            for idx, item in enumerate(items1, start=1):
                res_obj = {
                    "result_num": idx,
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "published_date": item.get("publishedDate"),
                    "summary": item.get("summary"),
                    "text_snippet_preview": item.get("text", "")[:300] + "..." if item.get("text") else ""
                }
                results_output["canonical_identity_results"].append(res_obj)
                print(f"   [{idx}] {res_obj['title']} | {res_obj['url']}")
        else:
            print(f"   ❌ Error Call 1: {res1.text[:200]}")

        # Call 2: Deep Signals
        print("\n🔹 CALL 2: Deep Fresh Signals (Past 7 Days + Output Schema)...")
        res2 = await client.post(url, headers=headers, json=signal_payload)
        if res2.status_code != 200:
            # Fallback for schema parameter naming
            signal_payload["output_schema"] = signal_payload.pop("outputSchema", company_schema)
            res2 = await client.post(url, headers=headers, json=signal_payload)

        print(f"   HTTP Status: {res2.status_code}")
        if res2.status_code == 200:
            items2 = res2.json().get("results", [])
            print(f"   Received {len(items2)} deep signal items")
            for idx, item in enumerate(items2, start=1):
                res_obj = {
                    "result_num": idx,
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "published_date": item.get("publishedDate"),
                    "summary": item.get("summary"),
                    "text_snippet_preview": item.get("text", "")[:300] + "..." if item.get("text") else ""
                }
                results_output["deep_signals_results"].append(res_obj)
                print(f"   [{idx}] {res_obj['title']} | {res_obj['url']}")
        else:
            print(f"   ❌ Error Call 2: {res2.text[:200]}")

    # Save output to scratch directory
    os.makedirs("scratch", exist_ok=True)
    output_file = "scratch/exa_test_output.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results_output, f, indent=2)

    print(f"\n======================================================================")
    print(f"💾 SAVED FULL 2-CALL TEST OUTPUT TO: '{output_file}'")
    print(f"======================================================================\n")

if __name__ == "__main__":
    asyncio.run(test_exa_search())

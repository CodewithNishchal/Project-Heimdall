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
logger = logging.getLogger("TestExaStructured")

EXA_API_KEY = os.getenv("EXA_API_KEY")

async def test_exa_structured_enrichment(company_name: str = "Teliolabs Communications", target_domain: str = "teliolabs.com"):
    print("\n" + "=" * 75)
    print(f"🚀 EXA AI STRUCTURED & DEEP ENRICHMENT TEST")
    print(f"Target Company : {company_name}")
    print(f"Target Domain  : {target_domain}")
    print("=" * 75 + "\n")

    if not EXA_API_KEY:
        print("❌ ERROR: EXA_API_KEY is missing from backend/.env!")
        return

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": EXA_API_KEY
    }

    url = "https://api.exa.ai/search"

    # Flat schema (max 10 properties) for structured extraction
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

    # ----------------------------------------------------------------------
    # CALL 1: Canonical Self-Reported Identity (Domain-Restricted)
    # Low-latency, cached snapshot allowed (no tight maxAgeHours)
    # Clean query without "2025 2026" or "site:" keyword hacks
    # ----------------------------------------------------------------------
    identity_payload = {
        "query": f"{company_name} company profile leadership services telecom digital transformation",
        "type": "neural",
        "category": "company",
        "numResults": 3,
        "includeDomains": [target_domain],
        "contents": {
            "text": True,
            "summary": True
        }
    }

    # ----------------------------------------------------------------------
    # CALL 2: Deep Signal & Third-Party Validation (Open-Web)
    # type: "deep" + maxAgeHours: 168 (1 week freshness)
    # Structured extraction with outputSchema
    # Clean query without "2025 2026" noise tokens
    # ----------------------------------------------------------------------
    signal_payload = {
        "query": f"{company_name} recent funding valuation hiring open roles growth press release news",
        "type": "deep",
        "maxAgeHours": 168,  # Weekly freshness window
        "numResults": 5,
        "excludeDomains": ["clutch.co", "upcity.com", "designrush.com", "goodfirms.co", "byethost7.com", "zya.me"],
        "contents": {
            "text": True,
            "summary": True,
            "extras": {
                "links": 3
            }
        },
        "outputSchema": company_schema
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        # 1. Canonical Identity Request
        print(f"1️⃣  Executing Canonical Self-Reported Identity Call (`includeDomains: ['{target_domain}']`)...")
        try:
            res1 = await client.post(url, json=identity_payload, headers=headers)
            if res1.status_code == 200:
                identity_results = res1.json().get("results", [])
                print(f"   ✅ Received {len(identity_results)} canonical identity sources.")
            else:
                print(f"   ⚠️ Identity call returned status {res1.status_code}: {res1.text[:200]}")
                identity_results = []
        except Exception as e:
            print(f"   ❌ Identity request error: {e}")
            identity_results = []

        # 2. Deep Fresh Signal Request
        print(f"\n2️⃣  Executing Deep Fresh Signal Call (`type: 'deep'`, `maxAgeHours: 168`, `outputSchema`)...")
        try:
            res2 = await client.post(url, json=signal_payload, headers=headers)
            if res2.status_code == 200:
                data2 = res2.json()
                signal_results = data2.get("results", [])
                output_grounding = data2.get("output", {})
                print(f"   ✅ Received {len(signal_results)} deep signal sources.")
                if output_grounding:
                    print(f"   ✨ Exa Native Structured Schema Output:\n{json.dumps(output_grounding, indent=4)}")
            else:
                print(f"   ⚠️ Signal call returned status {res2.status_code}: {res2.text[:200]}")
                # Fallback without outputSchema if payload format requires lower-level schema wrapping
                print("   🔄 Testing alternative schema field key ('output_schema')...")
                fallback_signal = dict(signal_payload)
                fallback_signal["output_schema"] = fallback_signal.pop("outputSchema")
                res2_fb = await client.post(url, json=fallback_signal, headers=headers)
                if res2_fb.status_code == 200:
                    data2 = res2_fb.json()
                    signal_results = data2.get("results", [])
                    output_grounding = data2.get("output", {})
                    print(f"   ✅ Fallback succeeded! Received {len(signal_results)} signal sources.")
                    if output_grounding:
                        print(f"   ✨ Exa Native Structured Schema Output:\n{json.dumps(output_grounding, indent=4)}")
                else:
                    print(f"   ❌ Fallback signal status {res2_fb.status_code}: {res2_fb.text[:200]}")
                    signal_results = []
                    output_grounding = {}
        except Exception as e:
            print(f"   ❌ Deep signal request error: {e}")
            signal_results = []
            output_grounding = {}

    # Deduplicate & Aggregate Results
    combined_sources = []
    seen_urls = set()

    for item in identity_results + signal_results:
        u = item.get("url")
        if u and u not in seen_urls:
            seen_urls.add(u)
            combined_sources.append({
                "title": item.get("title", "No Title"),
                "url": item.get("url", ""),
                "published_date": item.get("publishedDate"),
                "summary": item.get("summary", ""),
                "text_snippet": item.get("text", "")[:400] if item.get("text") else None,
                "structured_output": item.get("output")
            })

    output_payload = {
        "company_name": company_name,
        "domain": target_domain,
        "pipeline_metadata": {
            "canonical_identity_results": len(identity_results),
            "deep_signal_results": len(signal_results),
            "total_unique_sources": len(combined_sources)
        },
        "native_exa_structured_extraction": output_grounding,
        "harvested_sources": combined_sources
    }

    print("\n" + "=" * 75)
    print(f"📊 SUMMARY OF HARVESTED SOURCES ({len(combined_sources)} Sources Total)")
    print("=" * 75)
    for i, s in enumerate(combined_sources, 1):
        print(f"[{i}] {s['title']}")
        print(f"    URL           : {s['url']}")
        print(f"    Published Date: {s['published_date']}")
        print(f"    Summary       : {(s['summary'] or '')[:250]}...")
        print("-" * 75)

    clean_domain = target_domain.replace(".", "_")
    out_file = os.path.join(os.path.dirname(__file__), f"test_exa_structured_{clean_domain}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Structured Exa results saved to: {out_file}\n")

async def main():
    company_name = sys.argv[1] if len(sys.argv) > 1 else "Teliolabs Communications"
    domain = sys.argv[2] if len(sys.argv) > 2 else "teliolabs.com"
    await test_exa_structured_enrichment(company_name, domain)

if __name__ == "__main__":
    asyncio.run(main())

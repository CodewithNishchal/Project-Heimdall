import os
import json
import logging
import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestExaNewsFetch")

EXA_API_KEY = os.getenv("EXA_API_KEY")

# Flat schema (max 10 properties) for structured extraction
COMPANY_FACTS_SCHEMA = {
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

def fetch_company_and_news(company_name: str = "Teliolabs Communications", domain: str = "teliolabs.com"):
    """
    Executes an optimized dual-search Exa AI retrieval:
    1. Canonical Self-Reported Identity Call (Domain-restricted, cached snapshot allowed, no year-keyword hack)
    2. Fresh Signals & Third-Party Validation Call (Open-web, type="deep", maxAgeHours=168, schema-structured extraction)
    """
    if not EXA_API_KEY:
        logger.error("EXA_API_KEY is missing in backend/.env!")
        return None

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": EXA_API_KEY
    }

    url = "https://api.exa.ai/search"

    # Call 1: Canonical Self-Reported Identity (includeDomains=[domain], cached snapshot ok)
    identity_payload = {
        "query": f"{company_name} company profile overview leadership telecom digital transformation",
        "type": "neural",
        "category": "company",
        "numResults": 3,
        "includeDomains": [domain],
        "contents": {
            "text": True,
            "summary": True
        }
    }

    # Call 2: Fresh Signals & Open-Web Third-Party Validation (type="deep", maxAgeHours=168, outputSchema)
    signal_payload = {
        "query": f"{company_name} recent funding valuation hiring open roles ARR growth news press release",
        "type": "deep",
        "maxAgeHours": 168,  # 7-day freshness window for signal rotation
        "numResults": 5,
        "excludeDomains": ["clutch.co", "upcity.com", "designrush.com", "goodfirms.co", "byethost7.com", "zya.me"],
        "contents": {
            "text": True,
            "summary": True
        },
        "outputSchema": COMPANY_FACTS_SCHEMA
    }

    logger.info(f"🔎 [1/2] Executing Canonical Identity Search for '{company_name}' ({domain})...")
    
    with httpx.Client(timeout=45.0) as client:
        # Search 1: Canonical Identity
        res1 = client.post(url, json=identity_payload, headers=headers)
        res1.raise_for_status()
        company_results = res1.json().get("results", [])

        # Search 2: Deep Fresh Signals with Schema Extraction
        logger.info(f"📰 [2/2] Executing Deep Fresh Signal Search for '{company_name}' (type='deep', maxAgeHours=168)...")
        res2 = client.post(url, json=signal_payload, headers=headers)
        
        output_structured = {}
        if res2.status_code == 200:
            data2 = res2.json()
            news_results = data2.get("results", [])
            output_structured = data2.get("output", {})
        else:
            # Fallback if alternative schema key is required by endpoint version
            signal_payload_fb = dict(signal_payload)
            signal_payload_fb["output_schema"] = signal_payload_fb.pop("outputSchema")
            res2_fb = client.post(url, json=signal_payload_fb, headers=headers)
            res2_fb.raise_for_status()
            data2 = res2_fb.json()
            news_results = data2.get("results", [])
            output_structured = data2.get("output", {})

    harvested_sources = []
    combined_text = ""

    # Aggregate Canonical Company Profile Results
    for item in company_results:
        source_obj = {
            "source_type": "CANONICAL_IDENTITY",
            "title": item.get("title", "No Title"),
            "url": item.get("url", ""),
            "published_date": item.get("publishedDate"),
            "summary": item.get("summary", ""),
            "text_snippet": item.get("text", "")[:400] if item.get("text") else None
        }
        harvested_sources.append(source_obj)
        combined_text += f"\n--- CANONICAL IDENTITY: {source_obj['title']} ({source_obj['url']}) ---\nSUMMARY: {source_obj['summary']}\n"

    # Aggregate Deep Third-Party Signal Results
    for item in news_results:
        source_obj = {
            "source_type": "THIRD_PARTY_SIGNAL",
            "title": item.get("title", "No Title"),
            "url": item.get("url", ""),
            "published_date": item.get("publishedDate"),
            "summary": item.get("summary", ""),
            "text_snippet": item.get("text", "")[:400] if item.get("text") else None
        }
        harvested_sources.append(source_obj)
        combined_text += f"\n--- THIRD PARTY SIGNAL: {source_obj['title']} ({source_obj['url']}) Date: {source_obj['published_date']}\nSUMMARY: {source_obj['summary']}\n"

    audit_output = {
        "metadata": {
            "company_name": company_name,
            "domain": domain,
            "total_canonical_identity_results": len(company_results),
            "total_third_party_signal_results": len(news_results),
            "total_harvested_sources": len(harvested_sources)
        },
        "native_exa_structured_facts": output_structured,
        "harvested_sources": harvested_sources,
        "combined_evidence_preview": combined_text[:3000]
    }

    out_file = os.path.join(os.path.dirname(__file__), f"test_exa_news_results_{domain.replace('.', '_')}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(audit_output, f, indent=2, ensure_ascii=False)

    logger.info(f"✅ SUCCESS! Harvested {len(company_results)} canonical identity profiles & {len(news_results)} deep signal sources.")
    logger.info(f"📁 Audit saved to: {out_file}")

    return audit_output

if __name__ == "__main__":
    fetch_company_and_news("Teliolabs Communications", "teliolabs.com")

"""
Standalone test runner for testing the new Exa AI multi-query discovery for 3 niches:
- Recruitment Agency Clients (6 queries x 25 = ~150 candidates)
- Marketing Agency Clients (3 queries x 25 = ~75 candidates)
- Appointment Setting Clients (3 queries x 25 = ~75 candidates)
"""

import os
import sys
import json
import time
import asyncio
import logging
import httpx
from dotenv import dotenv_values

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TestNewExaQueries")

# ---------------------------------------------------------------------------
# Target 3 Niche Exa AI Queries Definition
# ---------------------------------------------------------------------------
NEW_EXA_QUERIES = {
    "recruitment": [
        {
            "label": "High-growth companies hiring heavily",
            "query": "companies rapidly scaling team hiring multiple roles engineering sales growing headcount 2025 2026",
            "category": "company",
            "numResults": 25
        },
        {
            "label": "Companies with recruiting pain",
            "query": "company struggling to hire talent shortage time to fill roles open months scaling team challenges",
            "category": "company",
            "numResults": 25
        },
        {
            "label": "Recently funded companies about to scale",
            "query": "startup raised series A series B seed funding hiring plan team expansion 2025 2026",
            "category": "company",
            "numResults": 25
        },
        {
            "label": "Federal contract wins (urgent hiring need)",
            "query": "company awarded federal contract government agency deal prime contract subcontract defense civilian 2025 2026",
            "category": "company",
            "numResults": 25
        },
        {
            "label": "New VP/leadership hires (immediate hiring trigger)",
            "query": "company announces new vp joins appointed vp sales vp engineering vp marketing leadership hire welcomes 2025 2026",
            "category": "company",
            "numResults": 25
        },
        {
            "label": "M&A / Acquisitions (integration hiring wave)",
            "query": "company acquired acquisition merger combines teams post-merger integration restructuring 2025 2026",
            "category": "company",
            "numResults": 25
        }
    ],
    "marketing": [
        {
            "label": "Companies investing in growth without marketing team",
            "query": "company growing revenue expanding market no CMO no marketing director hiring sales but not marketing 2025 2026",
            "category": "company",
            "numResults": 25
        },
        {
            "label": "Companies with marketing pain signals",
            "query": "company struggling with customer acquisition CAC rising paid ads not working SEO declining need marketing help",
            "category": "company",
            "numResults": 25
        },
        {
            "label": "Funded companies entering growth phase",
            "query": "startup raised funding go-to-market strategy brand launch product-market fit growth phase 2025 2026",
            "category": "company",
            "numResults": 25
        }
    ],
    "appointment_setting": [
        {
            "label": "Companies building sales without SDR team",
            "query": "B2B company growing revenue founder-led sales no SDR team need more meetings pipeline 2025 2026",
            "category": "company",
            "numResults": 25
        },
        {
            "label": "Companies with outbound pain",
            "query": "company outbound sales not working cold email low response pipeline dry need more demos qualified leads",
            "category": "company",
            "numResults": 25
        },
        {
            "label": "Funded B2B companies ready to scale outbound",
            "query": "B2B SaaS startup raised funding hiring AE account executive need pipeline outbound scaling sales 2025 2026",
            "category": "company",
            "numResults": 25
        }
    ]
}

# Seller Filter (Agency Guard) Exclusion Terms Per Niche
EXCLUDE_TERMS_PER_NICHE = {
    "recruitment": ["staffing", "recruiting", "recruitment agency", "headhunter", "rpo", "talent acquisition firm"],
    "marketing": ["marketing agency", "digital agency", "seo agency", "ad agency", "media agency"],
    "appointment_setting": ["sdr agency", "lead gen agency", "appointment setting company", "cold email agency", "bdr agency"]
}


async def execute_exa_query(client: httpx.AsyncClient, query_obj: dict, api_key: str) -> list[dict]:
    """Sends a single neural search request to Exa AI API."""
    url = "https://api.exa.ai/search"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": api_key
    }
    payload = {
        "query": query_obj.get("query"),
        "type": "neural",
        "useAutoprompt": False,
        "category": "company",
        "excludeDomains": [
            "clutch.co", "upcity.com", "designrush.com", "goodfirms.co", 
            "linkedin.com", "crunchbase.com", "g2.com", "capterra.com"
        ],
        "numResults": query_obj.get("numResults", 25),
        "contents": {
            "text": True,
            "summary": True
        }
    }
    try:
        resp = await client.post(url, headers=headers, json=payload, timeout=30.0)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            for r in results:
                r["_query_label"] = query_obj.get("label")
            return results
        else:
            logger.error(f"Exa HTTP {resp.status_code} for query '{query_obj.get('label')}': {resp.text[:150]}")
            return []
    except Exception as e:
        logger.error(f"Exa error for query '{query_obj.get('label')}': {e}")
        return []


def apply_agency_guard_filter(candidates: list[dict], niche_name: str) -> tuple[list[dict], list[dict]]:
    """Applies Rule 1 Seller Filter (Agency Guard) to discard competitor service providers."""
    exclude_terms = EXCLUDE_TERMS_PER_NICHE.get(niche_name, [])
    survivors = []
    rejected = []

    for item in candidates:
        title = (item.get("title") or item.get("company_name") or "").lower()
        summary = (item.get("summary") or item.get("text") or "").lower()

        is_seller = any(term in title or term in summary for term in exclude_terms)
        if is_seller:
            rejected.append({
                "company_name": item.get("title"),
                "reason": f"Seller Filter (Agency Guard): matched competitor term in '{niche_name}' space"
            })
        else:
            survivors.append(item)

    return survivors, rejected


async def test_niche_exa_queries(niche_name: str, exa_api_key: str):
    print("=" * 80)
    print(f"🚀 TESTING EXA AI QUERIES FOR NICHE: '{niche_name.upper()}'")
    print("=" * 80)

    queries = NEW_EXA_QUERIES.get(niche_name, [])
    print(f"📋 Executing {len(queries)} parallel Exa queries (25 results each = ~{len(queries)*25} raw candidates max)...")
    for idx, q in enumerate(queries, 1):
        print(f"   [{idx}] {q['label']}")
        print(f"       Query: \"{q['query']}\"")

    start_time = time.time()
    async with httpx.AsyncClient() as client:
        tasks = [execute_exa_query(client, q, exa_api_key) for q in queries]
        batch_results = await asyncio.gather(*tasks)

    elapsed = time.time() - start_time
    total_raw = sum(len(b) for b in batch_results)

    # Deduplicate by URL and Title/Domain
    seen_urls = set()
    deduped = []
    for batch in batch_results:
        for item in batch:
            url = str(item.get("url") or "").lower()
            if url and url not in seen_urls:
                seen_urls.add(url)
                deduped.append(item)
            elif not url and item.get("title") not in seen_urls:
                seen_urls.add(item.get("title"))
                deduped.append(item)

    print(f"\n⚡ Completed in {elapsed:.2f} seconds.")
    print(f"📊 Query Results Summary:")
    print(f"   - Total Raw Hits Fetched:    {total_raw}")
    print(f"   - Deduplicated Candidates:   {len(deduped)}")

    # Apply Seller Filter (Agency Guard)
    survivors, rejected = apply_agency_guard_filter(deduped, niche_name)
    print(f"   - Rejected by Agency Guard:  {len(rejected)}")
    print(f"   - SURVIVORS Ready for Gatekeeper: {len(survivors)}")

    print("\n" + "-" * 80)
    print("📋 SAMPLE SURVIVORS (Top 5 Results):")
    print("-" * 80)
    for idx, c in enumerate(survivors[:5], 1):
        title = c.get("title") or c.get("company_name") or "Unknown"
        url = c.get("url") or "No URL"
        query_label = c.get("_query_label", "General")
        summary = (c.get("summary") or c.get("text") or "")[:140].replace("\n", " ")
        print(f"[{idx}] {title}")
        print(f"    Source Query: {query_label}")
        print(f"    URL:          {url}")
        print(f"    Summary:      {summary}...")
        print()

    return {
        "niche": niche_name,
        "execution_time_sec": round(elapsed, 2),
        "total_raw": total_raw,
        "deduplicated_count": len(deduped),
        "survivors_count": len(survivors),
        "rejected_count": len(rejected),
        "sample_survivors": survivors[:10],
        "sample_rejected": rejected[:5]
    }


async def main():
    env_vars = dotenv_values("backend/.env")
    exa_api_key = env_vars.get("EXA_API_KEY") or os.getenv("EXA_API_KEY")

    if not exa_api_key or "your_" in exa_api_key or exa_api_key == "mock_key_if_empty":
        print("⚠️ EXA_API_KEY missing or invalid in backend/.env. Cannot execute live API tests.")
        print("   Please ensure EXA_API_KEY is set in backend/.env")
        return

    # Test all 3 niches sequentially
    niches_to_test = ["recruitment", "marketing", "appointment_setting"]
    all_results = {}

    for niche in niches_to_test:
        res = await test_niche_exa_queries(niche, exa_api_key)
        all_results[niche] = res
        print("\n")

    output_path = "backend/test_new_exa_queries_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    print("=" * 80)
    print(f"💾 Comprehensive Exa query test results saved to: {output_path}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

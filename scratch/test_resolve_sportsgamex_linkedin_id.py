import os
import sys
import re
import json
import asyncio
import httpx
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join("backend", ".env"), override=True)

from backend.pipeline.linkedin_id_resolver import resolve_linkedin_company_id

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
OUTPUT_FILE = os.path.join("scratch", "sportsgamex_resolution_output.json")

async def search_serper_for_linkedin(query: str):
    if not SERPER_API_KEY:
        print("⚠️ SERPER_API_KEY not configured in backend/.env")
        return []

    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    payload = {"q": query, "num": 10}

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, headers=headers, json=payload, timeout=15.0)
            if resp.status_code == 200:
                results = resp.json().get("organic", [])
                return [r.get("link") for r in results if "linkedin.com/company" in r.get("link", "")]
        except Exception as e:
            print(f"❌ Serper Error for query '{query}': {e}")
    return []

async def test_resolve_sportsgamex():
    print("======================================================================")
    print("🔍 RESOLVING LINKEDIN COMPANY ID FOR: Sports GameX (sportsgamex.com)")
    print("======================================================================\n")

    results_summary = {
        "company_name": "Sports GameX",
        "domain": "sportsgamex.com",
        "slugs_tested": [],
        "serper_urls_found": [],
        "resolved_id": None
    }

    # Step 1: Search Serper API for LinkedIn company pages
    queries = [
        'site:linkedin.com/company "Sports GameX"',
        'site:linkedin.com/company "sportsgamex"',
        'sportsgamex.com linkedin company'
    ]

    found_urls = []
    for q in queries:
        print(f"📡 Querying Serper: '{q}'...")
        urls = await search_serper_for_linkedin(q)
        if urls:
            print(f"   ✅ Found LinkedIn URLs: {urls}")
            found_urls.extend(urls)
        else:
            print("   ℹ️ No direct LinkedIn company URLs found.")

    found_urls = list(set(found_urls))
    results_summary["serper_urls_found"] = found_urls

    # Step 2: Test candidate slugs with linkedin_id_resolver
    candidate_slugs = ["sportsgamex", "sports-gamex", "sportsgamex-com", "sportsgamexcom"]
    for url in found_urls:
        slug = url.rstrip("/").split("/")[-1]
        if slug not in candidate_slugs:
            candidate_slugs.append(slug)

    print(f"\n🔍 Candidate Slugs to Resolve: {candidate_slugs}\n")

    resolved_id = None
    for slug in candidate_slugs:
        print(f"⏳ Attempting resolution for slug: '{slug}'...")
        results_summary["slugs_tested"].append(slug)
        comp_id = await resolve_linkedin_company_id(slug)
        if comp_id:
            print(f"🎉 SUCCESS! Resolved Numeric LinkedIn Company ID: {comp_id} (slug: '{slug}')")
            resolved_id = comp_id
            results_summary["resolved_id"] = comp_id
            results_summary["winning_slug"] = slug
            break
        else:
            print(f"   ❌ Could not resolve ID for '{slug}'")

    if not resolved_id:
        print("\n⚠️ COULD NOT AUTOMATICALLY RESOLVE LINKEDIN ID FOR SPORTS GAMEX.")
        print("   Possible reasons: Company may not have an active public LinkedIn Company Page or uses a distinct trade name.")
    else:
        print(f"\n✅ FINAL RESOLVED LINKEDIN COMPANY ID FOR SPORTS GAMEX: {resolved_id}")

    os.makedirs("scratch", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results_summary, f, indent=2)

    print(f"\n💾 Results saved to: '{OUTPUT_FILE}'\n")

if __name__ == "__main__":
    asyncio.run(test_resolve_sportsgamex())

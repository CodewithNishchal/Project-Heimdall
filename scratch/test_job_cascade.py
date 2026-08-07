"""
Test script: Tests 3-tier Job Fetching Cascade (Apify Career Scraper -> TheirStack -> Serper).
Run: python scratch/test_job_cascade.py
"""
import os
import sys
import asyncio
import logging

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath("."))

from backend.pipeline.streaming_orchestrator import (
    fetch_company_jobs_apify,
    fetch_company_job_theirstack,
    fetch_company_jobs_serper
)

logging.basicConfig(level=logging.INFO)

async def test_cascade():
    test_companies = [
        {"name": "Google", "domain": "careers.google.com", "slug": "google"},
        {"name": "Valence", "domain": "getvalence.com", "slug": "getvalence"}
    ]

    for company in test_companies:
        c_name = company["name"]
        dom = company["domain"]
        slug = company["slug"]

        print("\n" + "=" * 70)
        print(f"🧪 TESTING JOB CASCADE FOR: {c_name} ({dom})")
        print("=" * 70)

        # Step 1: Apify
        print("\n1️⃣ Attempting Primary: Apify Career Scraper...")
        res = await fetch_company_jobs_apify(c_name, dom, slug)
        
        if not res or res.get("total_results", 0) == 0:
            print("   ⚠️ Apify returned 0 jobs or failed. Triggering Fallback 1: TheirStack...")
            res = await fetch_company_job_theirstack(c_name, dom, slug)

        if not res or res.get("total_results", 0) == 0:
            print("   ⚠️ TheirStack returned 0 jobs or failed. Triggering Fallback 2: Serper...")
            res = await fetch_company_jobs_serper(c_name, slug, dom)

        if res and res.get("qualified_jobs"):
            print(f"\n✅ SUCCESS! Source: '{res.get('source')}' | Total Jobs: {len(res['qualified_jobs'])}")
            for j in res["qualified_jobs"][:3]:
                print(f"   • {j.get('title')} ({j.get('location', 'N/A')}) -> {j.get('link')}")
        else:
            print("\n❌ All 3 tiers failed or returned 0 jobs.")

if __name__ == "__main__":
    asyncio.run(test_cascade())

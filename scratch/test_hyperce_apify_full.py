import asyncio
import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.pipeline.linkedin_id_resolver import resolve_linkedin_company_id
from backend.pipeline.streaming_orchestrator import fetch_company_jobs_apify, fetch_linkedin_company_insights

async def main():
    company_name = "Hyperce"
    domain = "hyperce.io"
    company_slug = "hyperce"
    
    print(f"🚀 Running Full Pipeline Test for: {company_name} ({domain})\n")
    
    # 1. Resolve LinkedIn Company ID
    print("--- Step 1: Resolving LinkedIn Company ID ---")
    company_id = await resolve_linkedin_company_id(company_slug)
    print(f"✅ Resolved LinkedIn Company ID: {company_id}\n")
    
    # 2. Test Apify Career Scraper (Jobs)
    print("--- Step 2: Testing Apify Career Scraper (Jobs) ---")
    jobs_result = await fetch_company_jobs_apify(company_name, domain, company_slug)
    if jobs_result:
        print("✅ Apify Career Scraper Succeeded!")
        print(json.dumps(jobs_result, indent=2))
    else:
        print("❌ Apify Career Scraper returned 0 jobs or failed.")
        
    print("\n--------------------------------------------------\n")

    # 3. Test Apify LinkedIn Insights
    print("--- Step 3: Testing Apify LinkedIn Insights ---")
    if not company_id:
        print("⚠️ Skipping LinkedIn Insights (company_id is missing)")
    else:
        insights_result = await fetch_linkedin_company_insights(company_id, company_slug)
        if insights_result:
            print("✅ Apify LinkedIn Insights Succeeded!")
            print(json.dumps(insights_result, indent=2))
        else:
            print("❌ Apify LinkedIn Insights returned None (Check if APIFY_INSIGHTS_API_KEY exceeded monthly limit).")

if __name__ == "__main__":
    asyncio.run(main())

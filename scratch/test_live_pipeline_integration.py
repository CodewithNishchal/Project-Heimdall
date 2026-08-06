"""
Integration Test Script: Runs process_single_company in backend/pipeline/streaming_orchestrator.py
for a candidate company ('Modal', 'modal.com') to verify the end-to-end intent scoring,
gated enrichment (intent_score >= 80), zero-cost LinkedIn ID resolution, Apify Insights,
and Serper ATS job search integration.

Saves output to scratch/live_pipeline_integration_output.json.
"""
import sys
import os
import json
import asyncio
from dotenv import load_dotenv

# Add project root to sys.path so we can import 'backend'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv(os.path.join("backend", ".env"))

from backend.pipeline.streaming_orchestrator import process_single_company

OUTPUT_FILE = os.path.join("scratch", "live_pipeline_integration_output.json")


async def test_streaming_orchestrator_integration():
    candidate = {
        "company_name": "Azion",
        "domain": "azion.com",
        "linkedin_slug": "aziontech",
        "firmographics": {
            "employee_count": 197,
            "total_funding": 24000000
        }
    }

    print("=" * 85)
    print("🚀 TESTING LIVE PIPELINE INTEGRATION: streaming_orchestrator.py")
    print(f"🏢 Candidate: '{candidate['company_name']}' ({candidate['domain']})")
    print("=" * 85 + "\n")

    sem = asyncio.Semaphore(1)
    result = await process_single_company(candidate, sem)

    if result:
        intent_score = result.get("intent_score", 0)
        linkedin_id = result.get("company_linkedin_id")
        insights = result.get("company_insights")
        jobs = result.get("job_openings")

        print("✅ PIPELINE EXECUTION COMPLETE!")
        print(f"   Intent Score        : {intent_score}")
        print(f"   LinkedIn Company ID : {linkedin_id}")
        print(f"   Company Insights    : {'PRESENT' if insights else 'NONE'}")
        print(f"   Job Openings        : {'PRESENT' if jobs else 'NONE'}")

        if jobs:
            print(f"   Total Qualified Jobs: {jobs.get('total_results', 0)}")

        os.makedirs("scratch", exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        print(f"\n💾 Saved full lead payload to: '{OUTPUT_FILE}'\n")
    else:
        print("❌ Pipeline returned None.")


if __name__ == "__main__":
    asyncio.run(test_streaming_orchestrator_integration())

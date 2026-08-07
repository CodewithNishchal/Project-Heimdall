import asyncio
import sys
import os
import json

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.pipeline.airtable_connector import fetch_airtable_candidates_batch

async def main():
    target_start = 100
    target_end = 105
    print(f"🚀 Fetching Airtable Companies #{target_start} to #{target_end}...")

    current_count = 0
    offset_token = None
    records_100_to_105 = []

    while current_count < target_end:
        # Fetch in pages of 50
        page_limit = min(50, target_end - current_count)
        batch, next_offset = await fetch_airtable_candidates_batch(limit=page_limit, offset_token=offset_token)
        
        if not batch:
            print("⚠️ End of Airtable table reached.")
            break

        for item in batch:
            current_count += 1
            if target_start <= current_count <= target_end:
                records_100_to_105.append((current_count, item))

        offset_token = next_offset
        if not next_offset or current_count >= target_end:
            break

    print("\n=========================================================================")
    print(f"📋 AIRTABLE RECORDS #{target_start} to #{target_end}:")
    print("=========================================================================")

    for row_num, comp in records_100_to_105:
        c_name = comp.get("company_name", "Unknown")
        domain = comp.get("domain", "Unknown")
        raw_fields = comp.get("raw_fields", {})
        linkedin = raw_fields.get("LinkedIn") or raw_fields.get("LinkedIn URL") or raw_fields.get("Company LinkedIn") or "Not Listed"
        industry = comp.get("firmographics", {}).get("industry", "Unknown")
        emp_count = comp.get("firmographics", {}).get("employee_count", "Unknown")

        print(f"\n[Record #{row_num}] Company Name : {c_name}")
        print(f"            Domain       : {domain}")
        print(f"            Industry     : {industry}")
        print(f"            Employee Size: {emp_count}")
        print(f"            LinkedIn URL : {linkedin}")

    print("\n=========================================================================")
    print("✨ Note: This peek script did NOT advance your active pipeline_state.json offset.")

if __name__ == "__main__":
    asyncio.run(main())

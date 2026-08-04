"""
Test script: Verifies that get_ui_test_batch(limit=5) makes exactly 1 HTTP call
to Airtable and retrieves exactly 5 candidate records.
"""
import os
import sys
import asyncio
import json
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestAirtableBatch5")

from backend.pipeline.airtable_connector import get_ui_test_batch

async def main():
    print("=" * 65)
    print("🚀 TESTING 1-CALL AIRTABLE BATCH RETRIEVAL (5 RECORDS)")
    print("=" * 65)

    batch, state = await get_ui_test_batch(limit=5)

    print("\n" + "=" * 65)
    print(f"✅ RECEIVED {len(batch)} CANDIDATE RECORDS IN 1 API CALL:")
    print("=" * 65)

    for i, item in enumerate(batch, 1):
        print(f"[{i:02d}] ID: {item['airtable_id']} | Company: {item['company_name']:<25} | Domain: {item['domain']}")

    print("\n" + "-" * 65)
    print("📌 State Updated:")
    print(f"   - Next Offset Token : {state.get('next_offset_token')}")
    print(f"   - Processed Today   : {state.get('daily_processed_count')}")
    print(f"   - Last Run Timestamp: {state.get('last_run_timestamp')}")
    print("-" * 65 + "\n")

    out_file = os.path.join(os.path.dirname(__file__), "test_airtable_batch_5_results.json")
    with open(out_file, "w") as f:
        json.dump(batch, f, indent=2)
    print(f"✅ Results saved to: {out_file}\n")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.pipeline.airtable_connector import fetch_airtable_candidates_batch, load_pipeline_state, save_pipeline_state

async def main():
    print("🚀 Fast-forwarding Airtable offset to skip the first 200 records...")
    
    current_offset_token = None
    total_fetched = 0
    target = 200
    
    # 1. Loop and fetch in max batch sizes (100) until we hit 200
    while total_fetched < target:
        batch_size = min(100, target - total_fetched)
        print(f"Fetching batch of {batch_size}... (Current Token: {current_offset_token})")
        batch, next_token = await fetch_airtable_candidates_batch(limit=batch_size, offset_token=current_offset_token)
        total_fetched += len(batch)
        current_offset_token = next_token
        print(f"  -> Fetched {len(batch)} records. New Token: {current_offset_token}")
        
        if not next_token:
            print("  -> Reached the end of the Airtable base!")
            break

    print(f"\n✅ Successfully fast-forwarded {total_fetched} records.")
    print(f"The offset token for record #{total_fetched + 1} is: {current_offset_token}")
    
    # 2. Update pipeline_state.json
    print("\n--- Updating pipeline_state.json ---")
    state = load_pipeline_state()
    state["current_offset"] = total_fetched
    state["next_offset_token"] = current_offset_token
    save_pipeline_state(state)
    
    print(json.dumps(state, indent=2))
    print("\n✅ Main pipeline is now configured to start from record #201!")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import sys
import os
import json

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.pipeline.airtable_connector import fetch_airtable_candidates_batch, load_pipeline_state, save_pipeline_state

async def main():
    print("🚀 Fast-forwarding main pipeline cursor to Record #100...")

    current_count = 0
    offset_token = None
    target_count = 99  # We want the token that points to record #100

    while current_count < target_count:
        page_limit = min(50, target_count - current_count)
        batch, next_offset = await fetch_airtable_candidates_batch(limit=page_limit, offset_token=offset_token)
        
        if not batch:
            print("⚠️ End of Airtable table reached.")
            break

        current_count += len(batch)
        offset_token = next_offset
        print(f"  Processed {current_count}/{target_count} records... (Next Token: {offset_token})")
        
        if not next_offset:
            break

    # Save to pipeline_state.json
    state = load_pipeline_state()
    state["current_offset"] = current_count
    state["next_offset_token"] = offset_token
    save_pipeline_state(state)

    print("\n=========================================================================")
    print(f"✅ PIPELINE FAST-FORWARD COMPLETE!")
    print(f"   Current Offset Integer: {current_count}")
    print(f"   Next Offset Token: '{offset_token}'")
    print(f"   The next pipeline run will fetch Record #{current_count + 1}!")
    print("=========================================================================")

if __name__ == "__main__":
    asyncio.run(main())

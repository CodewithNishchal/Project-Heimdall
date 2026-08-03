import os
import sys
import json
import logging
import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestAirtableFetch")

# Environment Credentials
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY") # Personal Access Token (pat...)
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID") # Base ID (app...)
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "Companies") # Table Name or ID

async def test_airtable_fetch(batch_size: int = 30):
    print("\n" + "=" * 65)
    print("🚀 HEIMDALL AIRTABLE CANDIDATE RETRIEVAL TESTER")
    print("=" * 65 + "\n")

    if not AIRTABLE_API_KEY or AIRTABLE_API_KEY == "your_airtable_api_key_here":
        print("❌ MISSING CONFIGURATION: AIRTABLE_API_KEY (Personal Access Token) is missing in backend/.env!")
        print_required_credentials_help()
        return

    if not AIRTABLE_BASE_ID or AIRTABLE_BASE_ID == "your_airtable_base_id_here":
        print("❌ MISSING CONFIGURATION: AIRTABLE_BASE_ID (app...) is missing in backend/.env!")
        print_required_credentials_help()
        return

    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Query parameters for batch limit
    params = {
        "pageSize": batch_size
    }

    print(f"Connecting to Airtable Base '{AIRTABLE_BASE_ID}' / Table '{AIRTABLE_TABLE_NAME}'...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            records = data.get("records", [])
            offset_token = data.get("offset")

            print("\n" + "=" * 65)
            print(f"✅ SUCCESSFULLY FETCHED {len(records)} CANDIDATE RECORDS FROM AIRTABLE!")
            print("=" * 65 + "\n")

            candidates = []
            for i, rec in enumerate(records, 1):
                fields = rec.get("fields", {})
                rec_id = rec.get("id")
                
                # Extract potential company name / domain fields dynamically
                company_name = fields.get("Company Name") or fields.get("Company") or fields.get("Name") or "Unknown"
                domain = fields.get("Domain") or fields.get("Website") or fields.get("URL") or "N/A"
                
                candidates.append({
                    "airtable_id": rec_id,
                    "company_name": company_name,
                    "domain": domain,
                    "raw_fields": fields
                })

                print(f"[{i:02d}] Company: {company_name:<25} | Domain: {domain}")

            if offset_token:
                print(f"\n📌 Next Pagination Offset Token: {offset_token}")

            # Save fetched records to JSON file
            out_file = os.path.join(os.path.dirname(__file__), "test_airtable_fetch_results.json")
            with open(out_file, "w") as f:
                json.dump(candidates, f, indent=2)
            print(f"\n✅ Results saved to: {out_file}\n")

        except httpx.HTTPStatusError as err:
            print(f"❌ HTTP Error from Airtable API: {err.response.status_code} - {err.response.text}")
            if err.response.status_code == 404:
                print("   💡 Tip: Verify your AIRTABLE_BASE_ID and AIRTABLE_TABLE_NAME.")
            elif err.response.status_code == 401:
                print("   💡 Tip: Verify your AIRTABLE_API_KEY (Personal Access Token).")
        except Exception as err:
            print(f"❌ Error fetching from Airtable: {err}")

def print_required_credentials_help():
    print("\n" + "-" * 65)
    print("📋 CREDENTIALS NEEDED IN `backend/.env`:")
    print("1. AIRTABLE_API_KEY   : Personal Access Token (starts with 'pat...')")
    print("2. AIRTABLE_BASE_ID   : Base ID (starts with 'app...')")
    print("3. AIRTABLE_TABLE_NAME : Table Name or ID (e.g. 'Companies' or 'tbl...')")
    print("-" * 65 + "\n")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_airtable_fetch(30))

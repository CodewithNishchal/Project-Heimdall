import os
import json
import httpx
import asyncio
from dotenv import dotenv_values, load_dotenv

# Load environment variables
load_dotenv("backend/.env")
env_vars = dotenv_values("backend/.env")

HARVEST_API_KEY = env_vars.get("HARVEST_API_KEY") or env_vars.get("APIFY_API_KEY") or os.getenv("APIFY_API_KEY")
FULLENRICH_API_KEY = env_vars.get("FULLENRICH_API_KEY") or os.getenv("FULLENRICH_API_KEY")

async def test_harvest_api():
    print("\n" + "=" * 80)
    print("🌾 TEST 1: HARVEST API (APIFY LINKEDIN SCRAPER)")
    print("=" * 80)

    if not HARVEST_API_KEY or "your_" in HARVEST_API_KEY:
        print("❌ HARVEST_API_KEY / APIFY_API_KEY not found in backend/.env")
        return

    print(f"--> Using Key: {HARVEST_API_KEY[:10]}...")

    target_company_url = "https://www.linkedin.com/company/greenboard/"
    actor_id = "harvestapi~linkedin-company"
    url = f"https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items?token={HARVEST_API_KEY}"

    payload = {
        "urls": [target_company_url]
    }

    print(f"--> Querying HarvestAPI for company profile: {target_company_url}")
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        try:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Success! HarvestAPI returned {len(data)} company items.\n")
                if data:
                    comp = data[0]
                    summary = {
                        "name": comp.get("name"),
                        "website": comp.get("websiteUrl") or comp.get("website"),
                        "employee_count": comp.get("employeeCount") or comp.get("employeesCount"),
                        "industry": comp.get("industry") or comp.get("industries"),
                        "description": (comp.get("description") or "")[:200] + "..."
                    }
                    print("📊 HarvestAPI Extracted Result:")
                    print(json.dumps(summary, indent=2))

                    with open("backend/harvest_api_test_results.json", "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    print("💾 Full raw payload saved to 'backend/harvest_api_test_results.json'")
            else:
                print(f"⚠️ HarvestAPI HTTP Error Status {resp.status_code}: {resp.text[:300]}")
        except Exception as e:
            print(f"❌ HarvestAPI Execution Error: {e}")


async def test_fullenrich_api():
    print("\n" + "=" * 80)
    print("🔍 TEST 2: FULLENRICH CONTACT ENRICHMENT API (v2 Bulk Endpoint)")
    print("=" * 80)

    if not FULLENRICH_API_KEY or "your_" in FULLENRICH_API_KEY:
        print("⚠️ FULLENRICH_API_KEY is not configured with a valid key in backend/.env")
        print("   To run live tests, replace FULLENRICH_API_KEY=your_key in backend/.env\n")
        print("   Showing FullEnrich v2 API Syntax & Request Payload structure:")
        sample_request = {
            "endpoint": "POST https://app.fullenrich.com/api/v2/contact/enrich/bulk",
            "headers": {
                "Authorization": "Bearer YOUR_FULLENRICH_API_KEY",
                "Content-Type": "application/json"
            },
            "payload": {
                "name": "Heimdall Executive Search",
                "data": [
                    {
                        "first_name": "Dave",
                        "last_name": "Feldman",
                        "domain": "greenboard.com",
                        "company_name": "Greenboard",
                        "enrich_fields": [
                            "contact.work_emails",
                            "contact.personal_emails",
                            "contact.phones"
                        ]
                    }
                ]
            }
        }
        print(json.dumps(sample_request, indent=2))
        return

    print(f"--> Using FullEnrich API Key: {FULLENRICH_API_KEY[:10]}...")

    # FullEnrich v2 Bulk Contact Enrichment Endpoint
    endpoint = "https://app.fullenrich.com/api/v2/contact/enrich/bulk"
    headers = {
        "Authorization": f"Bearer {FULLENRICH_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": "Heimdall Executive Contact Search",
        "data": [
            {
                "first_name": "Dave",
                "last_name": "Feldman",
                "domain": "greenboard.com",
                "company_name": "Greenboard",
                "enrich_fields": [
                    "contact.work_emails",
                    "contact.personal_emails",
                    "contact.phones"
                ]
            }
        ]
    }

    print(f"--> Sending v2 Bulk Enrichment request to FullEnrich for: Dave Feldman @ Greenboard (greenboard.com)")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(endpoint, headers=headers, json=payload)
            if resp.status_code in (200, 201, 202):
                result = resp.json()
                enrichment_id = result.get("enrichment_id")
                print(f"✅ FullEnrich Job Triggered! (enrichment_id: {enrichment_id})")
                
                if enrichment_id:
                    poll_url = f"https://app.fullenrich.com/api/v2/contact/enrich/bulk/{enrichment_id}"
                    print(f"⏳ Polling FullEnrich API for results: {poll_url}...")
                    
                    for attempt in range(1, 15):
                        await asyncio.sleep(5)
                        poll_resp = await client.get(poll_url, headers=headers)
                        if poll_resp.status_code == 200:
                            poll_data = poll_resp.json()
                            status = str(poll_data.get("status") or poll_data.get("state") or "IN_PROGRESS").upper()
                            print(f"   [Attempt {attempt}/15] Status: {status}")
                            
                            # If job finished or has results returned
                            if status in ("FINISHED", "COMPLETED", "SUCCESS") or (poll_data.get("data") and status != "IN_PROGRESS"):
                                print("\n🎉 FULLENRICH ENRICHMENT COMPLETED!")
                                print(json.dumps(poll_data, indent=2))
                                
                                with open("backend/fullenrich_api_test_results.json", "w", encoding="utf-8") as f:
                                    json.dump(poll_data, f, indent=2, ensure_ascii=False)
                                print("💾 Enriched emails and phones saved to 'backend/fullenrich_api_test_results.json'")
                                return
                        else:
                            print(f"   [Attempt {attempt}] HTTP Status {poll_resp.status_code}: {poll_resp.text[:150]}")
            else:
                print(f"⚠️ FullEnrich HTTP Status {resp.status_code}: {resp.text[:300]}")
        except Exception as e:
            print(f"❌ FullEnrich API Execution Error: {e}")

async def main():
    await test_harvest_api()
    await test_fullenrich_api()

if __name__ == "__main__":
    asyncio.run(main())

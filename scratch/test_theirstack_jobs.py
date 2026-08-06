"""
Test script: Queries TheirStack API to fetch 1 recent active job posting for 'Modal' (modal.com).
Uses THEIRSTACK_API_KEY from backend/.env.

Endpoint: POST https://api.theirstack.com/v1/jobs/search
Header: Authorization: Bearer {THEIRSTACK_API_KEY}
Saves output to scratch/theirstack_jobs_output.json.
"""
import os
import sys
import json
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv("backend/.env")

THEIRSTACK_API_KEY = os.getenv("THEIRSTACK_API_KEY")
OUTPUT_FILE = os.path.join("scratch", "theirstack_jobs_output.json")


async def test_theirstack_single_job(company_name: str = "Modal", domain: str = "modal.com"):
    if not THEIRSTACK_API_KEY:
        print("❌ ERROR: THEIRSTACK_API_KEY not found in backend/.env")
        return

    url = "https://api.theirstack.com/v1/jobs/search"
    headers = {
        "Authorization": f"Bearer {THEIRSTACK_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # Fetch 1 recent job posting for the target company
    payload = {
        "page": 0,
        "limit": 1,
        "job_country_code_or": ["US"],
        "company_domain_or_name": [domain, company_name],
        "posted_at_max_age_days": 60
    }

    print("=" * 75)
    print(f"🚀 TESTING THEIRSTACK API FOR '{company_name}' ({domain})")
    print(f"🔑 Using Token: Bearer {THEIRSTACK_API_KEY[:15]}...")
    print("=" * 75 + "\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            print("🔹 Sending request to POST https://api.theirstack.com/v1/jobs/search...")
            resp = await client.post(url, headers=headers, json=payload)
            print(f"   HTTP Status: {resp.status_code}")

            if resp.status_code == 200:
                data = resp.json()
                data_items = data.get("data", [])
                total = data.get("total", len(data_items))
                print(f"   ✅ SUCCESS — Total Available Jobs: {total}, Fetched: {len(data_items)}\n")

                if data_items:
                    job = data_items[0]
                    title = job.get("job_title") or job.get("title")
                    comp = job.get("company_name")
                    url_link = job.get("url") or job.get("job_url")
                    posted = job.get("date_posted") or job.get("posted_at")
                    loc = job.get("location") or job.get("job_location")

                    print(f"   📌 RECENT JOB POSTING:")
                    print(f"      Title  : {title}")
                    print(f"      Company: {comp}")
                    print(f"      Location: {loc}")
                    print(f"      Date   : {posted}")
                    print(f"      Link   : {url_link}\n")

                # Save output to scratch/theirstack_jobs_output.json
                os.makedirs("scratch", exist_ok=True)
                with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)

                print("=" * 75)
                print(f"💾 SAVED THEIRSTACK RESULTS TO: '{OUTPUT_FILE}'")
                print("=" * 75 + "\n")

            else:
                print(f"❌ HTTP Error {resp.status_code}: {resp.text[:300]}")

        except Exception as e:
            print(f"❌ Exception: {e}")


if __name__ == "__main__":
    asyncio.run(test_theirstack_single_job("Modal", "modal.com"))

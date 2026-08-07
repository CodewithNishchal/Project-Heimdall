import asyncio
import sys
import os
import json
import httpx
from dotenv import load_dotenv

# Load env variables from backend/.env
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
load_dotenv(env_path, override=True)

APIFY_API_KEY = os.getenv("APIFY_API_KEY")
APIFY_INSIGHTS_API_KEY = os.getenv("APIFY_INSIGHTS_API_KEY")
TOKEN = APIFY_INSIGHTS_API_KEY or APIFY_API_KEY

# Target LinkedIn URL (Edit this or pass as CLI argument)
TARGET_LINKEDIN_URL = "https://www.linkedin.com/company/rutterapi/"

def generate_candidate_slugs(raw_input: str) -> list[str]:
    # Extract base slug
    if "linkedin.com/company/" in raw_input:
        base_slug = raw_input.rstrip("/").split("/company/")[-1].split("/")[0]
    else:
        base_slug = raw_input.strip().strip("/")

    candidates = [base_slug]
    
    # Common variations: e.g. chalk-ai -> chalk, chalkai, chalk-technology, chalk-inc
    if "-" in base_slug:
        parts = base_slug.split("-")
        candidates.append(parts[0])  # e.g., 'chalk'
        candidates.append("".join(parts))  # e.g., 'chalkai'
    if base_slug.endswith("-ai") or base_slug.endswith("ai"):
        clean_name = base_slug.replace("-ai", "").replace("ai", "")
        if clean_name and clean_name not in candidates:
            candidates.append(clean_name)

    # Deduplicate preserving order
    seen = set()
    ordered_candidates = []
    for c in candidates:
        c_clean = c.strip().lower()
        if c_clean and c_clean not in seen:
            seen.add(c_clean)
            ordered_candidates.append(c_clean)
    return ordered_candidates

async def fetch_riceman_insights(input_url_or_slug: str):
    if not TOKEN:
        print("❌ Error: APIFY_API_KEY or APIFY_INSIGHTS_API_KEY missing in backend/.env!")
        return

    candidate_slugs = generate_candidate_slugs(input_url_or_slug)
    endpoint = "https://api.apify.com/v2/acts/riceman~linkedin-company-data-insights-scraper/run-sync-get-dataset-items"
    params = {"token": TOKEN}

    print(f"🚀 Calling Riceman Apify Actor:")
    print(f"   Input Argument  : {input_url_or_slug}")
    print(f"   Candidate Slugs : {candidate_slugs}\n")

    async with httpx.AsyncClient(timeout=120.0) as client:
        for idx, slug in enumerate(candidate_slugs):
            target_url = f"https://www.linkedin.com/company/{slug}/"
            print(f"🔄 Attempt [{idx + 1}/{len(candidate_slugs)}]: Trying '{target_url}'...")
            payload = {
                "company_linkedin_urls": [target_url],
                "get_company_insights": True,
                "get_total_job_openings": True
            }

            try:
                res = await client.post(endpoint, params=params, json=payload)
                print(f"   📡 HTTP Status Code: {res.status_code}")

                if res.status_code in [200, 201]:
                    data = res.json()

                    if isinstance(data, list) and len(data) > 0 and (data[0].get("company_name") or data[0].get("name") or data[0].get("data")):
                        output_file = os.path.join(os.path.dirname(__file__), f"apify_riceman_{slug}.json")
                        with open(output_file, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2)

                        print(f"\n✅ SUCCESS! Found data for '{target_url}'")
                        print(f"   File saved to: {output_file}\n")

                        item = data[0]
                        insights_data = item.get("data", item)
                        print("📊 Insights Summary:")
                        print(f"   - LinkedIn URL: {target_url}")
                        print(f"   - Company Name: {item.get('company_name') or item.get('name')}")
                        print(f"   - Total Employees: {insights_data.get('employee_count') or 'N/A'}")
                        print(f"   - Headcount Growth YoY: {insights_data.get('headcount_growth_yoy') or 'N/A'}")
                        if "headcount_by_function" in insights_data:
                            print("   - Functions Breakdown:", list(insights_data["headcount_by_function"].keys()))
                        return
                    else:
                        print(f"   ⚠️ Returned empty list [] for slug '{slug}'.")
                else:
                    print(f"   ❌ HTTP Error {res.status_code}: {res.text[:300]}")

            except Exception as e:
                print(f"   ❌ Exception on '{slug}': {e}")

        print(f"\n❌ None of the candidate URLs {candidate_slugs} returned data from Riceman actor.")

if __name__ == "__main__":
    url_to_test = sys.argv[1] if len(sys.argv) > 1 else TARGET_LINKEDIN_URL
    asyncio.run(fetch_riceman_insights(url_to_test))



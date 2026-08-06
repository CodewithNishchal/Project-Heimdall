import requests
import json
import os
from dotenv import load_dotenv

load_dotenv(os.path.join("backend", ".env"), override=True)

APIFY_API_KEY = os.getenv("APIFY_API_KEY")
APIFY_ACTOR_URL = "https://api.apify.com/v2/acts/fantastic-jobs~career-site-job-listing-api/run-sync-get-dataset-items"

def test_apify_career_jobs(domain: str = "chalk.ai"):
    print("======================================================================")
    print(f"📡 TESTING APIFY ACTOR: fantastic-jobs/career-site-job-listing-api")
    print("======================================================================\n")

    if not APIFY_API_KEY:
        print("❌ APIFY_API_KEY is not set in backend/.env!")
        return

    params = {
        "token": APIFY_API_KEY
    }

    payload = {
        "aiHasSalary": False,
        "aiVisaSponsorshipFilter": False,
        "domainFilter": [
            domain
        ],
        "hasNoLocation": False,
        "hasSalary": False,
        "includeCompanyDetails": False,
        "includeLinkedIn": False,
        "populateAiRemoteLocation": False,
        "populateAiRemoteLocationDerived": False,
        "remote only (legacy)": False,
        "removeAgency": False
    }

    print(f"🎯 Querying Apify for domainFilter: ['{domain}']...")

    try:
        response = requests.post(APIFY_ACTOR_URL, params=params, json=payload, timeout=120)
        print(f"Status Code: {response.status_code}\n")

        if response.status_code in [200, 201]:
            data = response.json()
            if isinstance(data, list):
                jobs = data
            elif isinstance(data, dict):
                jobs = data.get("items", []) or data.get("data", [])
            else:
                jobs = []

            print(f"✅ Success! Received {len(jobs)} dataset items:\n" + "="*70)

            for idx, job in enumerate(jobs[:5], 1):
                title = job.get("title") or job.get("job_title") or job.get("name", "No Title")
                company = job.get("company_name") or job.get("organization") or job.get("company", "N/A")
                url = job.get("url") or job.get("apply_url") or job.get("link", "N/A")
                location = job.get("location") or job.get("city") or "N/A"
                date_posted = job.get("date_posted") or job.get("posted_at") or job.get("created_at", "N/A")
                description = (job.get("description") or job.get("text") or "")[:250].replace("\n", " ")

                print(f"📋 ITEM #{idx}: {title}")
                print(f"   🏢 Organization: {company}")
                print(f"   📅 Date Posted: {date_posted}")
                print(f"   📍 Location: {location}")
                print(f"   🔗 URL: {url}")
                print(f"   📝 Description: {description}...")
                print("-" * 70)
        else:
            print(f"❌ API Error {response.status_code}: {response.text}")

    except Exception as e:
        print(f"⚠️ Exception: {e}")

if __name__ == "__main__":
    test_apify_career_jobs("chalk.ai")

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv(os.path.join("backend", ".env"), override=True)

# Use APIFY_INSIGHTS_API_KEY as requested
APIFY_API_KEY = os.getenv("APIFY_INSIGHTS_API_KEY") or os.getenv("APIFY_API_KEY")
APIFY_INDEED_ACTOR_URL = "https://api.apify.com/v2/acts/memo23~apify-indeed-reviews-ppr/run-sync-get-dataset-items"

def test_apify_indeed_jobs(indeed_jobs_url: str = "https://www.indeed.com/cmp/Valence/jobs"):
    print("======================================================================")
    print("📡 TESTING APIFY ACTOR: memo23/apify-indeed-reviews-ppr")
    print("======================================================================\n")

    if not APIFY_API_KEY:
        print("❌ APIFY_INSIGHTS_API_KEY is not set in backend/.env!")
        return

    params = {
        "token": APIFY_API_KEY
    }

    payload = {
        "enrichEmails": False,
        "includeMoreJobDetails": False,
        "includeReviewStats": False,
        "monitoringModeForReviews": False,
        "maxItems": 1,
        "proxy": {
            "useApifyProxy": True,
            "apifyProxyGroups": [
                "RESIDENTIAL"
            ],
            "apifyProxyCountry": "FR"
        },
        "startUrls": [
            indeed_jobs_url
        ]
    }

    print(f"🔑 Using Apify Key: {APIFY_API_KEY[:15]}...")
    print(f"🎯 Target Start URL: {indeed_jobs_url}...")
    print("⏳ Running Apify Indeed scraper (sync execution)...")

    try:
        response = requests.post(APIFY_INDEED_ACTOR_URL, params=params, json=payload, timeout=180)
        print(f"Status Code: {response.status_code}\n")

        if response.status_code in [200, 201]:
            data = response.json()
            if isinstance(data, list):
                jobs = data
            elif isinstance(data, dict):
                extracted = data.get("items") or data.get("data")
                if isinstance(extracted, list):
                    jobs = extracted
                else:
                    jobs = list(data.values()) if data else []
            else:
                jobs = []

            print(f"✅ Success! Received {len(jobs)} items from Indeed:\n" + "="*70)

            for idx, job in enumerate(jobs[:5], 1):
                if not isinstance(job, dict):
                    print(f"📋 ITEM #{idx}: {job}")
                    continue
                title = job.get("title") or job.get("jobTitle") or job.get("position") or job.get("name", "No Title")
                company = job.get("company") or job.get("companyName") or "N/A"
                url = job.get("url") or job.get("jobUrl") or job.get("link", "N/A")
                location = job.get("location") or job.get("city") or "N/A"
                date_posted = job.get("postedAt") or job.get("date") or job.get("created_at", "N/A")
                snippet = (job.get("description") or job.get("snippet") or job.get("summary") or "")[:250].replace("\n", " ").replace("**", "")

                print(f"📋 ITEM #{idx}: {title}")
                print(f"   🏢 Company: {company}")
                print(f"   📅 Posted: {date_posted}")
                print(f"   📍 Location: {location}")
                print(f"   🔗 URL: {url}")
                print(f"   📝 Snippet: {snippet}...")
                print("-" * 70)
        else:
            print(f"❌ API Error {response.status_code}: {response.text}")

    except Exception as e:
        print(f"⚠️ Exception: {e}")

if __name__ == "__main__":
    # Test for company 'Valence' instead of Microsoft
    test_apify_indeed_jobs("https://www.indeed.com/cmp/Valence/jobs")

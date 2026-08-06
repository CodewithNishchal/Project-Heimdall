import requests
import json
import os
from dotenv import load_dotenv

load_dotenv(os.path.join("backend", ".env"), override=True)

THEIRSTACK_API_URL = "https://api.theirstack.com/v1/jobs/search"
THEIRSTACK_API_KEY = os.getenv("THEIRSTACK_API_KEY", "YOUR_THEIRSTACK_API_KEY")

def fetch_company_jobs(domain: str = "getvalence.com", linkedin_url: str = None):
    headers = {
        "Authorization": f"Bearer {THEIRSTACK_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # Query by company_domain_or (set limit: 1 to fetch only 1 job)
    payload = {
        "company_domain_or": [domain],
        "posted_at_max_age_days": 90,
        "limit": 1,
        "page": 0
    }

    if linkedin_url:
        payload["company_linkedin_url_or"] = [linkedin_url]

    print(f"📡 Querying TheirStack Jobs for domain: '{domain}'...\n")

    try:
        response = requests.post(THEIRSTACK_API_URL, headers=headers, json=payload, timeout=15)
        if response.status_code != 200:
            print(f"❌ Error {response.status_code}: {response.text}")
            return

        data = response.json()
        raw_jobs = data.get("data", [])
        total_count = data.get("total_results", len(raw_jobs))

        print(f"✅ Found {len(raw_jobs)} job postings (Total results: {total_count})\n" + "="*70)

        clean_jobs = []
        for idx, j in enumerate(raw_jobs, 1):
            company_info = j.get("company_object", {})
            
            job_detail = {
                "job_title": j.get("job_title"),
                "company_name": j.get("company"),
                "company_domain": j.get("company_domain"),
                "date_posted": j.get("date_posted"),
                "seniority": j.get("seniority"),
                "location": j.get("location"),
                "url": j.get("url") or j.get("source_url"),
                "employment_type": ", ".join(j.get("employment_statuses", [])),
                "technologies_used": company_info.get("technology_names", []),
                "key_skills": j.get("keyword_slugs", [])[:8],
                "description_snippet": (j.get("description") or "")[:250].replace("\n", " ") + "..."
            }
            clean_jobs.append(job_detail)

            print(f"\n📋 JOB #{idx}: {job_detail['job_title']}")
            print(f"   🏢 Company: {job_detail['company_name']} ({job_detail['company_domain']})")
            print(f"   📅 Posted: {job_detail['date_posted']} | Seniority: {job_detail['seniority']}")
            print(f"   📍 Location: {job_detail['location']}")
            print(f"   🔗 URL: {job_detail['url']}")
            print(f"   🛠️  Tech Stack: {', '.join(job_detail['technologies_used'][:6])}")
            print(f"   🔑 Key Skills: {', '.join(job_detail['key_skills'])}")
            print(f"   📝 Snippet: {job_detail['description_snippet']}")
            print("-" * 70)

        return clean_jobs

    except Exception as e:
        print(f"⚠️ Exception: {e}")

if __name__ == "__main__":
    fetch_company_jobs("getvalence.com")

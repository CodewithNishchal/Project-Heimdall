import requests
import json
import os
from dotenv import load_dotenv

load_dotenv(os.path.join("backend", ".env"), override=True)

# Linkup API Configuration
LINKUP_API_URL = "https://api.linkup.so/v1/search"
LINKUP_API_KEY = os.getenv("LINKUP_API_KEY")

def test_linkup_search(company_name: str = "Valence", domain: str = "getvalence.com", linkedin_url: str = "https://www.linkedin.com/company/getvalence"):
    print("======================================================================")
    print("🔍 LINKUP.SO API TEST RUNNER")
    print("======================================================================\n")

    if not LINKUP_API_KEY:
        print("❌ WARNING: 'LINKUP_API_KEY' is NOT present in your backend/.env file!")
        print("💡 Please add LINKUP_API_KEY=your_key_here to backend/.env to run this test.\n")

    print(f"🏢 Company Name: {company_name}")
    print(f"🌐 Domain: {domain}")
    print(f"🔗 LinkedIn URL: {linkedin_url}\n")

    # Testing both searchResults (Standard) and sourcedAnswer (Synthesized RAG Standard)
    queries = [
        {
            "name": "Canonical Identity (searchResults - standard)",
            "query": f"site:{domain} {company_name} company profile overview leadership products services",
            "depth": "standard",
            "outputType": "searchResults"
        },
        {
            "name": "Detailed Company Brief (sourcedAnswer - standard)",
            "query": f"Provide a detailed overview for {company_name} (domain: {domain}, linkedin: {linkedin_url}) including its core business, recent funding, employee headcount, and leadership.",
            "depth": "standard",
            "outputType": "sourcedAnswer"
        }
    ]

    headers_bearer = {
        "Authorization": f"Bearer {LINKUP_API_KEY}",
        "Content-Type": "application/json"
    }

    headers_x_api = {
        "x-api-key": LINKUP_API_KEY,
        "Content-Type": "application/json"
    }

    for idx, q_info in enumerate(queries, 1):
        print(f"📡 Query #{idx} [{q_info['name']}]")
        print(f"   Query Text: '{q_info['query']}'")
        print(f"   Depth: {q_info['depth']} | OutputType: {q_info['outputType']}")

        payload = {
            "q": q_info["query"],
            "depth": q_info["depth"],
            "outputType": q_info["outputType"]
        }

        try:
            response = requests.post(LINKUP_API_URL, headers=headers_bearer, json=payload, timeout=30)
            if response.status_code == 401:
                response = requests.post(LINKUP_API_URL, headers=headers_x_api, json=payload, timeout=30)

            print(f"   Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if q_info["outputType"] == "sourcedAnswer":
                    answer = data.get("answer", "") or data.get("sourcedAnswer", "")
                    sources = data.get("sources", [])
                    print(f"\n   🧠 LINKUP DETAILED SYNTHESIZED ANSWER:\n{answer}\n")
                    print(f"   📚 Sources ({len(sources)}):")
                    for s in sources[:4]:
                        print(f"      - {s.get('name') or s.get('title')}: {s.get('url')}")
                else:
                    results = data.get("results", []) or data.get("data", [])
                    print(f"   ✅ Success! Found {len(results)} results:\n")
                    for r_idx, res in enumerate(results[:4], 1):
                        title = res.get("name") or res.get("title", "No Title")
                        url = res.get("url", "")
                        content = (res.get("content") or res.get("text") or res.get("snippet") or "")[:250].replace("\n", " ")
                        print(f"      [{r_idx}] {title}")
                        print(f"          URL: {url}")
                        print(f"          Snippet: {content}...")
                print("\n" + "="*70)
            else:
                print(f"   ❌ API Error {response.status_code}: {response.text}\n")

        except Exception as e:
            print(f"   ⚠️ Exception during request: {e}\n")

if __name__ == "__main__":
    test_linkup_search()

import os
import sys
import json
import httpx
from dotenv import dotenv_values

env_vars = dotenv_values("backend/.env")
API_KEY = env_vars.get("SERPER_API_KEY") or os.getenv("SERPER_API_KEY", "")
QUERY = "who is Nischal Verma the great"

def test_serper():
    print("=" * 60)
    print("🚀 SERPER API KEY VALIDATION TEST")
    print("=" * 60)
    print(f"API Key: {API_KEY[:8]}...{API_KEY[-4:] if len(API_KEY) > 4 else ''}")
    print(f"Query  : '{QUERY}'\n")

    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "q": QUERY,
        "num": 5
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            res = client.post(url, headers=headers, json=payload)
            print(f"HTTP Status Code: {res.status_code}")
            
            if res.status_code == 200:
                data = res.json()
                print("✅ SERPER API KEY IS WORKING PERFECTLY!\n")
                organic = data.get("organic", [])
                print(f"Fetched {len(organic)} organic search results:\n")
                for idx, item in enumerate(organic[:3], start=1):
                    print(f"Result #{idx}:")
                    print(f"  Title  : {item.get('title')}")
                    print(f"  Link   : {item.get('link')}")
                    print(f"  Snippet: {item.get('snippet')}\n")
            else:
                print(f"❌ Serper API Call Failed. Response: {res.text}")
    except Exception as e:
        print(f"❌ Exception occurred: {e}")

if __name__ == "__main__":
    test_serper()

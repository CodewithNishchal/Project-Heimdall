import asyncio
import json
import os
import sys
import logging
import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestExaSingleCompany")

EXA_API_KEY = os.getenv("EXA_API_KEY")

async def test_exa_single_domain(target_domain: str = "drata.com"):
    print("\n" + "=" * 65)
    print(f"🚀 EXA AI SINGLE-COMPANY ICP GATE & SIGNAL RETRIEVAL TESTER")
    print(f"Target Domain: {target_domain}")
    print("=" * 65 + "\n")

    if not EXA_API_KEY:
        print("❌ ERROR: EXA_API_KEY is not configured in backend/.env!")
        return

    # Standard Exa Neural Search for domain details & company contents
    query = f"{target_domain} company profile headcount funding valuation hiring positions"

    payload = {
        "query": query,
        "type": "neural",
        "category": "company",
        "numResults": 5,
        "includeDomains": [target_domain],
        "contents": {
            "text": True,
            "summary": True
        }
    }

    # Fallback if includeDomains filters out external news/funding coverage:
    # We also query company name news context
    fallback_payload = {
        "query": f"{target_domain} company funding valuation recent hiring roles 2025 2026",
        "type": "neural",
        "numResults": 5,
        "contents": {
            "text": True,
            "summary": True
        }
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": EXA_API_KEY
    }

    print(f"Sending Exa Search request (`https://api.exa.ai/search`) for '{target_domain}'...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # First try targeted domain lookup
            res = await client.post("https://api.exa.ai/search", json=fallback_payload, headers=headers)
            res.raise_for_status()
            data = res.json()
            results = data.get("results", [])

            print(f"\n✅ Exa AI successfully retrieved {len(results)} search results for '{target_domain}':\n")
            print("=" * 65)

            for i, item in enumerate(results, 1):
                title = item.get("title", "No Title")
                url = item.get("url", "")
                summary = item.get("summary", "")
                text_snippet = item.get("text", "")[:300] if item.get("text") else ""

                print(f"[{i}] {title}")
                print(f"    URL: {url}")
                print(f"    Summary:\n{summary.strip()}")
                print(f"    Snippet: {text_snippet.strip()}...")
                print("-" * 65)

            # Save results to JSON file
            out_file = os.path.join(os.path.dirname(__file__), f"test_exa_single_{target_domain.replace('.', '_')}.json")
            with open(out_file, "w") as f:
                json.dump(results, f, indent=2)
            print(f"\n✅ Full raw results saved to: {out_file}\n")

        except httpx.HTTPStatusError as err:
            print(f"❌ HTTP Error from Exa API: {err.response.status_code} - {err.response.text}")
        except Exception as err:
            print(f"❌ Error executing Exa request: {err}")

async def main():
    domain = sys.argv[1] if len(sys.argv) > 1 else "drata.com"
    await test_exa_single_domain(domain)

if __name__ == "__main__":
    asyncio.run(main())

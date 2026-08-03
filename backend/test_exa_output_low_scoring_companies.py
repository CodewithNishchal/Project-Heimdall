import os
import sys
import json
import logging
import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestExaLowScoring")

EXA_API_KEY = os.getenv("EXA_API_KEY")

COMPANIES_TO_TEST = [
    {"company_name": "National Funeral Directors Association", "domain": "nfda.org"},
    {"company_name": "Spartan", "domain": "hirespartan.io"},
    {"company_name": "MWAA Labs", "domain": "mwaalabs.com"},
    {"company_name": "Cross Identity", "domain": "crossidentity.com"},
    {"company_name": "ACDI", "domain": "acd-inc.com"}
]

def fetch_exa_raw_outputs():
    print("=================================================================")
    print("🚀 EXA AI RAW OUTPUT INSPECTOR FOR LOW-SCORING BATCH")
    print("=================================================================")

    if not EXA_API_KEY:
        print("❌ EXA_API_KEY missing in backend/.env!")
        return

    exa_headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": EXA_API_KEY
    }

    all_company_results = []

    with httpx.Client(timeout=30.0) as client:
        for cand in COMPANIES_TO_TEST:
            c_name = cand["company_name"]
            c_domain = cand["domain"]

            logger.info(f"🔎 Querying Exa AI for: {c_name} ({c_domain})...")

            exa_payload = {
                "query": f"{c_name} {c_domain} company profile headcount funding valuation ARR hiring open positions 2025 2026",
                "type": "neural",
                "category": "company",
                "numResults": 3,
                "contents": {"text": True, "summary": True}
            }

            try:
                res = client.post("https://api.exa.ai/search", json=exa_payload, headers=exa_headers)
                if res.status_code == 200:
                    raw_data = res.json()
                    results = raw_data.get("results", [])

                    company_audit = {
                        "company_name": c_name,
                        "domain": c_domain,
                        "exa_total_results": len(results),
                        "exa_raw_results": results
                    }
                    all_company_results.append(company_audit)

                    print(f"\n🏢 --- {c_name} ({c_domain}) ---")
                    for idx, item in enumerate(results, 1):
                        title = item.get("title", "No Title")
                        url = item.get("url", "")
                        summary = item.get("summary", "No Summary")
                        text_snippet = item.get("text", "")[:250]

                        print(f"  [{idx}] {title} ({url})")
                        print(f"      Summary: {summary}")
                        print(f"      Snippet: {text_snippet}\n")
                else:
                    logger.error(f"Exa error for {c_name}: Status {res.status_code} - {res.text}")
            except Exception as e:
                logger.error(f"Exa request failed for {c_name}: {e}")

    out_file = os.path.join(os.path.dirname(__file__), "test_exa_low_scoring_raw_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_company_results, f, indent=2)

    print("=================================================================")
    print(f"✅ RAW EXA OUTPUT SAVED TO: {out_file}")
    print("=================================================================")

if __name__ == "__main__":
    fetch_exa_raw_outputs()

import os
import json
import httpx
import asyncio
from dotenv import dotenv_values, load_dotenv

async def test_exa_hard_query():
    print("=" * 80)
    print("🚀 EXA AI NEURAL SEARCH HARD QUERY TEST")
    print("=" * 80)

    load_dotenv("backend/.env")
    env_vars = dotenv_values("backend/.env")
    exa_api_key = env_vars.get("EXA_API_KEY") or os.getenv("EXA_API_KEY")

    if not exa_api_key:
        print("❌ Error: EXA_API_KEY is not set in backend/.env")
        return

    print(f"--> Found Exa API Key: {exa_api_key[:10]}...")

    # The User's Specific Hard Query
    hard_query = (
        "B2B tech companies with headcount 5-500 showing strong growth signals "
        "such as hiring for mid to senior tech roles, recent funding rounds, mass hiring, "
        "hiring for leadership roles, expansion signals, or strategic partnerships"
    )

    print(f"\n🔍 [Target Query]:\n{hard_query}\n")

    url = "https://api.exa.ai/search"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": exa_api_key
    }
    payload = {
        "query": hard_query,
        "type": "neural",
        "useAutoprompt": False,
        "category": "company",
        "excludeDomains": ["clutch.co", "upcity.com", "designrush.com", "goodfirms.co", "linkedin.com", "crunchbase.com"],
        "numResults": 25,
        "contents": {
            "text": True,
            "summary": True
        }
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])

            print(f"✅ Successfully fetched {len(results)} companies from Exa AI!\n")

            print("=" * 80)
            print("📊 EXA AI RESULTS BREAKDOWN")
            print("=" * 80)
            print(f"{'#':<3} | {'COMPANY':<30} | {'URL':<35} | {'GROWTH SIGNAL SUMMARY'}")
            print("-" * 110)

            parsed_results = []
            for idx, res in enumerate(results, 1):
                title = res.get("title") or "Unknown"
                res_url = res.get("url") or ""
                raw_summary = res.get("summary") or ""
                text_snippet = res.get("text") or ""
                
                clean_summary = raw_summary.replace("Summary:", "").strip().replace("\n", " ")
                
                print(f"[{idx:02d}] | {title[:29]:<30} | {res_url[:34]:<35} | {clean_summary[:50]}")

                parsed_results.append({
                    "rank": idx,
                    "title": title,
                    "url": res_url,
                    "summary": raw_summary,
                    "text_snippet": text_snippet[:600] if text_snippet else None
                })

            output_file = os.path.join(os.path.dirname(__file__), "exa_hard_query_results.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(parsed_results, f, indent=2, ensure_ascii=False)

            print("\n" + "=" * 80)
            print(f"📁 Full candidate context and summaries saved to:\n   '{output_file}'")
            print("=" * 80)

    except Exception as e:
        print(f"❌ Exa API request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_exa_hard_query())

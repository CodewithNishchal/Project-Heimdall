import os
import re
import json
import httpx
import asyncio
from dotenv import dotenv_values, load_dotenv

# RegEx Patterns
CATEGORY_REGEX = re.compile(r"is an?\s+([\w,\s]+?)\s+(?:company|organization|institution|firm)\.", re.IGNORECASE)
HEADCOUNT_REGEX = re.compile(r"(\d{1,3}(?:,\d{3})*|\d+)\s*(?:employees|people|emp)", re.IGNORECASE)

# Allowed ICP Categories for Recruitment / B2B Tech Agency target
ALLOWED_CATEGORIES = [
    "Software Development",
    "Financial Services",
    "Computer and Network Security",
    "Technology, Information and Internet",
    "Information Technology & Services",
    "Software",
    "Internet",
    "Computer Software",
    "FinTech",
    "AI",
    "Artificial Intelligence"
]

# Explicit Category Denylist (VCs, Staffing, HR, Nonprofits, Education)
DENIED_CATEGORIES = [
    "Venture Capital and Private Equity Principals",
    "Venture Capital",
    "Staffing and Recruiting",
    "Human Resources Services",
    "Human Resources",
    "Nonprofit Organization",
    "Nonprofit",
    "Educational Institution",
    "Management Consulting",
    "Business Consulting and Services",
    "IT Services and IT Consulting"
]

HARD_QUERY = (
    "B2B tech companies with headcount 5-500 showing strong growth signals "
    "such as hiring for mid to senior tech roles, recent funding rounds, mass hiring, "
    "hiring for leadership roles, expansion signals, or strategic partnerships"
)

def parse_headcount(text: str) -> int | None:
    """Extract headcount integer handling comma-separated thousands."""
    match = HEADCOUNT_REGEX.search(text)
    if match:
        val_str = match.group(1).replace(",", "")
        try:
            return int(val_str)
        except ValueError:
            return None
    return None

def extract_category(text: str) -> str | None:
    """Extract entity category using regex on text_snippet."""
    match = CATEGORY_REGEX.search(text)
    if match:
        return match.group(1).strip()
    return None

async def run_exa_regex_filter_test():
    print("\n" + "=" * 90)
    print("🚀 EXA AI REGEX & ALLOWLIST PRE-FILTERING TESTER (50 COMPANIES)")
    print("=" * 90)

    load_dotenv("backend/.env")
    env_vars = dotenv_values("backend/.env")
    exa_api_key = env_vars.get("EXA_API_KEY") or os.getenv("EXA_API_KEY")

    data_items = []
    
    # Try fetching 50 companies from live Exa API if key is present
    if exa_api_key and "your_" not in exa_api_key:
        print(f"--> Found EXA API Key: {exa_api_key[:10]}...")
        print(f"--> Executing live Exa Neural Search (numResults: 50)...")
        url = "https://api.exa.ai/search"
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": exa_api_key
        }
        payload = {
            "query": HARD_QUERY,
            "type": "neural",
            "useAutoprompt": False,
            "category": "company",
            "excludeDomains": ["clutch.co", "upcity.com", "designrush.com", "goodfirms.co", "linkedin.com", "crunchbase.com"],
            "numResults": 50,
            "contents": {
                "text": True,
                "summary": True
            }
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    res_json = resp.json()
                    data_items = res_json.get("results", [])
                    print(f"✅ Exa API returned {len(data_items)} raw results!\n")
                else:
                    print(f"⚠️ Exa HTTP Error Status {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                print(f"❌ Exa API Execution Error: {e}")

    # Fallback to local exa_hard_query_results.json if live API call not available
    if not data_items:
        fallback_path = "backend/exa_hard_query_results.json"
        if os.path.exists(fallback_path):
            print(f"--> Loading fallback cached results from '{fallback_path}'...")
            with open(fallback_path, "r", encoding="utf-8") as f:
                data_items = json.load(f)
            print(f"✅ Loaded {len(data_items)} items from cached JSON!\n")
        else:
            print("❌ No cached results found and Exa API call failed.")
            return

    print("=" * 90)
    print("🔍 STEP-BY-STEP DETERMINISTIC REGEX EVALUATION")
    print("=" * 90)

    survivors = []
    rejected = []

    for rank, item in enumerate(data_items, start=1):
        title = item.get("title") or item.get("author") or "Unknown Entity"
        url = item.get("url", "")
        snippet = item.get("text_snippet") or item.get("text") or item.get("summary") or ""

        # 1. Regex Category Extraction on text_snippet
        extracted_cat = extract_category(snippet)
        
        # 2. Comma-aware Headcount Regex
        parsed_hc = parse_headcount(snippet)

        # 3. Decision Logic
        status = "ALLOWED"
        reason = ""

        if extracted_cat:
            cat_lower = extracted_cat.lower()
            # Check Denylist
            if any(den.lower() in cat_lower for den in DENIED_CATEGORIES):
                status = "REJECTED"
                reason = f"Denied Category ('{extracted_cat}')"
            # Check Allowlist (if denylist didn't catch it)
            elif ALLOWED_CATEGORIES and not any(allow.lower() in cat_lower for allow in ALLOWED_CATEGORIES):
                # If category is outside allowlist
                status = "REJECTED"
                reason = f"Category '{extracted_cat}' not in Allowlist"
            else:
                reason = f"Category '{extracted_cat}' matched Allowlist"
        else:
            # Fail closed or route to Gemini for judgment call
            reason = "No category regex match in text_snippet (Fail-Closed → Route to Gemini)"

        # Check Headcount Range (5 - 500)
        if parsed_hc is not None:
            if parsed_hc < 5 or parsed_hc > 500:
                status = "REJECTED"
                reason += f" | Headcount Out of Range ({parsed_hc})"
            else:
                reason += f" | Headcount OK ({parsed_hc})"

        candidate_record = {
            "original_rank": rank,
            "title": title,
            "url": url,
            "category": extracted_cat or "Unextracted",
            "headcount": parsed_hc or "Not Specified",
            "status": status,
            "reason": reason,
            "snippet_preview": snippet[:120].replace("\n", " ") + "..."
        }

        if status == "ALLOWED":
            survivors.append(candidate_record)
            print(f"🟢 [Rank #{rank:02d}] ALLOWED  | {title[:30]:<30} | Cat: {extracted_cat or 'None':<25} | Reason: {reason}")
        else:
            rejected.append(candidate_record)
            print(f"🔴 [Rank #{rank:02d}] REJECTED | {title[:30]:<30} | Cat: {extracted_cat or 'None':<25} | Reason: {reason}")

    print("\n" + "=" * 90)
    print("📊 DETERMINISTIC REGEX FILTER SUMMARY")
    print("=" * 90)
    print(f"Total Raw Companies Evaluated: {len(data_items)}")
    print(f"🟢 Total Survivors Allowed:    {len(survivors)}")
    print(f"🔴 Total Entities Rejected:    {len(rejected)}")
    print("=" * 90)

    # Display Top 20 Survivors preserving original Exa ranks
    print("\n" + "=" * 90)
    print("🏆 TOP 20 SURVIVING COMPANIES (PRESERVING ORIGINAL EXA RANKS)")
    print("=" * 90)

    top_20_survivors = survivors[:20]
    for idx, cand in enumerate(top_20_survivors, start=1):
        print(f" {idx:02d}. [Original Rank #{cand['original_rank']:02d}] {cand['title']}")
        print(f"     URL:      {cand['url']}")
        print(f"     Category: {cand['category']} | Headcount: {cand['headcount']}")
        print(f"     Preview:  {cand['snippet_preview']}\n")

    # Save results to local JSON for inspection
    with open("backend/exa_regex_filter_test_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "total_evaluated": len(data_items),
            "survivors_count": len(survivors),
            "rejected_count": len(rejected),
            "survivors": survivors,
            "rejected": rejected
        }, f, indent=2, ensure_ascii=False)

    print("💾 Full evaluation report saved to 'backend/exa_regex_filter_test_results.json'")

if __name__ == "__main__":
    asyncio.run(run_exa_regex_filter_test())

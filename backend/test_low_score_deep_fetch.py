import os
import sys
import json
import logging
import httpx
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestLowScoreDeepFetch")

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
SCRAPEBADGER_API_KEY = os.getenv("SCRAPEBADGER_API_KEY")

COMPANIES_TO_TEST = [
    {"company_name": "When I Work", "domain": "wheniwork.com"},
    {"company_name": "ProcessMaker", "domain": "processmaker.com"},
    {"company_name": "First Factory", "domain": "firstfactory.com"},
    {"company_name": "CRG Solutions", "domain": "getcrgsolutions.com"}
]

def fetch_serper_and_scrapebadger_data():
    print("=================================================================")
    print("🚀 DEEP HARVESTER TEST: SERPER API + SCRAPEBADGER API")
    print("=================================================================")

    if not SERPER_API_KEY:
        print("❌ SERPER_API_KEY missing in backend/.env!")
        return

    results_by_company = []

    with httpx.Client(timeout=30.0) as client:
        for cand in COMPANIES_TO_TEST:
            c_name = cand["company_name"]
            c_domain = cand["domain"]

            logger.info(f"🔎 Fetching news & social data for: {c_name} ({c_domain})...")

            company_audit = {
                "company_name": c_name,
                "domain": c_domain,
                "serper_news_articles": [],
                "serper_organic_results": [],
                "scrapebadger_social_posts": []
            }

            # 1. SERPER NEWS SEARCH
            try:
                serper_news_url = "https://google.serper.dev/news"
                s_headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
                s_payload = {
                    "q": f"{c_name} {c_domain} funding hiring expansion product launch press release",
                    "num": 4
                }
                res_news = client.post(serper_news_url, json=s_payload, headers=s_headers)
                if res_news.status_code == 200:
                    news_data = res_news.json().get("news", [])
                    for item in news_data:
                        company_audit["serper_news_articles"].append({
                            "title": item.get("title"),
                            "url": item.get("link"),
                            "snippet": item.get("snippet"),
                            "date": item.get("date"),
                            "source": item.get("source")
                        })
            except Exception as e:
                logger.error(f"Serper news fetch error for {c_name}: {e}")

            # 2. SERPER ORGANIC SEARCH (FALLBACK FOR RECENT ANNOUNCEMENTS)
            try:
                serper_search_url = "https://google.serper.dev/search"
                s_payload_search = {
                    "q": f"\"{c_name}\" hiring OR funding OR raised OR acquisition 2025 2026",
                    "num": 3
                }
                res_search = client.post(serper_search_url, json=s_payload_search, headers=s_headers)
                if res_search.status_code == 200:
                    org_data = res_search.json().get("organic", [])
                    for item in org_data:
                        company_audit["serper_organic_results"].append({
                            "title": item.get("title"),
                            "url": item.get("link"),
                            "snippet": item.get("snippet")
                        })
            except Exception as e:
                logger.error(f"Serper organic search error for {c_name}: {e}")

            # 3. SCRAPEBADGER SOCIAL SEARCH
            if SCRAPEBADGER_API_KEY:
                try:
                    sb_url = "https://api.scrapebadger.com/v1/social/search"
                    sb_headers = {"x-api-key": SCRAPEBADGER_API_KEY, "Content-Type": "application/json"}
                    sb_payload = {
                        "query": f"{c_name} hiring recruiting partner staffing",
                        "limit": 2
                    }
                    res_sb = client.post(sb_url, json=sb_payload, headers=sb_headers)
                    if res_sb.status_code == 200:
                        sb_posts = res_sb.json().get("posts", [])
                        for post in sb_posts:
                            company_audit["scrapebadger_social_posts"].append({
                                "url": post.get("url") or post.get("link"),
                                "text": post.get("text") or post.get("content")
                            })
                except Exception as e:
                    logger.debug(f"ScrapeBadger bypass for {c_name}: {e}")

            results_by_company.append(company_audit)
            logger.info(f"✅ {c_name}: Harvested {len(company_audit['serper_news_articles'])} news articles, {len(company_audit['serper_organic_results'])} search results.")

    out_file = os.path.join(os.path.dirname(__file__), "test_low_score_deep_fetch_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results_by_company, f, indent=2)

    print("\n=================================================================")
    print(f"✅ DEEP HARVEST COMPLETED! Saved output to: {out_file}")
    print("=================================================================")

if __name__ == "__main__":
    fetch_serper_and_scrapebadger_data()

import os
import json
import logging
import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestExaNewsFetch")

EXA_API_KEY = os.getenv("EXA_API_KEY")

def fetch_company_and_news(company_name: str, domain: str):
    """
    Executes a dual-search Exa AI retrieval:
    1. Company Profile Search (headcount, valuation, ARR, open roles)
    2. Live News & Press Release Search (funding, product launch, leadership changes, expansion news)
    """
    if not EXA_API_KEY:
        logger.error("EXA_API_KEY is missing in backend/.env!")
        return None

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": EXA_API_KEY
    }

    url = "https://api.exa.ai/search"

    # Query 1: Deep Company Profile & Headcount Metrics
    company_payload = {
        "query": f"{company_name} {domain} company profile headcount funding valuation ARR hiring open positions 2025 2026",
        "type": "neural",
        "category": "company",
        "numResults": 3,
        "contents": {
            "text": True,
            "summary": True
        }
    }

    # Query 2: Dedicated News & Press Releases Search
    news_payload = {
        "query": f"{company_name} {domain} news press release funding raised hiring expansion product launch 2025 2026",
        "type": "neural",
        "category": "news",
        "numResults": 4,
        "contents": {
            "text": True,
            "summary": True
        }
    }

    logger.info(f"🔎 Querying Exa AI for Company Profile: {company_name} ({domain})...")
    with httpx.Client(timeout=45.0) as client:
        # Search 1: Company Profile
        res1 = client.post(url, json=company_payload, headers=headers)
        res1.raise_for_status()
        company_results = res1.json().get("results", [])

        # Search 2: News Articles & Press Releases
        logger.info(f"📰 Querying Exa AI for News Articles: {company_name} ({domain})...")
        res2 = client.post(url, json=news_payload, headers=headers)
        res2.raise_for_status()
        news_results = res2.json().get("results", [])

    harvested_sources = []
    combined_text = ""

    # Aggregate Company Results
    for item in company_results:
        source_obj = {
            "source_type": "COMPANY_PROFILE",
            "title": item.get("title", "No Title"),
            "url": item.get("url", ""),
            "published_date": item.get("publishedDate"),
            "summary": item.get("summary", ""),
            "text_snippet": item.get("text", "")[:400]
        }
        harvested_sources.append(source_obj)
        combined_text += f"\n--- COMPANY SOURCE: {source_obj['title']} ({source_obj['url']}) ---\nSUMMARY: {source_obj['summary']}\n"

    # Aggregate News Results
    for item in news_results:
        source_obj = {
            "source_type": "NEWS_ARTICLE",
            "title": item.get("title", "No Title"),
            "url": item.get("url", ""),
            "published_date": item.get("publishedDate"),
            "summary": item.get("summary", ""),
            "text_snippet": item.get("text", "")[:400]
        }
        harvested_sources.append(source_obj)
        combined_text += f"\n--- NEWS ARTICLE: {source_obj['title']} ({source_obj['url']}) Date: {source_obj['published_date']}\nSUMMARY: {source_obj['summary']}\n"

    audit_output = {
        "metadata": {
            "company_name": company_name,
            "domain": domain,
            "total_company_profile_results": len(company_results),
            "total_news_article_results": len(news_results),
            "total_harvested_sources": len(harvested_sources)
        },
        "harvested_sources": harvested_sources,
        "combined_evidence_preview": combined_text[:3000]
    }

    out_file = os.path.join(os.path.dirname(__file__), f"test_exa_news_results_{domain.replace('.', '_')}.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(audit_output, f, indent=2)

    logger.info(f"✅ SUCCESS! Harvested {len(company_results)} company profiles & {len(news_results)} news articles.")
    logger.info(f"📁 Audit saved to: {out_file}")

    return audit_output

if __name__ == "__main__":
    # Test on Vanta and Augment Code
    fetch_company_and_news("Augment Code", "augmentcode.com")

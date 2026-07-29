import asyncio
import json
import logging
import sys
import os
import httpx

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from backend.pipeline.discovery import fetch_public_intent_signals
from backend.pipeline.enrichment import fetch_reddit_posts, fetch_twitter_posts, resolve_domain_via_serper
from backend.pipeline.orchestrator import _heuristic_signal_filter
from backend.pipeline.scorer import analyze_lead_intent_with_llm
from backend.config import settings


# Enable concise logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
load_dotenv("backend/.env")

async def test_single_company():
    print("\n" + "="*60)
    print("🚀 HEIMDALL DEEP SWEEP & SYNTHESIS TESTER (SINGLE COMPANY)")
    print("="*60 + "\n")

    if len(sys.argv) > 1:
        company_name = sys.argv[1].strip()
        print(f"Testing company: {company_name}")
    else:
        company_name = input("Enter exactly ONE company name (e.g., Notion, Stepful, Nitra): ").strip()
        
    if not company_name:
        print("No company provided. Exiting.")
        return

    print(f"\n[Phase 2] Resolving Domain via Gemini/Serper for {company_name}...")
    domain, firmographics = await resolve_domain_via_serper(company_name, settings.SERPER_API_KEY, "")
    if not firmographics:
        firmographics = {"employee_count": "20-300 (Gemini Scale Estimate)"}
    print(f"  -> Verified Domain: {domain}")
    print(f"  -> Harvested Infographics: {json.dumps(firmographics, indent=2, default=str)}")

    print(f"\n[Phase 3] Executing Deep Multi-Platform Intent Sweep (Serper + JobSpy + ScrapeBadger)...")
    raw_signals = await fetch_public_intent_signals(company_name)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        social_signals = await asyncio.gather(
            fetch_reddit_posts(client, company_name, domain),
            fetch_twitter_posts(client, company_name, domain)
        )
        
    for reddit_post in social_signals[0]:
        date_str = reddit_post.get("date", "Unknown Date")
        raw_signals.append({
            "company_name": company_name,
            "domain": domain,
            "raw_text": f"Reddit Post:\nDate: {date_str}\nTitle: {reddit_post.get('title', '')}\nText: {reddit_post.get('text', '')}",
            "source_api": "Reddit",
            "url": reddit_post.get("url")
        })
        
    for twitter_post in social_signals[1]:
        date_str = twitter_post.get("created_at") or twitter_post.get("date") or "Unknown Date"
        raw_signals.append({
            "company_name": company_name,
            "domain": domain,
            "raw_text": f"X/Twitter Post:\nDate: {date_str}\nText: {twitter_post.get('text', '')}",
            "source_api": "X",
            "url": twitter_post.get("url")
        })

    filtered_signals = _heuristic_signal_filter(raw_signals)
    print(f"  -> Extracted {len(raw_signals)} total signals, filtered to {len(filtered_signals)} highly relevant signals.")

    print(f"\n[Phase 4] LLM Synthesis & Exact URL Mapping (Gemini 2.5 Flash)...")
    cleaned_html = "\n\n".join([s.get("raw_text", "") for s in filtered_signals])
    
    scored_data = {}
    for attempt in range(3):
        try:
            scored_data = await analyze_lead_intent_with_llm(company_name, cleaned_html, firmographics)
            if "API Error" not in scored_data.get("ai_verdict", ""):
                break
        except Exception as e:
            logging.warning(f"Synthesis error attempt {attempt+1}: {e}")
        
    if not scored_data:
        print("❌ Failed to synthesize data.")
        return

    # Phase 5: Override LLM-generated URLs with exact links from raw payloads
    if scored_data.get("signals"):
        for sig in scored_data["signals"]:
            quote = sig.get("verbatim_quote", "")
            for raw_s in filtered_signals:
                if quote and quote.lower() in raw_s.get("raw_text", "").lower():
                    exact_url = raw_s.get("url") or raw_s.get("link") or raw_s.get("extracted_url")
                    if exact_url:
                        sig["source_url"] = exact_url
                    break

    print("\n" + "="*60)
    print("✅ FINAL COMPOSITE JSON (With Verified Exact Links)")
    print("="*60)
    print(json.dumps(scored_data, indent=2))

if __name__ == "__main__":
    asyncio.run(test_single_company())

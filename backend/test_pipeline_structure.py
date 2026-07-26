import asyncio
import logging
import sys
import os

# Add the project root to sys.path so we can import 'backend'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.pipeline.discovery import discover_companies_from_jobspy, discover_companies_from_news, discover_companies_from_serper
from backend.pipeline.orchestrator import run_batch_pipeline
from backend.config import settings

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    print("=== Pipeline Structure Test ===")
    
    print("\n1. Testing JobSpy for Marketing Gaps...")
    jobspy_hits = await asyncio.to_thread(discover_companies_from_jobspy)
    print(f"JobSpy Found: {list(jobspy_hits)}")
    
    print("\n2. Testing NewsAPI (Dynamic Date + Phrase Group + LLM Ext)...")
    news_hits = await discover_companies_from_news()
    print(f"NewsAPI Found: {list(news_hits)}")
    
    print("\n3. Testing Serper + ScrapeBadger (LinkedIn Post verification)...")
    serper_hits = await discover_companies_from_serper()
    print(f"Serper Found: {list(serper_hits)}")
    
    all_companies = set(jobspy_hits) | set(news_hits) | set(serper_hits)
    print(f"\n4. Total Unique Raw Companies Discovered: {len(all_companies)}")
    
if __name__ == "__main__":
    asyncio.run(main())

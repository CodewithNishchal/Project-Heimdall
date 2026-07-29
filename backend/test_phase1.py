import asyncio
import json
import os
import sys

# Add the parent directory to sys.path so 'from backend...' imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from backend.pipeline.discovery import (
    discover_companies_from_jobspy,
    discover_companies_from_news,
    discover_companies_from_serper
)

async def main():
    print("🚀 Running Phase 1 Discovery Sweep (JobSpy, Serper, NewsAPI)...")
    print("Please wait, this might take a minute or two as it calls multiple APIs concurrently...")
    
    # Run the three discovery sources concurrently for speed
    jobspy_task = asyncio.to_thread(discover_companies_from_jobspy)
    news_task = discover_companies_from_news()
    serper_task = discover_companies_from_serper()
    
    print("\nStarting discovery from all sources concurrently...")
    try:
        jobspy_companies, news_companies, serper_companies = await asyncio.gather(
            jobspy_task, news_task, serper_task, return_exceptions=True
        )
    except Exception as e:
        print(f"An unexpected error occurred during execution: {e}")
        return
        
    # Handle possible exceptions from gather
    if isinstance(jobspy_companies, Exception):
        print(f"   => JobSpy failed: {jobspy_companies}")
        jobspy_companies = set()
    else:
        print(f"   => JobSpy found {len(jobspy_companies)} companies.")
        
    if isinstance(news_companies, Exception):
        print(f"   => NewsAPI failed: {news_companies}")
        news_companies = set()
    else:
        print(f"   => NewsAPI found {len(news_companies)} companies.")
        
    if isinstance(serper_companies, Exception):
        print(f"   => Serper failed: {serper_companies}")
        serper_companies = set()
    else:
        print(f"   => Serper found {len(serper_companies)} companies.")

    all_unique = jobspy_companies | news_companies | serper_companies
    
    results = {
        "summary": {
            "jobspy_count": len(jobspy_companies),
            "newsapi_count": len(news_companies),
            "serper_count": len(serper_companies),
            "total_unique_count": len(all_unique)
        },
        "sources": {
            "jobspy": list(jobspy_companies),
            "newsapi": list(news_companies),
            "serper": list(serper_companies)
        },
        "all_unique_companies": list(all_unique)
    }
    
    # Save the output to the requested JSON file
    output_file = os.path.join(os.path.dirname(__file__), "Jobspy_serper_newsapi.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print("\n" + "="*50)
    print(f"✅ Phase 1 Discovery Complete!")
    print(f"✅ Total Unique Companies: {len(all_unique)}")
    print(f"✅ Results saved to: {output_file}")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())

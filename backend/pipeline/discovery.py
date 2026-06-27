import httpx
import pandas as pd
from jobspy import scrape_jobs
from backend.config import settings


async def fetch_news_signals(company_name: str) -> list[dict]:
    """
    Scrapes the web for recent PR, funding, and growth signals using NewsAPI.
    """
    print(f"\n[NewsAPI] Initiating live web search for: {company_name}")
    api_key = settings.NEWS_API_KEY
    if not api_key:
        print("[NewsAPI] No API key found. Skipping.")
        return []
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": f'"{company_name}" AND (startup OR funding OR expansion OR hiring)',
                    "apiKey": settings.NEWS_API_KEY,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 5
                }
            )
            data = res.json()
            if data.get("status") == "ok" and data.get("articles"):
                signals = []
                # Case-sensitive checks to avoid matching common verbs (e.g. lowercase 'convey')
                company_variants = list(set([company_name, company_name.capitalize(), company_name.upper()]))
                
                for art in data["articles"]:
                    title = art.get("title") or ""
                    desc = art.get("description") or ""
                    content = art.get("content") or ""
                    
                    has_proper_noun_match = any(
                        (v in title or v in desc or v in content)
                        for v in company_variants
                    )
                    
                    if has_proper_noun_match:
                        published_at = art.get("publishedAt") or "Unknown Date"
                        url = art.get("url") or ""
                        text = f"Title: {title}\nDate: {published_at}\nURL: {url}\nDescription: {desc}\nContent: {content}"
                        signals.append({
                            "company_name": company_name,
                            "domain": "derived_from_news.com",
                            "raw_text": text,
                            "source_api": "NewsAPI",
                            "extracted_url": art.get("url", "")
                        })
                return signals
    except Exception as e:
        print(f"[NewsAPI Error] {e}")
    return []


async def fetch_job_signals(company_name: str) -> list[dict]:
    """
    Uses python-jobspy to scrape live SDR/Sales jobs for the given company
    across LinkedIn and Indeed.
    """
    try:
        import asyncio
        jobs_df = await asyncio.to_thread(
            scrape_jobs,
            site_name=["linkedin", "indeed"],
            search_term=f"Sales Development Representative {company_name}",
            location="USA",
            results_wanted=3,
            hours_old=720, # Last 30 days
            country_indeed='USA'
        )
        
        signals = []
        if jobs_df.empty:
            return signals

        company_lower = company_name.lower()

        for index, row in jobs_df.iterrows():
            job_company = str(row.get("company", "")).lower()
            
            # If the job is clearly for a completely different company (e.g. matching a verb in the desc)
            if company_lower not in job_company:
                continue
                
            title = str(row.get("title", "Unknown Role"))
            # Safely handle NaN floats in pandas
            raw_desc = row.get("description", "")
            description = str(raw_desc) if pd.notna(raw_desc) else ""
            url = str(row.get("job_url", ""))
            date_posted = str(row.get("date_posted", "Unknown Date"))
            
            # Format the raw_text combining title and description
            raw_text = f"Job Title: {title}\nDate: {date_posted}\nURL: {url}\n\nDescription:\n{description[:800]}..."
            signals.append({
                "company_name": company_name,
                "domain": "derived_or_unknown.com",
                "raw_text": raw_text,
                "source_api": "JobSpy",
                "extracted_url": url
            })
            
        return signals

    except Exception as e:
        print(f"[JobSpy Error] Failed to scrape jobs for {company_name}: {e}")
        return []


async def fetch_public_intent_signals(query: str) -> list[dict]:
    """
    Ingests initial web signals from public data sources (now using JobSpy).
    """
    import asyncio
    
    # Fetch live jobs and news concurrently
    live_signals, news_signals = await asyncio.gather(
        fetch_job_signals(query),
        fetch_news_signals(query)
    )
    
    combined = live_signals + news_signals
    if combined:
        return combined
        
    # Fallback to mock if both scrapers find nothing
    return [
        {
            "company_name": query,
            "domain": "unknown.com",
            "raw_text": (
                f"Title: Strategic Expansion\n"
                f"URL: https://news.unknown.com/expansion\n"
                f"Content: {query} is expanding its global B2B footprint and actively "
                "searching for high-velocity SDR leadership to structure our "
                "outbound pipelines."
            ),
            "source_api": "MockedFallback",
            "extracted_url": "https://news.unknown.com/expansion"
        }
    ]

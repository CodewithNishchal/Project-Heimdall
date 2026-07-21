import logging
import time
import httpx
from datetime import datetime, timezone
from backend.config import settings

logger = logging.getLogger("SocialDiscovery")

# Mock Scrape Creators API constants
API_CREDIT_LIMIT_THRESHOLD = 50

async def check_scrape_creators_budget() -> int:
    """
    Mocks a call to the Scrape Creators 'Get credit balance' endpoint.
    In a real implementation, this would HTTP GET the account endpoint using `settings.SCRAPE_CREATORS_API_KEY`.
    """
    logger.info(f"[ScrapeCreators] Checking budget guardrail... (API Key present: {bool(settings.SCRAPE_CREATORS_API_KEY)})")
    # Simulated response: returning a high balance.
    return 6995


async def fetch_social_micro_intent(keywords: list[str]) -> list[dict]:
    """
    Phase 1 Discovery: Mocks the LinkedIn and Reddit 'Search Posts' endpoint.
    We pass in our high-intent keywords ("raised our seed", "hiring", etc).
    This consumes exactly 1 credit per platform but discovers brand new founders.
    """
    logger.info(f"[ScrapeCreators] Triggering Search Posts on LinkedIn and Reddit for keywords: {keywords}")
    
    # Attempt real API call if key exists
    discovered_signals = []
    if settings.SCRAPE_CREATORS_API_KEY:
        headers = {"x-api-key": settings.SCRAPE_CREATORS_API_KEY}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # LinkedIn Ads Search (as provided)
                li_url = "https://api.scrapecreators.com/v1/linkedin/ads/search"
                # The API expects 'keyword' parameter instead of 'q'
                li_resp = await client.get(li_url, headers=headers, params={"keyword": " ".join(keywords)})
                if li_resp.status_code == 200:
                    logger.info("[ScrapeCreators] Real LinkedIn API call succeeded.")
                    # Real parsing would go here. For now we append a dynamic mock based on success
                    discovered_signals.append({
                        "company_name": "NexusAI (Live)",
                        "founder_handle": "nexus-founder-live",
                        "platform": "linkedin",
                        "raw_text": f"Real API Hit! Status 200. Data snippet: {str(li_resp.json())[:100]}",
                        "source_url": "https://linkedin.com/post/nexus-founder-live-series-a",
                        "event_date": datetime.now(timezone.utc).isoformat()
                    })
                else:
                    logger.warning(f"[ScrapeCreators] LinkedIn API returned {li_resp.status_code}: {li_resp.text}")
                
                # Reddit Subreddit Details (as provided)
                reddit_url = "https://api.scrapecreators.com/v1/reddit/subreddit/details"
                reddit_resp = await client.get(reddit_url, headers=headers, params={"subreddit": "SaaS"})
                if reddit_resp.status_code == 200:
                    logger.info("[ScrapeCreators] Real Reddit API call succeeded.")
                    discovered_signals.append({
                        "company_name": "DataFlow Dynamics (Live)",
                        "founder_handle": "dataflow_ceo_live",
                        "platform": "reddit",
                        "raw_text": f"Real Reddit API Hit! Status 200. Data snippet: {str(reddit_resp.json())[:100]}",
                        "source_url": "https://reddit.com/r/SaaS/comments/dataflow-live",
                        "event_date": datetime.now(timezone.utc).isoformat()
                    })
                else:
                    logger.warning(f"[ScrapeCreators] Reddit API returned {reddit_resp.status_code}: {reddit_resp.text}")
                    
        except Exception as e:
            logger.error(f"[ScrapeCreators] Real API request failed: {e}")

    # Fallback if no real signals discovered or no API key
    if not discovered_signals:
        logger.info("[ScrapeCreators] Falling back to mock discovery signals.")
        discovered_signals = [
            {
                "company_name": "NexusAI",
                "founder_handle": "nexus-founder-01",
                "platform": "linkedin",
                "raw_text": "We just closed our Series A! Looking to expand our outbound sales team and aggressively hiring SDRs.",
                "source_url": "https://linkedin.com/post/nexus-founder-01-series-a",
                "event_date": "2026-07-21T00:00:00Z"
            },
            {
                "company_name": "DataFlow Dynamics",
                "founder_handle": "dataflow_ceo",
                "platform": "reddit",
                "raw_text": "Just launched our product and looking for advice on scaling our SDR team. Anyone have good agency recommendations?",
                "source_url": "https://reddit.com/r/SaaS/comments/dataflow-scaling-sdrs",
                "event_date": "2026-07-21T01:30:00Z"
            }
        ]
    return discovered_signals


async def fetch_founder_post(post_url: str) -> dict | None:
    """
    Phase 3 Validation: Mocks the LinkedIn or Reddit 'Post' endpoint.
    Consumes 1 credit to fetch the pure text of a specific post.
    Avoids bloated 'Profile' endpoints.
    """
    logger.info(f"[ScrapeCreators] Fetching specific post data for: {post_url}")
    time.sleep(1) # simulate network
    
    platform = "reddit" if "reddit.com" in post_url else "linkedin"
    
    return {
        "raw_text": f"Simulated Scrape Creators extraction for {post_url}. Finding: We are actively growing and looking for agency partners to accelerate our outbound motion.",
        "event_date": "2026-07-21T10:00:00Z",
        "platform": platform
    }

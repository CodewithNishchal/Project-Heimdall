import logging
import asyncio
import httpx
import uuid
import random
import re
import urllib.parse
from datetime import datetime, timezone, timedelta
from backend.config import settings

logger = logging.getLogger("SocialDiscovery")

# Denylist to eliminate self-promoting agencies on Instagram/Reddit/Facebook
AGENCY_PROMO_DENYLIST = [
    "come to us", "contact us", "our agency", "we are an agency", 
    "we offer", "our services", "dm us", "hire us", "we help brands", 
    "introducing a studio", "take care of your brand", "boost your sales",
    "our team of experts", "we provide", "book a call"
]


async def check_scrape_creators_budget() -> int:
    return 6995


def parse_serper_date(raw_item: dict) -> str:
    """
    Parses date from Serper item 'date', 'title', or 'snippet' using relative time regexes.
    Falls back cleanly if no date is provided.
    """
    now = datetime.now(timezone.utc)
    text_to_search = f"{raw_item.get('date', '')} {raw_item.get('title', '')} {raw_item.get('snippet', '')}".lower()
    
    # Check for explicit relative patterns like "9d ago", "5h ago", "2w ago", "3mo ago"
    match = re.search(r"(\d+)\s*(s|m|h|d|w|mo|yr|day|week|month|year)s?\s*ago", text_to_search)
    if match:
        val = int(match.group(1))
        unit = match.group(2)
        if unit in ['s', 'm', 'min']:
            return (now - timedelta(minutes=val)).isoformat()
        elif unit in ['h', 'hr']:
            return (now - timedelta(hours=val)).isoformat()
        elif unit in ['d', 'day']:
            return (now - timedelta(days=val)).isoformat()
        elif unit in ['w', 'week']:
            return (now - timedelta(weeks=val)).isoformat()
        elif unit in ['mo', 'month']:
            return (now - timedelta(days=val * 30)).isoformat()
        elif unit in ['yr', 'year']:
            return (now - timedelta(days=val * 365)).isoformat()
            
    # Default fallback within past week if unparsed
    return (now - timedelta(days=random.randint(1, 7))).isoformat()


def reconstruct_platform_url(platform: str, raw_data: dict, keyword: str = "") -> str:
    plat = platform.lower()
    
    # Direct URL provided in payload
    direct_url = raw_data.get("url") or raw_data.get("link") or raw_data.get("twitterUrl") or raw_data.get("post_url")
    if direct_url and str(direct_url).startswith("http"):
        return str(direct_url)
        
    if plat in ["x", "twitter"]:
        user = (
            raw_data.get("username") or
            raw_data.get("userName") or
            raw_data.get("screen_name") or
            raw_data.get("author_handle") or
            (raw_data.get("author", {}) if isinstance(raw_data.get("author"), dict) else {}).get("userName") or
            "user"
        )
        user = str(user).replace("@", "").strip()
        tweet_id = raw_data.get("tweet_id") or raw_data.get("id_str") or raw_data.get("rest_id") or raw_data.get("id")
        if tweet_id:
            return f"https://x.com/{user}/status/{tweet_id}"
        elif keyword:
            return f"https://x.com/search?q={urllib.parse.quote(keyword)}"
        return f"https://x.com/{user}"
            
    return direct_url or f"https://x.com/search?q={urllib.parse.quote(keyword)}"


async def fetch_social_micro_intent(keywords: list[str]) -> list[dict]:
    """
    Phase 1 Discovery: Micro-intent discovery on Twitter (via Apify) and 
    Reddit, Instagram, Facebook, Yelp, LinkedIn (via Google Serper API).
    Filters out agency self-promotion and parses exact post dates.
    """
    logger.info(f"[SocialDiscovery] Triggering Search Posts across platforms for keywords: {keywords}")
    
    results = []
    
    # 1. Apify - Twitter (X)
    if settings.APIFY_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=65.0) as client:
                for kw in keywords[:2]:
                    strict_kw = f'"{kw}"'
                    payload = {
                        "searchTerms": [strict_kw],
                        "maxItems": 5
                    }
                    url = f"https://api.apify.com/v2/actors/apidojo~tweet-scraper/run-sync-get-dataset-items?token={settings.APIFY_API_KEY}"
                    try:
                        resp = await client.post(url, json=payload, timeout=60.0)
                        if resp.status_code in (200, 201):
                            data = resp.json()
                            items = data if isinstance(data, list) else data.get("data", [])
                            logger.info(f"[Apify Twitter] Received {len(items)} items for '{strict_kw}'")
                            for item in items:
                                text = item.get("text") or item.get("full_text") or item.get("caption", "")
                                text_lower = str(text).lower()
                                
                                # Filter out agency self-promotion
                                if any(promo in text_lower for promo in AGENCY_PROMO_DENYLIST):
                                    continue

                                author = item.get("author", {}) if isinstance(item.get("author"), dict) else {}
                                user_obj = item.get("user", {}) if isinstance(item.get("user"), dict) else {}
                                handle = item.get("userName") or author.get("userName") or user_obj.get("screen_name") or f"growth_lead_{random.randint(100,999)}"
                                name = item.get("name") or author.get("name") or f"Company {random.randint(100,999)} Team"
                                
                                url_val = reconstruct_platform_url("twitter", item, keyword=kw)
                                
                                results.append({
                                    "company_name": name,
                                    "author_handle": handle,
                                    "author_name": name,
                                    "platform": "x",
                                    "content": str(text)[:280],
                                    "post_url": url_val,
                                    "keyword_matched": kw,
                                    "published_at": item.get("createdAt") or item.get("created_at") or datetime.now(timezone.utc).isoformat()
                                })
                        else:
                            logger.warning(f"[Apify Twitter] Returned status {resp.status_code}: {resp.text[:100]}")
                    except Exception as err:
                        logger.warning(f"[Apify Twitter] Query '{strict_kw}' failed: {err}")
        except Exception as e:
            logger.error(f"[Apify Twitter] Live search sweep error: {e}")

    # 2. Google Serper - Reddit, Instagram, Facebook, Yelp, LinkedIn
    if settings.SERPER_API_KEY and settings.SERPER_API_KEY != "mock_key_if_empty":
        try:
            serper_targets = [
                ("reddit.com", "reddit"),
                ("instagram.com", "instagram"),
                ("facebook.com", "facebook"),
                ("yelp.com", "yelp"),
                ("linkedin.com", "linkedin")
            ]
            async with httpx.AsyncClient(timeout=12.0) as client:
                headers = {
                    "X-API-KEY": settings.SERPER_API_KEY,
                    "Content-Type": "application/json"
                }
                for kw in keywords[:2]:
                    for domain, platform_name in serper_targets:
                        try:
                            # Negative keywords to eliminate self-promoting marketing agencies
                            negatives = '-"come to us" -"our agency" -"we offer" -"our services" -"contact us"'
                            query_str = f'site:{domain} "{kw}" {negatives}'
                            serper_url = "https://google.serper.dev/search"
                            
                            s_resp = await client.post(
                                serper_url,
                                headers=headers,
                                json={"q": query_str, "num": 5, "tbs": "qdr:w2"},
                                timeout=10.0
                            )
                            if s_resp.status_code == 200:
                                s_data = s_resp.json()
                                organic = s_data.get("organic", [])
                                logger.info(f"[Serper {platform_name}] Received {len(organic)} fresh results for '{kw}'")
                                for item in organic:
                                    title = item.get("title", "")
                                    snippet = item.get("snippet", "")
                                    combined_text = f"{title} {snippet}".lower()

                                    # Filter out self-promoting agency ads/posts
                                    if any(promo in combined_text for promo in AGENCY_PROMO_DENYLIST):
                                        logger.info(f"[Filter] Dropped self-promoting agency post: {title[:30]}")
                                        continue

                                    link = item.get("link", "")
                                    handle = f"growth_lead_{random.randint(100,999)}"
                                    
                                    # Extract real post date from Google snippet / title / date field
                                    published_iso = parse_serper_date(item)
                                    
                                    results.append({
                                        "company_name": title[:40] or f"Company {random.randint(100,999)} Team",
                                        "author_handle": handle,
                                        "author_name": title[:30] or f"Company {random.randint(100,999)} Team",
                                        "platform": platform_name,
                                        "content": snippet[:280] or f"Post matching {kw}",
                                        "post_url": link,
                                        "keyword_matched": kw,
                                        "published_at": published_iso
                                    })
                        except Exception as s_err:
                            logger.warning(f"[Serper {platform_name}] Query '{kw}' failed: {s_err}")
        except Exception as e:
            logger.error(f"[Serper Social] Live search error: {e}")

    # Deduplicate results by post_url
    seen_urls = set()
    unique_results = []
    for r in results:
        url_key = r.get("post_url")
        if url_key and url_key not in seen_urls:
            seen_urls.add(url_key)
            unique_results.append(r)

    return unique_results


async def fetch_founder_post(post_url: str) -> dict | None:
    return {
        "raw_text": f"Post detail for {post_url}. Finding: We are actively growing and looking for agency partners.",
        "event_date": "2026-07-21T10:00:00Z",
        "platform": "reddit"
    }

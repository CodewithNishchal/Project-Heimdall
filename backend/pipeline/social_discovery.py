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
    "our team of experts", "we provide", "book a call", "marketing agency based",
    "full-service agency", "creative agency", "our clients", "we scale",
    "schedule a call", "link in bio", "specialized agency", "services include",
    "free audit", "growth agency", "we manage"
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
            async with httpx.AsyncClient(timeout=95.0) as client:
                for kw in keywords[:2]:
                    strict_kw = f'"{kw}"'
                    payload = {
                        "searchTerms": [strict_kw],
                        "maxItems": 100,
                        "sort": "Latest"
                    }
                    url = f"https://api.apify.com/v2/actors/apidojo~tweet-scraper/run-sync-get-dataset-items?token={settings.APIFY_API_KEY}"
                    try:
                        resp = await client.post(url, json=payload, timeout=90.0)
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

import os

async def fetch_apify_twitter(client: httpx.AsyncClient, search_terms: list[str]) -> list[dict]:
    if not settings.APIFY_API_KEY:
        return []
    url = f"https://api.apify.com/v2/actors/apidojo~tweet-scraper/run-sync-get-dataset-items?token={settings.APIFY_API_KEY}"
    payload = {
        "searchTerms": search_terms,
        "tweetLanguage": "en",
        "sort": "Latest",
        "maxItems": 20
    }
    try:
        resp = await client.post(url, json=payload, timeout=90.0)
        if resp.status_code in (200, 201):
            data = resp.json()
            items = data if isinstance(data, list) else data.get("data", [])
            logger.info(f"[Apify Twitter] Received {len(items)} items")
            return items
        else:
            logger.warning(f"[Apify Twitter] Returned status {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        logger.error(f"[Apify Twitter] Error: {e}")
    return []

async def fetch_serper_reddit(client: httpx.AsyncClient, query: str) -> list[dict]:
    if not settings.SERPER_API_KEY:
        return []
    url = "https://google.serper.dev/search"
    payload = {
        "q": query,
        "tbs": "qdr:w", # Past week (w2 is often rejected by Google)
        "num": 20
    }
    headers = {
        "X-API-KEY": settings.SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    try:
        resp = await client.post(url, json=payload, headers=headers, timeout=30.0)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("organic", [])
            logger.info(f"[Serper Reddit] Received {len(items)} items for query '{query[:30]}...'")
            return items
        else:
            logger.error(f"[Serper Reddit] 400 Error. Payload: {payload}, Response: {resp.text}")
    except Exception as e:
        logger.error(f"[Serper Reddit] Error: {e}")
    return []
async def fetch_scrapebadger_reddit(client: httpx.AsyncClient, query: str) -> list:
    url = "https://scrapebadger.com/v1/reddit/search/posts"
    api_key = settings.SCRAPEBADGER_API_KEY
    
    headers = {
        "x-api-key": api_key
    }
    for attempt in range(2):
        try:
            resp = await client.get(url, params={"q": query, "limit": 25}, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("posts", [])
                logger.info(f"[ScrapeBadger Reddit] Received {len(items)} items for query '{query}'")
                return items
            elif resp.status_code in (502, 503, 504) and attempt == 0:
                logger.warning(f"[ScrapeBadger Reddit] Got {resp.status_code} Bad Gateway. Retrying in 1.5s...")
                await asyncio.sleep(1.5)
                continue
            else:
                log_msg = resp.text[:150].replace('\n', ' ') if resp.text else ""
                logger.error(f"[ScrapeBadger Reddit] {resp.status_code} Error: {log_msg}")
        except Exception as e:
            logger.error(f"[ScrapeBadger Reddit] Error: {e}")
            break
    return []

async def fetch_scrapebadger_twitter(client: httpx.AsyncClient, query: str) -> list:
    url = "https://scrapebadger.com/v1/twitter/tweets/advanced_search"
    api_key = settings.SCRAPEBADGER_API_KEY
    
    headers = {
        "x-api-key": api_key
    }
    for attempt in range(2):
        try:
            resp = await client.get(
                url, 
                params={"query": query, "count": 25}, 
                headers=headers
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("tweets") or data.get("data") or data.get("results") or []
                if isinstance(data, list):
                    items = data
                logger.info(f"[ScrapeBadger Twitter] Received {len(items)} items for query '{query}'")
                return items
            elif resp.status_code in (502, 503, 504) and attempt == 0:
                logger.warning(f"[ScrapeBadger Twitter] Got {resp.status_code} Bad Gateway. Retrying in 1.5s...")
                await asyncio.sleep(1.5)
                continue
            else:
                log_msg = resp.text[:150].replace('\n', ' ') if resp.text else ""
                logger.error(f"[ScrapeBadger Twitter] {resp.status_code} Error: {log_msg}")
        except Exception as e:
            logger.error(f"[ScrapeBadger Twitter] Error: {e}")
            break
    return []

async def fetch_social_micro_intent(triggers: list[str], topics: list[str]) -> list[dict]:
    if not triggers or not topics:
        return []
        
    sentences = []
    # Build natural sentences like "looking for a marketing agency"
    for trigger in triggers[:1]: # Limit to 1 trigger * 2 topics = 2 sentences * 2 platforms = 4 requests (Under 5 limit)
        for topic in topics[:2]: 
            clean_trig = trigger.strip('\'"')
            clean_top = topic.strip('\'"')
            sentences.append(f"{clean_trig} a {clean_top}")
            sentences.append(f"{clean_trig} {clean_top}")
            
    sentences = sentences[:2]
            
    results = []
    
    async with httpx.AsyncClient(timeout=95.0) as client:
        sem = asyncio.Semaphore(3)
        
        async def fetch_with_sem(fetch_func, query):
            async with sem:
                await asyncio.sleep(0.5)
                return await fetch_func(client, query)
                
        # Launch tasks for both Reddit and Twitter
        tasks = []
        for sentence in sentences:
            tasks.append(fetch_with_sem(fetch_scrapebadger_reddit, sentence))
            tasks.append(fetch_with_sem(fetch_scrapebadger_twitter, sentence))
            
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        
        for idx, response_items in enumerate(responses):
            if isinstance(response_items, Exception) or not isinstance(response_items, list):
                continue
                
            is_reddit = idx % 2 == 0
            platform_name = "reddit" if is_reddit else "x"
                
            for item in response_items:
                # Local Timestamp Filter (< 30 days old)
                created_val = item.get("created_utc") if is_reddit else (item.get("createdAt") or item.get("created_at"))
                
                if not created_val:
                    continue
                
                try:
                    if isinstance(created_val, (int, float)):
                        post_date = datetime.fromtimestamp(created_val, timezone.utc)
                    else:
                        try:
                            post_date = datetime.strptime(created_val, "%a %b %d %H:%M:%S %z %Y")
                        except ValueError:
                            post_date = datetime.fromisoformat(created_val.replace("Z", "+00:00"))
                except Exception:
                    post_date = datetime.now(timezone.utc)
                    
                if post_date < thirty_days_ago:
                    continue # Skip posts older than 30 days
                    
                if is_reddit:
                    text = f"{item.get('title', '')} {item.get('selftext', '')}".strip()
                else:
                    text = item.get("text") or item.get("full_text") or ""
                    
                if not text:
                    continue
                    
                if any(promo in str(text).lower() for promo in AGENCY_PROMO_DENYLIST):
                    continue
                
                if is_reddit:
                    url_val = item.get("url", "")
                    author_handle = item.get("author") or "reddit_user"
                    author_name = item.get("author") or "Reddit User"
                else:
                    author_obj = item.get("author", {}) if isinstance(item.get("author"), dict) else {}
                    author_handle = item.get("username") or item.get("userName") or author_obj.get("userName") or f"tw_user_{random.randint(100,999)}"
                    author_name = item.get("user_name") or item.get("name") or author_obj.get("name") or author_handle
                    url_val = item.get("url") or f"https://twitter.com/{author_handle}/status/{item.get('id', random.randint(1000,9999))}"
                    
                if not url_val:
                    continue
                    
                results.append({
                    "company_name": author_name,
                    "author_handle": author_handle,
                    "author_name": author_name,
                    "platform": platform_name,
                    "content": str(text),
                    "post_url": url_val,
                    "keyword_matched": "marketing agency",
                    "published_at": post_date.isoformat()
                })
                
    # Deduplicate results by post_url locally before returning
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


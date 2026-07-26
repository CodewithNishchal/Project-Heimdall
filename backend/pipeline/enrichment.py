import asyncio
import json
import logging
import httpx
import urllib.parse
import re
from datetime import datetime, timezone, timedelta
from backend.config import settings
from dotenv import dotenv_values

logger = logging.getLogger("Enrichment")

def sanitize_url(url: str, platform: str) -> str | None:
    if not url:
        return None
        
    if platform == "X":
        match = re.search(r"(x\.com|twitter\.com)/[^/]+/status/\d+", url)
        return f"https://{match.group(0)}" if match else None
        
    elif platform == "LinkedIn":
        if "/posts/" in url or "/activity-" in url or "/feed/update/" in url:
            return url
        return None

    elif platform == "NewsAPI":
        return url if url.startswith("http") else None
        
    elif platform == "Reddit":
        return url if "/comments/" in url else None

    return url

SYSTEM_INSTRUCTION = """
You are an execution agent responsible for populating a B2B Lead Intelligence Dashboard.
You will be provided with an array of 5 target company objects at runtime, each containing { "company_name": "...", "domain": "..." } and their raw extracted signals.

Your task is to synthesize these signals into intent scores and construct a structured JSON output for each company.

### EXECUTION STEPS PER COMPANY

STEP 1: MULTI-SOCIAL SIGNAL SCRAPING (ScrapeBadger API)
From the provided signals, extract ONLY the TOP 2 MOST INTENT-DRIVEN posts per platform (LinkedIn, X, Reddit).
- MANDATORY URL FORMAT: `source_link` MUST be the full absolute URL starting with https:// (e.g., https://x.com/user/status/123, https://reddit.com/r/...). Do NOT use relative paths.

STEP 2: MEDIA & PRESS EXTRACTION (NewsAPI)
- Select up to 2 top news mentions from the provided news signals.
- MANDATORY URL FORMAT: `source_link` MUST be the direct canonical article URL.
- FALLBACK RULE: If no funding articles exist, set "funding_stage": "Bootstrapped / Undisclosed".

STEP 3: EXECUTIVE DISCOVERY (Serper API)
- Extract up to 3 executive names, titles, and LinkedIn profile links from the provided exec signals.

STEP 4: DUMMY DATA INJECTION (FOR APOLLO & PROSPEO EXCLUSIVE FIELDS)
Inject placeholders with explicit status tags for fields reserved for paid enrichment:
1. Executive Emails:
   - Generate pattern email: first.last@{company_domain}
   - Tag explicitly: email_status: "GENERATED"
2. Hiring & Revenue Velocity:
   - Set status: "High Velocity Growth" (if active posts/news exist) or "Steady Growth".
   - Tag explicitly: velocity_status: "MOCK_ESTIMATE"

STEP 5: INTENT SYNTHESIS & AI VERDICT
Synthesize all collected social posts and news articles into the final JSON output:
1. composite_intent_score: Numeric score (0–100) based on signal recency, density, and growth indicators.
2. ai_verdict: A concise 2-sentence pitch strategy. The first sentence MUST reference exact numbers from the data (e.g., "$187M funding", "$1B volume", "50 locations"). The second sentence must pitch a specific agency service (e.g., scale-up infrastructure, enterprise security, performance marketing) to support that exact metric.
3. Populate detected_signals (max 8 signals total per company across LinkedIn, X, Reddit, and Serper News) to feed directly into the EXTRACTION EVIDENCE LOG UI.

### CRITICAL SCHEMA RULES
1. 'funding_stage' MUST strictly be one of: ["Pre-Seed", "Seed", "Series A", "Series B", "Series C+", "Growth", "Private Equity", "Bootstrapped", "UNKNOWN"]. Do NOT put dollar amounts into 'funding_stage'.
2. If 'hiring_velocity' cannot be verified from live social/job signals, set 'hiring_velocity_tag' to "MOCK_ESTIMATE".

### LLM GROUNDING & GUARDRAILS
You are a strict data synthesizer. Base all fields EXCLUSIVELY on the provided raw JSON signals. 
- If no news or funding articles exist in the input, set 'funding_stage' to 'UNKNOWN'.
- Do NOT guess or assume 'Bootstrapped' if funding data is missing.
- Only mark verification_status as 'Verified' if supported by a direct quote or link.

---

### REQUIRED OUTPUT JSON SCHEMA

Return ONLY a valid JSON array of objects for the 5 target companies. Do not include prose explanations outside the JSON block.

[
  {
    "company_name": "String",
    "domain": "String",
    "contact_reliability_score": "80%",
    "trust_tier": "High Trust",
    "infographics": {
      "employee_count": "String (e.g., '51-200 employees (Est.)')",
      "funding_stage": "String (e.g., 'Series B / Seed')",
      "hiring_velocity": "String (e.g., 'High Velocity Growth')",
      "hiring_velocity_tag": "MOCK_ESTIMATE"
    },
    "composite_intent": {
      "score": 88,
      "freshness": "90% Fresh",
      "detected_signals": [
        {
          "platform": "LinkedIn | X | Reddit | Serper News",
          "category": "PARTNERSHIP INTEREST | PRODUCT LAUNCH | HIRING | MEDIA MENTION",
          "quote": "Verbatim quote or headline snippet",
          "source_link": "Direct post permalink URL",
          "recency": "UNKNOWN | RECENT | 2 days ago",
          "impact_score": "+12.5 pts",
          "verification_status": "Verified (100%)"
        }
      ]
    },
    "ai_verdict": "String summary of agency pitch strategy.",
    "key_contacts": [
      {
        "name": "String",
        "title": "String",
        "email": "string@domain.com",
        "email_status": "GENERATED",
        "linkedin_url": "URL if available"
      }
    ]
  }
]
"""

async def fetch_linkedin_slug(client: httpx.AsyncClient, company_name: str) -> str:
    clean_name = company_name.replace(" World", "").replace(" Inc", "").replace(" LLC", "").replace(" Inc.", "").strip()
    if not settings.SERPER_API_KEY: return clean_name.lower().replace(" ", "-")
    
    query = f'site:linkedin.com/company/ "{company_name}"'
    try:
        res = await client.post("https://google.serper.dev/search", headers={"X-API-KEY": settings.SERPER_API_KEY}, json={"q": query, "num": 3})
        for r in res.json().get("organic", []):
            link = r.get("link", "")
            if "linkedin.com/company/" in link:
                slug = link.split("linkedin.com/company/")[1].strip("/").split("/")[0]
                if clean_name.lower() in slug.lower() or company_name.lower() in link.lower():
                    return slug
    except Exception: pass
    
    # Fallback to a broader query if the first one failed
    query_2 = f'site:linkedin.com/company/ "{clean_name}"'
    try:
        res = await client.post("https://google.serper.dev/search", headers={"X-API-KEY": settings.SERPER_API_KEY}, json={"q": query_2, "num": 3})
        for r in res.json().get("organic", []):
            link = r.get("link", "")
            if "linkedin.com/company/" in link:
                slug = link.split("linkedin.com/company/")[1].strip("/").split("/")[0]
                return slug
    except Exception: pass

    return clean_name.lower().replace(" ", "-")

async def scrapebadger_get(client: httpx.AsyncClient, url: str, params: dict = None) -> httpx.Response | None:
    if not settings.SCRAPEBADGER_API_KEY: return None
    headers = {"x-api-key": settings.SCRAPEBADGER_API_KEY}
    for attempt in range(3):
        try:
            # Small pre-request delay to space out concurrent calls
            if attempt > 0:
                wait_time = 5 * (2 ** attempt)  # 10s, 20s
            else:
                await asyncio.sleep(0.5)  # 0.5s breathing room on first try
                wait_time = 0
            if wait_time:
                logger.info(f"ScrapeBadger rate-limit backoff: waiting {wait_time}s (attempt {attempt + 1}/3)")
                await asyncio.sleep(wait_time)
            res = await client.get(url, params=params, headers=headers)
            if res.status_code == 200:
                return res
            elif res.status_code in (429, 502, 503):
                continue
            else:
                break
        except Exception as e:
            if attempt == 2:
                logger.warning(f"ScrapeBadger request failed: {e}")
    return None



async def fetch_twitter_posts(client: httpx.AsyncClient, company_name: str, domain: str) -> list:
    if not settings.SCRAPEBADGER_API_KEY: return []
    
    clean_name = re.sub(r'\b(Inc|LLC|Corp|Corporation|Co|World)\b\.?', '', company_name, flags=re.IGNORECASE).strip()
    c_name_no_spaces = clean_name.replace(" ", "")
    
    name_variants = [f'"{clean_name}"']
    if c_name_no_spaces != clean_name:
        name_variants.append(f'"{c_name_no_spaces}"')
        
    name_query = " OR ".join(name_variants)
    
    if domain:
        query = f'"{domain}" OR ({name_query})'
    else:
        query = name_query
    
    try:
        res = await scrapebadger_get(client, "https://scrapebadger.com/v1/twitter/tweets/advanced_search", params={"query": query, "count": 20})
        if res and res.status_code == 200:
            posts = []
            json_res = res.json()
            raw_posts = json_res.get("tweets") or json_res.get("data") or json_res.get("results") or []
            if isinstance(json_res, list):
                raw_posts = json_res
                
            for t in raw_posts[:5]:
                url = t.get("url") or t.get("link", "")
                if not url and t.get("id"):
                    url = f"https://x.com/user/status/{t.get('id')}"
                safe_url = sanitize_url(url, "X") or url
                t["url"] = safe_url
                posts.append(t)
            return posts
    except Exception as e:
        logger.warning(f"Failed to fetch Twitter posts: {e}")
    return []

async def fetch_reddit_posts(client: httpx.AsyncClient, company_name: str, domain: str = "") -> list:
    if not settings.SCRAPEBADGER_API_KEY: 
        return []
    
    # 1. Clean corporate suffixes using regex word boundaries
    clean_name = re.sub(r'\b(Inc|LLC|Corp|Corporation|Co|World)\b\.?', '', company_name, flags=re.IGNORECASE).strip()
    c_name_no_spaces = clean_name.replace(" ", "")
    
    # 2. Build a flexible query matching domain OR brand variants
    name_variants = [f'"{clean_name}"']
    if c_name_no_spaces != clean_name:
        name_variants.append(f'"{c_name_no_spaces}"')
        
    name_query = " OR ".join(name_variants)
    
    if domain:
        query = f'"{domain}" OR ({name_query})'
    else:
        query = name_query

    try:
        # 3. Query ScrapeBadger Reddit Search
        res = await scrapebadger_get(
            client, 
            "https://scrapebadger.com/v1/reddit/search/posts", 
            params={"q": query, "sort": "relevance"}
        )
        
        if res and res.status_code == 200:
            posts = []
            json_res = res.json()
            
            # FIX: Support both 'posts' (Reddit standard) and 'data' (fallback) keys
            raw_posts = json_res.get("posts") or json_res.get("data") or []
            
            import datetime
            for p in raw_posts[:5]:
                url = sanitize_url(p.get("url", ""), "Reddit") or p.get("url", "")
                if url:
                    p["url"] = url
                    if "created_utc" in p:
                        try:
                            p["date"] = datetime.datetime.fromtimestamp(p["created_utc"], datetime.timezone.utc).isoformat()
                        except Exception:
                            pass
                    posts.append(p)
            return posts

    except Exception as e:
        logger.error(f"Error extracting metadata for domain {domain}: {e}")
        
    return []

async def fetch_news_mentions(client: httpx.AsyncClient, company_name: str, domain: str) -> list:
    if not settings.SERPER_API_KEY: return []
    # Serper (Google) uses space for AND, so we format accordingly
    query = f'("{company_name}" OR "{domain}") ("funding" OR "raised" OR "Series")'
    try:
        res = await client.post(
            "https://google.serper.dev/news",
            headers={"X-API-KEY": settings.SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": 5}
        )
        if res.status_code == 200:
            articles = []
            for a in res.json().get("news", []):
                url = sanitize_url(a.get("link", ""), "NewsAPI")
                if url:
                    a["url"] = url
                    articles.append(a)
            return articles
    except Exception: pass
    return []

async def fetch_executives(client: httpx.AsyncClient, company_name: str, domain: str) -> list:
    if not settings.SERPER_API_KEY: return []
    query = f'site:linkedin.com/in "{company_name}" ("CEO" OR "Founder" OR "VP Marketing" OR "CMO" OR "Director")'
    c_lower = company_name.lower()
    try:
        res = await client.post("https://google.serper.dev/search", headers={"X-API-KEY": settings.SERPER_API_KEY}, json={"q": query, "num": 10})
        execs = []
        for r in res.json().get("organic", []):
            text = (r.get("title", "") + " " + r.get("snippet", "")).lower()
            # Strict boundary checking prevents "Project Read AI" from matching "Read AI"
            if domain in text or f"at {c_lower}" in text or f"- {c_lower}" in text or f"| {c_lower}" in text or f" {c_lower} " in text:
                execs.append(r)
            if len(execs) == 3:
                break
        
        # Fallback if strict filtering drops everyone
        if not execs:
            return res.json().get("organic", [])[:3]
        return execs
    except Exception: pass
    return []

async def gather_company_signals(companies: list[dict]) -> list[dict]:
    logger.info(f"Gathering Multi-Platform Signals for {len(companies)} companies...")
    
    import dns.resolver
    
    enriched_data = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        for comp in companies:
            c_name = comp["company_name"]
            domain = comp.get("domain", "")
            
            # Discovery: if no domain provided, use Serper to find official site
            if not domain:
                if settings.SERPER_API_KEY:
                    query = f'"{c_name}" official site'
                    try:
                        res = await client.post("https://google.serper.dev/search", headers={"X-API-KEY": settings.SERPER_API_KEY}, json={"q": query, "num": 3})
                        for r in res.json().get("organic", []):
                            link = r.get("link", "")
                            if "linkedin.com" not in link and "wikipedia.org" not in link and "bloomberg.com" not in link:
                                domain = urllib.parse.urlparse(link).netloc.replace("www.", "")
                                break
                    except Exception: pass
                if not domain:
                    domain = f"{c_name.lower().replace(' ', '')}.com"
                    
            # Validation: MX Record Check
            def check_mx():
                try:
                    return bool(dns.resolver.resolve(domain, 'MX'))
                except Exception:
                    return False
            is_valid = await asyncio.to_thread(check_mx)
            if not is_valid:
                logger.warning(f"Domain {domain} failed MX validation. Proceeding with caution.")
            
            slug = await fetch_linkedin_slug(client, c_name)
            tw_posts = await fetch_twitter_posts(client, c_name, domain)
            rd_posts = await fetch_reddit_posts(client, c_name, domain)
            news = await fetch_news_mentions(client, c_name, domain)
            execs = await fetch_executives(client, c_name, domain)
            
            enriched_data.append({
                "company_name": c_name,
                "domain": domain,
                "mx_valid": is_valid,
                "signals": {
                    "linkedin_profile": {}, # Deprecated ScrapeBadger integration
                    "linkedin_posts": [],   # Deprecated ScrapeBadger integration
                    "twitter_posts": tw_posts,
                    "reddit_posts": rd_posts,
                    "news_articles": news,
                    "executives": execs
                }
            })
    return enriched_data

async def synthesize_intent(enriched_data: list[dict]) -> list[dict]:
    env_vars = dotenv_values("backend/.env")
    openrouter_key = env_vars.get("OPENROUTER_API_KEY") or getattr(settings, "OPENROUTER_API_KEY", "")

    if not openrouter_key:
        logger.error("OPENROUTER_API_KEY is missing. Cannot run synthesis.")
        return []

    prompt = f"Here is the raw scraped data for the {len(enriched_data)} companies. Analyze it strictly according to the system instructions and output the JSON array.\n\n"
    prompt += json.dumps(enriched_data, indent=2)

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "HTTP-Referer": "https://heimdall.app",
        "X-Title": "Heimdall Lead Intel",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            
            cleaned_content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned_content)
    except Exception as e:
        logger.error(f"Failed to generate composite intent with OpenRouter LLM: {e}")
        return []

async def execute_enrichment_pipeline(companies: list[dict]) -> list[dict]:
    enriched_data = await gather_company_signals(companies)
    return await synthesize_intent(enriched_data)

# Domains to ignore when looking for the company's canonical website
EXCLUDED_DOMAINS = {
    "linkedin.com", "facebook.com", "twitter.com", "x.com", "wikipedia.org",
    "crunchbase.com", "youtube.com", "instagram.com", "pitchbook.com",
    "g2.com", "capterra.com", "glassdoor.com", "bloomberg.com", "ycombinator.com"
}

async def resolve_domain_via_serper(company_name: str, serper_api_key: str, phase1_estimated_domain: str = "") -> str:
    """
    Resolves official company domain using Gemini Phase 1 output with Serper API fallback.
    Prevents false positives like resolving 'Clay' -> 'clayton.k12.ga.us'.
    """
    # 1. Clean and check Phase 1 estimated domain first
    if phase1_estimated_domain:
        clean_est = phase1_estimated_domain.lower().replace("https://", "").replace("http://", "").replace("www.", "").strip("/")
        if "." in clean_est and not any(ext in clean_est for ext in EXCLUDED_DOMAINS):
            return clean_est

    if not serper_api_key:
        return f"{company_name.lower().replace(' ', '')}.com"

    # 2. Query Serper for entity-disambiguated search
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": serper_api_key, "Content-Type": "application/json"}
    
    # Adding context keywords forces Google to rank the B2B company above schools/places
    query = f'"{company_name}" official website software company'
    payload = {"q": query, "num": 5}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            if res.status_code == 200:
                data = res.json()
                
                # A. Check Google Knowledge Graph first (100% accurate if present)
                kg = data.get("knowledgeGraph", {})
                kg_site = kg.get("website") or kg.get("attributes", {}).get("Website")
                if kg_site:
                    import urllib.parse
                    domain = urllib.parse.urlparse(kg_site if kg_site.startswith("http") else f"https://{kg_site}").netloc
                    return domain.replace("www.", "").lower()

                # B. Fallback to First Organic Result ignoring social/aggregator sites
                for item in data.get("organic", []):
                    link = item.get("link", "")
                    import urllib.parse
                    domain = urllib.parse.urlparse(link).netloc.replace("www.", "").lower()

                    if domain and not any(excluded in domain for excluded in EXCLUDED_DOMAINS):
                        return domain
                        
    except Exception as e:
        print(f"⚠️ Serper domain resolution fallback triggered for {company_name}: {e}")

    # Safety fallback
    return f"{company_name.lower().replace(' ', '')}.com"

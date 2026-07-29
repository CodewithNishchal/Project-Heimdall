"""
Phase 1 & 2 — Autonomous Company Discovery + Domain Resolution.

Replaces hardcoded company lists with three concurrent keyword sweeps
that return company names as OUTPUT, not input.
"""
import httpx
import asyncio
import logging
import pandas as pd
from jobspy import scrape_jobs
from backend.config import settings

logger = logging.getLogger("Discovery")

def validate_relevance(text: str) -> bool:
    """
    Post-Hit Relevance Filter using Extraction Keywords.
    """
    from backend.config_manager import load_intent_config
    config = load_intent_config()
    extraction_keywords = config.get("extraction_keywords", [
        "PPC", "local SEO", "fractional CMO", "marketing agency", "lead generation"
    ])
    text_lower = text.lower()
    for kw in extraction_keywords:
        if kw.lower() in text_lower:
            return True
    return False


# ---------------------------------------------------------------------------
# spaCy model — loaded once at module level for ORG entity extraction
# ---------------------------------------------------------------------------
try:
    import spacy
    _nlp = spacy.load("en_core_web_sm")
except Exception:
    _nlp = None
    logger.warning("spaCy model not loaded. Run: python -m spacy download en_core_web_sm")


# ======================================================================
# Phase 1 — Autonomous keyword-based company discovery
# ======================================================================

STAFFING_BLACKLIST = ["staffing", "recruiting", "talent", "manpower", "adecco"]


def discover_companies_from_jobspy() -> set[str]:
    """
    Phase 1 — JobSpy sweep. Queries role keywords instead of company names.
    Parses the company column from the returned DataFrame.
    Filters out staffing agencies.
    """
    try:
        from backend.config_manager import load_intent_config
        config = load_intent_config()
        # Default niche roles if config is missing
        job_roles = config.get("jobspy_search_term", "CMO, VP of Marketing, Director of Marketing, Head of Growth")
        if isinstance(job_roles, str):
            job_roles = [r.strip() for r in job_roles.split(",") if r.strip()]
        if not job_roles:
            job_roles = ["CMO", "VP of Marketing", "Director of Marketing", "Head of Growth"]

        companies = set()
        for role in job_roles:
            logger.info(f"[JobSpy] Sweeping for niche role: {role}")
            jobs_df = scrape_jobs(
                site_name=["linkedin", "indeed"],
                search_term=role,
                location="USA",
                results_wanted=10,
                hours_old=720,
                country_indeed="USA"
            )
            if jobs_df.empty:
                continue

            for _, row in jobs_df.iterrows():
                name = str(row.get("company", "")).strip()
                if not name or name.lower() == "nan":
                    continue
                
                # Sanitize company name
                clean_name = name.lower().replace(".com", "").replace(".co", "").replace(".io", "").strip().title()

                # Filter staffing agencies
                if any(bl in clean_name.lower() for bl in STAFFING_BLACKLIST):
                    continue
                companies.add(clean_name)

        logger.info(f"[JobSpy] Discovered {len(companies)} companies from niche role sweeps")
        return companies
    except Exception as e:
        logger.error(f"[JobSpy] Discovery sweep failed: {e}")
        return set()


def extract_orgs_from_articles(articles: list[dict]) -> set[str]:
    """
    Uses spaCy NER to extract ORG entities from article titles + descriptions.
    """
    if not _nlp:
        return set()
    orgs = set()
    false_positives = ["news", "inc", "inc.", "llc", "llc.", "ltd", "ltd.", "corp", "corporation"]
    for article in articles:
        text = (article.get("title", "") or "") + " " + (article.get("description", "") or "")
        doc = _nlp(text)
        for ent in doc.ents:
            clean_ent = ent.text.strip()
            if ent.label_ == "ORG" and len(clean_ent) > 3:
                # Reject if looks like a domain name, purely lowercase, or is a common false positive
                if "." in clean_ent or clean_ent.islower() or clean_ent.lower() in false_positives:
                    continue
                orgs.add(clean_ent)
    return orgs


async def discover_companies_from_news() -> set[str]:
    """
    Phase 1 — NewsAPI sweep. Queries intent phrases, extracts company names
    using LLM extraction pass per hit.
    """
    api_key = settings.NEWS_API_KEY
    if not api_key or api_key == "mock_key_if_empty":
        return set()

    from datetime import datetime, timezone, timedelta
    one_month_ago = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

    from backend.config_manager import load_intent_config
    config = load_intent_config()
    queries = config.get("news_queries", [
        '("expanding to new locations" OR "opening new locations" OR "franchise expansion" OR "multi-unit deal") AND ("marketing" OR "retail" OR "services") -billion -conglomerate -corp'
    ])
    all_articles: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for q in queries:
                import urllib.parse
                if len(urllib.parse.quote(q)) > 500:
                    q = q[:200]  # rough truncation to stay under 500 chars when encoded
                res = await client.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q": q,
                        "apiKey": api_key,
                        "language": "en",
                        "sortBy": "publishedAt",
                        "from": one_month_ago,
                        "pageSize": 5,
                    },
                )
                data = res.json()
                if data.get("status") == "ok" and data.get("articles"):
                    all_articles.extend(data["articles"])
    except Exception as e:
        logger.error(f"[NewsAPI] Discovery sweep failed: {e}")

    # Zero-cost extraction using local spaCy NER
    orgs = set()
    for art in all_articles:
        text = (art.get("title", "") or "") + " " + (art.get("description", "") or "") + " " + (art.get("content", "") or "")
        if validate_relevance(text):
            extracted = extract_orgs_from_articles([art])
            orgs.update(extracted)

    logger.info(f"[NewsAPI] Discovered {len(orgs)} companies from news articles")
    return orgs


async def discover_companies_from_serper() -> set[str]:
    """
    [Deprecated] Formerly used Serper + ScrapeBadger to search LinkedIn posts.
    Replaced by Apify HarvestAPI ('harvestapi~linkedin-company-posts') in enrichment.
    """
    return set()


async def discover_companies_from_yelp() -> set[str]:
    """
    Phase 1 — Yelp discovery sweep via Google Serper.
    Finds local business and agency prospects listed on Yelp matching high intent signals.
    """
    api_key = settings.SERPER_API_KEY
    if not api_key or api_key == "mock_key_if_empty":
        return set()

    yelp_queries = [
        'site:yelp.com/biz "website" OR "redesign" OR "new location" OR "expanding"',
        'site:yelp.com/biz "under new management" OR "rebrand"'
    ]

    companies = set()
    async with httpx.AsyncClient(timeout=10.0) as client:
        for query in yelp_queries:
            try:
                res = await client.post(
                    "https://google.serper.dev/search",
                    headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                    json={"q": query, "num": 10},
                )
                data = res.json()
                for result in data.get("organic", []):
                    title = result.get("title", "")
                    # Strip Yelp suffix: "BUSINESS NAME - City, ST - Yelp"
                    name = title.split(" - ")[0].replace("- Yelp", "").strip()
                    if name and len(name) > 2 and not name.lower().startswith("the best"):
                        companies.add(name)
            except Exception as e:
                logger.error(f"[Yelp] Discovery sweep failed for query '{query}': {e}")

    logger.info(f"[Yelp] Discovered {len(companies)} companies from Yelp listings")
    return companies


# ======================================================================
# Phase 2 — Domain Resolution via Clearbit Autocomplete
# ======================================================================

KNOWN_FIRMOGRAPHICS = {
    "goldmansachs.com": {"employee_count": 45000, "industry": "Financial Services", "funding_stage": "Public"},
    "roku.com": {"employee_count": 3800, "industry": "Technology", "funding_stage": "Public"},
    "venturetofunds.com": {"employee_count": 45, "industry": "Venture Capital", "funding_stage": "Seed"},
}

def resolve_domain(company_name: str) -> tuple[str | None, dict]:
    """
    Returns (domain, firmographics) from Clearbit Autocomplete. No API key needed.
    Falls back to constructing and verifying a domain if Clearbit returns nothing.
    """
    slug = company_name.lower().replace(" ", "").replace(".com", "")
    fallback = f"{slug}.com"
    
    if fallback in KNOWN_FIRMOGRAPHICS:
        return fallback, KNOWN_FIRMOGRAPHICS[fallback]

    try:
        resp = httpx.get(
            "https://autocomplete.clearbit.com/v1/companies/suggest",
            params={"query": company_name},
            timeout=5.0,
        )
        results = resp.json()
        
        # Retry with " Inc" if no results and name is short
        if not results and len(company_name) < 15 and "inc" not in company_name.lower():
            resp = httpx.get(
                "https://autocomplete.clearbit.com/v1/companies/suggest",
                params={"query": f"{company_name} Inc"},
                timeout=5.0,
            )
            results = resp.json()

        if results:
            first = results[0]
            domain = first.get("domain")
            if domain:
                return domain, {
                    "employee_count": first.get("employees"),
                    "industry": first.get("type", "Unknown"),
                }
    except Exception:
        pass

    # Wikipedia Fallback for firmographics
    import re
    firmographics = {}
    try:
        wiki_resp = httpx.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{company_name.replace(' ', '_')}",
            timeout=3.0,
        )
        if wiki_resp.status_code == 200:
            extract = wiki_resp.json().get("extract", "")
            emp_match = re.search(r"([0-9,]+)\s+employees", extract)
            if emp_match:
                emp_count = int(emp_match.group(1).replace(",", ""))
                firmographics["employee_count"] = emp_count
    except Exception:
        pass

    # Serper LinkedIn Fallback for firmographics if still missing
    if "employee_count" not in firmographics:
        from backend.config import settings
        api_key = settings.SERPER_API_KEY
        if api_key and api_key != "mock_key_if_empty":
            try:
                with httpx.Client(timeout=5.0) as client:
                    res = client.post(
                        "https://google.serper.dev/search",
                        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                        json={"q": f'site:linkedin.com/company "{company_name}"', "num": 3},
                    )
                    data = res.json()
                    for result in data.get("organic", []):
                        snippet = result.get("snippet", "")
                        
                        range_match = re.search(r"(\d+)-(\d+)\s+employees", snippet, re.IGNORECASE)
                        emp_match = re.search(r"([\d,]+)\+?\s*employees", snippet, re.IGNORECASE)
                        
                        if range_match:
                            firmographics["employee_count"] = int(range_match.group(2).replace(",", ""))
                            break
                        elif emp_match:
                            firmographics["employee_count"] = int(emp_match.group(1).replace(",", ""))
                            break
            except Exception:
                pass

    try:
        r = httpx.head(f"https://{fallback}", timeout=4.0, follow_redirects=True)
        if r.status_code < 400:
            return fallback, firmographics
    except Exception:
        pass

    return None, {}


async def discover_companies_from_exa() -> list[dict]:
    """
    Phase 1 — Exa AI Neural Search Sweep.
    Executes a high-intent neural search query to fetch up to 100 raw company snippets,
    titles, summaries, and URLs for B2B intent leads.
    """
    import os
    exa_api_key = getattr(settings, "EXA_API_KEY", None) or os.getenv("EXA_API_KEY")
    if not exa_api_key or exa_api_key == "mock_key_if_empty":
        logger.warning("[Exa AI] API key missing, returning empty discovery list")
        return []

    url = "https://api.exa.ai/search"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": exa_api_key
    }
    
    from backend.config_manager import load_intent_config
    config = load_intent_config()
    default_query = "multi-location franchise, healthcare, home services, or B2B companies in the US that recently opened a new location, expanded operations, or scaled revenue to $5M-$20M without a listed in-house marketing director"
    query = config.get("exa_query", default_query)

    payload = {
        "query": query,
        "type": "neural",
        "useAutoprompt": False,
        "category": "company",
        "excludeDomains": ["clutch.co", "upcity.com", "designrush.com", "goodfirms.co", "42web.io", "byethost7.com", "zya.me"],
        "numResults": 100,
        "contents": {
            "text": True,
            "summary": True
        }
    }

    results = []
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            if res.status_code == 200:
                data = res.json()
                raw_items = data.get("results", [])
                logger.info(f"[Exa AI Discovery] Successfully fetched {len(raw_items)} neural search results")
                for r in raw_items:
                    text_snippet = r.get("text", "")
                    title = r.get("title", "")
                    summary = r.get("summary", "")
                    
                    extracted_names = list(extract_orgs_from_articles([{"title": title, "description": summary}]))
                    comp_name = extracted_names[0] if extracted_names else title.split("|")[0].split("-")[0].strip()

                    results.append({
                        "company_name": comp_name,
                        "title": title,
                        "url": r.get("url", ""),
                        "summary": summary,
                        "text_snippet": text_snippet[:600] if text_snippet else ""
                    })
    except Exception as e:
        logger.error(f"[Exa AI Discovery] Sweep failed: {e}")

    return results


# ======================================================================
# Unified autonomous discovery pipeline
# ======================================================================

async def run_autonomous_discovery() -> list[dict]:
    """
    Phase 1 — Runs Exa AI Neural Discovery and returns candidate context objects
    (including title, url, summary, text_snippet) ready for Gemini Phase 1 Top 5 Selection.
    """
    exa_results = await discover_companies_from_exa()
    logger.info(f"[Discovery] Total candidate context objects fetched via Exa AI: {len(exa_results)}")
    return exa_results


# ======================================================================
# Original per-company discovery functions (still used by orchestrator)
# ======================================================================

async def fetch_news_signals(company_name: str) -> list[dict]:
    """
    Scrapes the web for recent PR, funding, and growth signals using Serper Google News.
    """
    logger.info(f"[Serper News] Initiating live web search for: {company_name}")
    api_key = settings.SERPER_API_KEY
    if not api_key or api_key == "mock_key_if_empty":
        return []
        
    url = "https://google.serper.dev/news"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    
    # Target funding, expansion, and corporate milestones explicitly
    query = f'"{company_name}" (funding OR raised OR valuation OR ARR OR launch)'
    payload = {"q": query, "num": 5}
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            if res.status_code == 200:
                articles = res.json().get("news", [])
                signals = []
                for a in articles:
                    title = a.get("title") or ""
                    snippet = a.get("snippet") or ""
                    date = a.get("date") or "Unknown Date"
                    link = a.get("link") or ""
                    
                    text = f"Title: {title}\nDate: {date}\nURL: {link}\nSnippet: {snippet}"
                    signals.append({
                        "company_name": company_name,
                        "domain": "derived_from_news.com",
                        "raw_text": text,
                        "source_api": "SerperNews",
                        "extracted_url": link,
                        "url": link
                    })
                return signals
    except Exception as e:
        logger.error(f"[Serper News] Search failed for {company_name}: {e}")
    return []


def extract_key_sentences(text: str, max_sentences: int = 2) -> str:
    """
    Phase 5.5 — Local extractive summarisation.
    Takes the first N sentences containing an intent keyword.
    Costs zero tokens. Good enough for funding/hiring signals.
    """
    from backend.config_manager import load_intent_config
    config = load_intent_config()
    sentences = text.split(". ")
    keywords = config.get("extraction_keywords", [
        "raised", "funding", "hired", "expanded", "launched", "SDR",
        "hiring", "growth", "series", "seed", "round"
    ])
    relevant = [s for s in sentences if any(k.lower() in s.lower() for k in keywords)]
    return ". ".join(relevant[:max_sentences])


async def fetch_job_signals(company_name: str) -> list[dict]:
    """
    Uses python-jobspy to scrape live SDR/Sales jobs for the given company
    across LinkedIn and Indeed.
    """
    try:
        from backend.config_manager import load_intent_config
        config = load_intent_config()
        search_term_base = config.get("jobspy_search_term", "Sales Development Representative")
        
        jobs_df = await asyncio.to_thread(
            scrape_jobs,
            site_name=["linkedin", "indeed"],
            search_term=f"{search_term_base} {company_name}",
            location="USA",
            results_wanted=3,
            hours_old=720,
            country_indeed="USA",
        )

        signals = []
        if jobs_df.empty:
            return signals

        company_lower = company_name.lower()

        for index, row in jobs_df.iterrows():
            job_company = str(row.get("company", "")).lower()

            if company_lower not in job_company:
                continue

            title = str(row.get("title", "Unknown Role"))
            raw_desc = row.get("description", "")
            description = str(raw_desc) if pd.notna(raw_desc) else ""
            url = str(row.get("job_url", ""))
            date_posted = str(row.get("date_posted", "Unknown Date"))

            raw_text = f"Job Title: {title}\nDate: {date_posted}\nURL: {url}\n\nDescription:\n{description[:800]}..."
            signals.append(
                {
                    "company_name": company_name,
                    "domain": "derived_or_unknown.com",
                    "raw_text": raw_text,
                    "source_api": "JobSpy",
                    "extracted_url": url,
                }
            )

        return signals

    except Exception as e:
        logger.error(f"[JobSpy Error] Failed to scrape jobs for {company_name}: {e}")
        return []


async def fetch_public_intent_signals(query: str) -> list[dict]:
    """
    Ingests initial web signals from public data sources (now using JobSpy).
    """
    # Fetch live jobs and news concurrently
    live_signals, news_signals = await asyncio.gather(
        fetch_job_signals(query), fetch_news_signals(query)
    )

    combined = live_signals + news_signals
    if combined:
        return combined

    return []

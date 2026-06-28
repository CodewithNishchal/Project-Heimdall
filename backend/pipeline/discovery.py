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
        jobs_df = scrape_jobs(
            site_name=["linkedin", "indeed"],
            search_term="Sales Development Representative",
            location="USA",
            results_wanted=15,
            hours_old=720,
            country_indeed="USA"
        )
        if jobs_df.empty:
            return set()

        companies = set()
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

        logger.info(f"[JobSpy] Discovered {len(companies)} companies from role-keyword sweep")
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
    from article titles using spaCy ORG entity recogniser.
    """
    api_key = settings.NEWS_API_KEY
    if not api_key or api_key == "mock_key_if_empty":
        return set()

    queries = [
        "SaaS startup raises funding",
        "B2B seed round 2026",
        "series A funding startup",
        "startup hiring SDR sales",
    ]
    all_articles: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for q in queries:
                res = await client.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q": q,
                        "apiKey": api_key,
                        "language": "en",
                        "sortBy": "publishedAt",
                        "pageSize": 5,
                    },
                )
                data = res.json()
                if data.get("status") == "ok" and data.get("articles"):
                    all_articles.extend(data["articles"])
    except Exception as e:
        logger.error(f"[NewsAPI] Discovery sweep failed: {e}")

    orgs = extract_orgs_from_articles(all_articles)
    logger.info(f"[NewsAPI] Discovered {len(orgs)} ORG entities from news articles")
    return orgs


async def discover_companies_from_serper() -> set[str]:
    """
    Phase 1 — Serper sweep. Searches LinkedIn for companies hiring SDRs.
    Strips '| LinkedIn' / '- LinkedIn' suffix from result titles.
    """
    api_key = settings.SERPER_API_KEY
    if not api_key or api_key == "mock_key_if_empty":
        return set()

    companies = set()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                json={
                    "q": 'site:linkedin.com/company "hiring SDR" OR "hiring BDR"',
                    "num": 10,
                },
            )
            data = res.json()
            for result in data.get("organic", []):
                title = result.get("title", "")
                name = (
                    title.replace("| LinkedIn", "")
                    .replace("- LinkedIn", "")
                    .strip()
                )
                if name and len(name) > 2:
                    companies.add(name)
    except Exception as e:
        logger.error(f"[Serper] Discovery sweep failed: {e}")

    logger.info(f"[Serper] Discovered {len(companies)} companies from LinkedIn search")
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


# ======================================================================
# Unified autonomous discovery pipeline
# ======================================================================

async def run_autonomous_discovery() -> list[tuple[str, str, dict]]:
    """
    Runs all three discovery sweeps concurrently, deduplicates,
    resolves domains, and checks 7-day cache.
    Returns list of (company_name, domain, firmographics) ready for scoring.
    """
    from backend.pipeline.filter_funnel import check_recent_cache

    # Run JobSpy in a thread (it's sync), NewsAPI + Serper are async
    jobspy_companies = await asyncio.to_thread(discover_companies_from_jobspy)
    news_companies, serper_companies = await asyncio.gather(
        discover_companies_from_news(),
        discover_companies_from_serper(),
    )

    # Union + dedup
    all_companies = jobspy_companies | news_companies | serper_companies
    logger.info(f"[Discovery] Total unique companies discovered: {len(all_companies)}")

    # Resolve domains and filter cached
    async def _resolve_single(name):
        domain, firms = await asyncio.to_thread(resolve_domain, name)
        return name, domain, firms

    results = await asyncio.gather(*[_resolve_single(n) for n in all_companies])
    resolved = [(n, d, f) for n, d, f in results if d and not check_recent_cache(d)]

    logger.info(f"[Discovery] {len(resolved)} companies ready for pipeline processing")
    return resolved


# ======================================================================
# Original per-company discovery functions (still used by orchestrator)
# ======================================================================

async def fetch_news_signals(company_name: str) -> list[dict]:
    """
    Scrapes the web for recent PR, funding, and growth signals using NewsAPI.
    """
    logger.info(f"[NewsAPI] Initiating live web search for: {company_name}")
    api_key = settings.NEWS_API_KEY
    if not api_key or api_key == "mock_key_if_empty":
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
                    "pageSize": 5,
                },
            )
            data = res.json()
            if data.get("status") == "ok" and data.get("articles"):
                signals = []
                company_variants = list(
                    set([company_name, company_name.capitalize(), company_name.upper()])
                )

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
                        signals.append(
                            {
                                "company_name": company_name,
                                "domain": "derived_from_news.com",
                                "raw_text": text,
                                "source_api": "NewsAPI",
                                "extracted_url": art.get("url", ""),
                            }
                        )
                return signals
    except Exception as e:
        logger.error(f"[NewsAPI Error] {e}")
    return []


def extract_key_sentences(text: str, max_sentences: int = 2) -> str:
    """
    Phase 5.5 — Local extractive summarisation.
    Takes the first N sentences containing an intent keyword.
    Costs zero tokens. Good enough for funding/hiring signals.
    """
    sentences = text.split(". ")
    keywords = ["raised", "funding", "hired", "expanded", "launched", "SDR",
                 "hiring", "growth", "series", "seed", "round"]
    relevant = [s for s in sentences if any(k.lower() in s.lower() for k in keywords)]
    return ". ".join(relevant[:max_sentences])


async def fetch_job_signals(company_name: str) -> list[dict]:
    """
    Uses python-jobspy to scrape live SDR/Sales jobs for the given company
    across LinkedIn and Indeed.
    """
    try:
        jobs_df = await asyncio.to_thread(
            scrape_jobs,
            site_name=["linkedin", "indeed"],
            search_term=f"Sales Development Representative {company_name}",
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

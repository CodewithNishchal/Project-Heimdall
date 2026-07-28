"""
Pipeline Orchestrator — Phases 1-6 unified execution engine.

run_pipeline_for_company() — single company: Discovery → ICP Gate → Scoring → DNS → Contacts → Persist
run_batch_pipeline()       — autonomous: Discovery sweeps → iterate each company through the above
"""
import uuid
import json
import logging
import time
import asyncio
from datetime import datetime, timezone

from backend.pipeline.discovery import (
    fetch_public_intent_signals,
    resolve_domain,
    run_autonomous_discovery,
)

from backend.pipeline.dns_audit import audit_domain_email_infrastructure
from backend.pipeline.filter_funnel import check_recent_cache
from backend.pipeline.contact_extractor import extract_contacts
from backend.models import LeadSnapshot
from backend.database import SessionLocal
from backend.config import settings

logger = logging.getLogger("PipelineOrchestrator")


async def run_pipeline_for_company(
    company_name: str,
    domain: str | None = None,
    firmographics: dict | None = None,
    pre_fetched_signals: list[dict] | None = None,
) -> dict:
    """
    Main orchestration sequence for Heimdall.
    Executes: Domain Resolution → ICP Gate → Discovery → Scoring → DNS Audit → Contacts → DB Write.
    """
    # Phase 2: Domain resolution (use provided or resolve via Clearbit)
    if not domain:
        domain, firmographics = resolve_domain(company_name)
    if not domain:
        logger.info(f"Skipping {company_name} — domain unresolved")
        return {"status": "skipped", "reason": "domain_unresolved"}

    if firmographics is None:
        firmographics = {}

    # Cache Check
    if check_recent_cache(domain):
        logger.info(f"Skipping {company_name} — recently cached.")
        return {"status": "skipped", "reason": "recently_cached"}

    logger.info(f"Starting pipeline execution for {company_name} ({domain})")

    # Clean up firmographics defaults to not mask nulls
    if "employee_count" not in firmographics:
        firmographics["employee_count"] = None
    if "industry" not in firmographics or not firmographics["industry"]:
        firmographics["industry"] = "Unknown"
    if "funding_stage" not in firmographics or not firmographics["funding_stage"]:
        firmographics["funding_stage"] = "Unknown"

    # Phase 3: ICP Gatekeeper Check (before any LLM call)
    from backend.pipeline.icp_filter import apply_icp_filters

    dummy_score, icp_fit_label = apply_icp_filters(
        base_score=50,
        employee_count=firmographics.get("employee_count"),
        funding_stage=firmographics.get("funding_stage"),
        industry=firmographics.get("industry", "Unknown"),
    )

    if icp_fit_label == "Poor":
        logger.info(f"Short-circuiting {company_name} due to Poor ICP fit.")
        lead_id = str(uuid.uuid4())
        icp_reason = _get_icp_rejection_reason(firmographics)
        
        # Fetch raw signals to populate evidence log without using Gemini
        if pre_fetched_signals is not None:
            raw_signals = pre_fetched_signals
        else:
            raw_signals = await fetch_public_intent_signals(company_name)
        fallback_signals = []
        import re
        for sig in raw_signals:
            raw_t = sig.get("raw_text", "")
            if not raw_t:
                continue
            url_match = re.search(r"URL:\s*(https?://[^\s]+)", raw_t)
            date_match = re.search(r"Date:\s*([^\n]+)", raw_t)
            
            # Simple slice for verbatim quote
            quote = raw_t.split("\nContent:")[-1].strip() if "Content:" in raw_t else raw_t.split("Description:")[-1].strip()
            quote = quote[:150] + "..." if len(quote) > 150 else quote
            
            fallback_signals.append({
                "signal_type": "Raw Discovery",
                "verbatim_quote": quote,
                "source_url": url_match.group(1) if url_match else "N/A",
                "event_date": date_match.group(1) if date_match else "2026-06-25T00:00:00Z",
                "quote_validated": True,
                "similarity_score": 100.0,
                "recency_label": "unknown",
                "score_contribution": 0.0
            })

        lead_payload = {
            "id": lead_id,
            "company_name": company_name,
            "domain": domain,
            "industry": firmographics.get("industry", "Unknown"),
            "employee_count": firmographics.get("employee_count"),
            "intent_score": dummy_score,
            "signal_freshness": 100,
            "tier": "Low",
            "icp_fit": "Poor",
            "confidence": {
                "label": "Low Trust",
                "color": "rose",
                "verified": 0,
                "total": 1,
            },
            "why_now": f"ICP Gatekeeper: {icp_reason}",
            "badge": "filtered",
            "signals": fallback_signals,
            "ai_verdict": f"Profile rejected — {icp_reason}",
            "dns_audit": {
                "spf": "Missing",
                "dkim": "Missing",
                "dmarc": "Missing",
                "issues": [],
            },
            "contacts": [],
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        _persist_lead(lead_id, domain, company_name, lead_payload)
        return {"status": "success", "lead": lead_payload}

    # Phase 1 (per-company): Discover signals for this specific company
    if pre_fetched_signals is not None:
        raw_signals = pre_fetched_signals
    else:
        raw_signals = await fetch_public_intent_signals(company_name)
        
    # Scrape Creators Phase 3: Narrow Validation
    try:
        from backend.pipeline.social_discovery import check_scrape_creators_budget, fetch_founder_post
        from backend.models import ScrapeLedger
        from datetime import timedelta
        
        db = SessionLocal()
        ledger_entry = db.query(ScrapeLedger).filter(
            ScrapeLedger.company_name == company_name
        ).first()
        
        in_cooldown = False
        if ledger_entry and ledger_entry.last_scraped_date:
            # Handle naive datetime from SQLite
            last_dt = ledger_entry.last_scraped_date
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - last_dt
            if age < timedelta(days=14):
                in_cooldown = True
                logger.info(f"Skipping Scrape Creators for {company_name} (14-day cooldown active).")
                
        if not in_cooldown:
            budget = await check_scrape_creators_budget()
            if budget >= 50:
                # Serper locate exact post URLs (simulated here)
                simulated_linkedin_url = f"https://linkedin.com/post/{company_name.lower().replace(' ', '-')}-update"
                simulated_reddit_url = f"https://reddit.com/r/SaaS/comments/{company_name.lower().replace(' ', '-')}-news"
                
                # Scrape Creators post endpoint for both
                social_post_li = await fetch_founder_post(simulated_linkedin_url)
                if social_post_li:
                    raw_signals.append(social_post_li)
                    
                social_post_reddit = await fetch_founder_post(simulated_reddit_url)
                if social_post_reddit:
                    raw_signals.append(social_post_reddit)
                
                # Update ledger (record multiple platforms)
                if ledger_entry:
                    ledger_entry.last_scraped_date = datetime.now(timezone.utc)
                else:
                    new_ledger = ScrapeLedger(
                        id=str(uuid.uuid4()),
                        company_name=company_name,
                        platform="linkedin,reddit",
                        last_scraped_date=datetime.now(timezone.utc)
                    )
                    db.add(new_ledger)
                db.commit()
            else:
                logger.warning(f"Skipping Scrape Creators for {company_name} due to low budget ({budget}).")
        db.close()
    except Exception as e:
        logger.error(f"Error executing Scrape Creators validation: {e}")

    # Combine text but explicitly attach the source URL above each chunk so the LLM can extract it
    cleaned_html_parts = []
    for s in raw_signals:
        url = s.get("url") or s.get("link") or s.get("extracted_url") or "Unknown URL"
        text = s.get("raw_text", "")
        cleaned_html_parts.append(f"[Source URL: {url}]\n{text}")
    cleaned_html = "\n\n---\n\n".join(cleaned_html_parts)

    # Phase 5: Fast intent classification using Groq
    from backend.pipeline.scorer import analyze_lead_intent_with_llm
    
    scored_data = {}
    for attempt in range(3):
        try:
            scored_data = await analyze_lead_intent_with_llm(
                company_name, 
                cleaned_html, 
                firmographics
            )
            if "API Error" not in scored_data.get("ai_verdict", ""):
                break
        except Exception as e:
            logger.warning(f"Phase 5 LLM Synthesis transient error on attempt {attempt+1}: {e}")
        
        if attempt < 2:
            logger.info("Backing off for 5 seconds before retrying Phase 5 LLM Synthesis...")
            await asyncio.sleep(5)
            
    if not scored_data:
        scored_data = {
            "company_name": company_name,
            "intent_score": 0,
            "ai_verdict": "API Error: Synthesis failed after 3 retries.",
            "signals": [],
            "icp_fit": "Poor"
        }
        
    # Override LLM-generated URLs with exact links from raw payloads
    if scored_data.get("signals"):
        for sig in scored_data["signals"]:
            quote = sig.get("verbatim_quote", "")
            for raw_s in raw_signals:
                if quote and quote.lower() in raw_s.get("raw_text", "").lower():
                    exact_url = raw_s.get("url") or raw_s.get("link") or raw_s.get("extracted_url")
                    if exact_url:
                        sig["source_url"] = exact_url
                    break

    # Phase 3b: DNS Audit
    dns_res = await audit_domain_email_infrastructure(domain)

    total_signals = len(scored_data.get("signals", []))
    verified_signals = sum(
        1 for s in scored_data.get("signals", []) if s.get("quote_validated")
    )

    # Multi-factor confidence calculation
    avg_similarity = (
        sum(s.get("similarity_score", 0) for s in scored_data.get("signals", []))
        / total_signals
        if total_signals > 0
        else 0
    )
    verification_ratio = (
        (verified_signals / total_signals * 100) if total_signals > 0 else 0
    )
    unique_types = (
        len(set(s.get("signal_type", "") for s in scored_data.get("signals", [])))
        if total_signals > 0
        else 0
    )
    diversity_bonus = min(unique_types * 7, 20)

    raw_confidence = (
        (avg_similarity * 0.50) + (verification_ratio * 0.30) + diversity_bonus
    )
    confidence_pct = min(int(raw_confidence * 0.92), 95)

    if total_signals == 0:
        conf_label = "Low Trust"
        conf_color = "rose"
        confidence_pct = 0
    elif confidence_pct >= 75:
        conf_label = "High Trust"
        conf_color = "emerald"
    elif confidence_pct >= 45:
        conf_label = "Moderate Trust"
        conf_color = "amber"
    else:
        conf_label = "Low Trust"
        conf_color = "rose"

    # Handle failed/empty records gracefully
    if total_signals == 0 or "API Error" in scored_data.get("ai_verdict", ""):
        logger.info(
            f"Zero signals found for {company_name}. Persisting with 0 score."
        )
        scored_data["ai_verdict"] = "No recent public signals detected for this target."
        scored_data["intent_score"] = 0
        scored_data["icp_fit"] = "Poor"

    # URL Override: Replace LLM hallucinated URLs with exact canonical links from ScrapeBadger/Serper
    if scored_data.get("signals"):
        for sig in scored_data["signals"]:
            quote = sig.get("verbatim_quote", "")
            for raw_s in raw_signals:
                if quote and quote.lower() in raw_s.get("raw_text", "").lower():
                    exact_url = raw_s.get("url") or raw_s.get("link") or raw_s.get("extracted_url")
                    if exact_url:
                        sig["source_url"] = exact_url
                    break

    # Phase 4: Contact Extraction (real, not mocked)
    contacts = extract_contacts(domain, scored_data.get("company_name", company_name))

    # Safely parse employee count which might come as a string range "50-200" from Gemini
    raw_emp = firmographics.get("employee_count")
    emp_val = None
    if isinstance(raw_emp, int):
        emp_val = raw_emp
    elif isinstance(raw_emp, str):
        import re
        nums = re.findall(r'\d+', raw_emp.replace(",", ""))
        if nums:
            emp_val = int(nums[-1])  # Take upper bound

    lead_id = str(uuid.uuid4())
    lead_payload = {
        "id": lead_id,
        "company_name": scored_data.get("company_name", company_name),
        "domain": domain,
        "industry": firmographics.get("industry", "Unknown"),
        "employee_count": emp_val,
        "intent_score": scored_data.get("intent_score", 0),
        "signal_freshness": scored_data.get("signal_freshness", 100),
        "tier": scored_data.get("tier", "Low"),
        "icp_fit": scored_data.get("icp_fit", "Partial"),
        "confidence": {
            "label": conf_label,
            "color": conf_color,
            "verified": confidence_pct,
            "total": 100,
        },
        "why_now": scored_data.get("why_now", "Automated batch sweep detected new signals."),
        "badge": "new_today",
        "signals": scored_data.get("signals", []),
        "ai_verdict": scored_data.get("ai_verdict", "Review signals for outreach context."),
        "dns_audit": dns_res,
        "contacts": contacts,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    _persist_lead(lead_id, domain, company_name, lead_payload)
    return {"status": "success", "lead": lead_payload}

async def select_top_5_leads(companies: set[str]) -> list[dict]:
    """
    Step 1: Gemini 2.5 Flash + Web Search
    Ranks 100 names -> Picks TOP 5 with live 2026 intent triggers
    """
    if not companies:
        return []

    logger.info(f"Selecting top 5 leads from {len(companies)} candidates using Gemini 2.5 Flash + Web Search...")
    company_list_str = "\n".join(list(companies))
    
    from backend.config_manager import load_intent_config
    config = load_intent_config()
    target_topics = config.get("social_topics", ["B2B services"])
    topics_str = ", ".join(target_topics)
    
    prompt = f"""You are a Lead Scoring AI and Senior B2B Sales Intelligence Analyst.

TASK:
Analyze the attached list of {len(companies)} company names.
Use live web search to evaluate recent developments (2025-2026) and identify the TOP 5 companies displaying the highest, most actionable sales intent triggers.

IDEAL CUSTOMER PROFILE (ICP) TARGET:
- Target Company Scale: Prioritize high-growth mid-market scale-ups and fast-growing startups (typically Series A through Series C/Growth rounds, approximately 20 to 300 employees).
- Avoid Mega-Unicorns / Enterprise Giants: Exclude mature tech giants or massive mega-unicorns with established >500–1,000+ employee bases (e.g., avoid giant infrastructure plays like Datadog, Perplexity, or ZoomInfo) unless they fit a mid-market scale-up profile.

EVALUATION & RANKING CRITERIA (Prioritize in order):
0. 🎯 EXPLICIT INTENT: Strong preference for companies displaying a high likelihood of needing {topics_str} (e.g. searching for leadership, growth consulting, specific marketing services).
1. 💰 Funding & Investment: Recent venture rounds (Series A, B, or C), debt financing, or strategic funding announcements in 2025-2026.
2. 📈 Revenue & Scale Milestones: Publicly announced ARR milestones ($5M–$50M+ ARR, $1B+ processing volume, etc.).
3. 👥 Rapid Hiring Spikes: Public leadership announcements hiring for 10+ new roles or filling C-level positions.
4. 🚀 Major Product / Market Launches: Rollouts of new AI platforms, international expansions, or strategic enterprise partnerships.

STRICT EXCLUSIONS (Do NOT pick):
- Exclude other service agencies, recruiting/staffing firms, consulting practices, and local boutique studios (e.g., recruitment agencies, design agencies, dev shops).
- Focus strictly on product-driven SaaS, B2B software platforms, or high-growth D2C scale-ups.
- Companies undergoing mass layoffs, bankruptcy, or legal/regulatory trouble.
- Dormant/inactive companies or companies with no verifiable 2025-2026 news.
- Micro-companies with fewer than 5 employees.

OUTPUT FORMAT:
Return ONLY a valid JSON array containing exactly the TOP 5 ranked companies formatted as follows:

[
  {{
    "rank": 1,
    "company_name": "Exact Brand Name",
    "estimated_domain": "companydomain.com",
    "intent_score": 94,
    "primary_category": "FUNDING | HIRING_SPIKE | PRODUCT_LAUNCH | STRATEGIC_REVIEW",
    "employee_count": "Estimated employee tier (e.g., 50-200, 20-300, etc.)",
    "top_intent_trigger": "1-2 sentence summary of the exact verified trigger event with metrics/dates",
    "suggested_outreach_angle": "1-sentence pitch hook specifically related to {topics_str}"
  }}
]

CRITICAL RULES:
- Ensure 'estimated_domain' uses the official canonical root website domain (e.g., 'nitra.com', 'readai.com', 'stepful.com').
- Do not include markdown commentary, introductory text, or conversational explanations outside the JSON array.

COMPANY LIST TO SCREEN ({len(companies)} Companies):
{company_list_str}
"""

    import os
    from google import genai
    from google.genai import types
    
    api_key = settings.GEMINI_API_KEY
    if not api_key or api_key in ["mock_key_if_empty", ""]:
        logger.warning("Gemini API key missing, falling back to dummy top 5 selection.")
        return _select_top_5_leads_dummy(companies)
        
    try:
        client = genai.Client(api_key=api_key, http_options={'timeout': 60.0})
        # Configure Gemini to use Google Search for grounding (response_mime_type is unsupported with tools)
        config = types.GenerateContentConfig(
            temperature=0.2,
            tools=[{"googleSearch": {}}]
        )
        
        # Use run_in_executor since generate_content can be synchronous
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=config
            )
        )
        
        raw_json = response.text.replace("```json", "").replace("```", "").strip()
        top_5_data = json.loads(raw_json)
        
        logger.info(f"Gemini successfully selected top 5 leads: {[c.get('company_name') for c in top_5_data]}")
        return top_5_data
        
    except Exception as e:
        logger.error(f"Error selecting top 5 leads with Gemini: {e}")
        return _select_top_5_leads_dummy(companies)


def _select_top_5_leads_dummy(companies: set[str]) -> list[dict]:
    """Fallback dummy function"""
    logger.info(f"Selecting top 5 leads from {len(companies)} candidates using dummy fallback...")
    top_5 = list(companies)[:5]
    return [{"company_name": name, "estimated_domain": f"{name.lower().replace(' ', '').replace(',', '')}.com", "industry": "B2B Software & Services"} for name in top_5]

async def run_batch_pipeline() -> dict:
    """
    Phase 6 — Autonomous batch pipeline.
    Discovers companies via keyword sweeps, then processes each one.
    Called by the scheduler instead of iterating a hardcoded list.
    """
    logger.info("Starting autonomous batch pipeline...")

    # Phase 1: Autonomous discovery
    discovered = await run_autonomous_discovery()
    logger.info(f"Batch pipeline: {len(discovered)} total companies to process after Search Posts sweep.")

    # Fetch currently active companies from DB to avoid duplicates (hash map)
    db = SessionLocal()
    try:
        active_companies = {lead.company_name for lead in db.query(LeadSnapshot).all()}
    finally:
        db.close()

    # Filter out companies already active on the frontend
    filtered_discovered = [d for d in discovered if d[0] not in active_companies]
    logger.info(f"Filtered to {len(filtered_discovered)} new companies (skipped {len(discovered) - len(filtered_discovered)} already live).")

    # Step 1: Gemini 2.5 Flash + Web Search (Ranks 100 names -> Picks TOP 5)
    pool_candidates = {d[0] for d in filtered_discovered[:100]}
    if not pool_candidates:
        logger.info("No new companies to process.")
        return {"companies_processed": 0, "successes": 0, "had_errors": False}
        
    top_5_leads = await select_top_5_leads(pool_candidates)
    
    # Phase 2: Entity Resolution (Top 5 Only)
    top_5_pool = []
    for lead in top_5_leads:
        c_name = lead.get("company_name")
        # Run Entity Resolution now so deep sweeps have verified domains
        from backend.pipeline.enrichment import resolve_domain_via_serper
        from backend.config import settings
        real_domain = await resolve_domain_via_serper(
            company_name=c_name, 
            serper_api_key=settings.SERPER_API_KEY, 
            phase1_estimated_domain=lead.get("estimated_domain", "")
        )
        
        # Inject the Gemini Phase 1 estimate so it flows into Phase 4 Hybrid Scoring
        firmos = {
            "employee_count": lead.get("employee_count", "Unknown"),
            "industry": lead.get("industry", "B2B Software & Services")
        }
        
        domain = real_domain or lead.get("estimated_domain") or lead.get("domain")
        firmographics = firmos if firmos else {}
        for d in filtered_discovered:
            if d[0] == c_name:
                firmographics.update(d[2])
                break
        top_5_pool.append((c_name, domain, firmographics))
    
    success_count = 0
    errors = False

    # Phase 3 & 4 & 5 & 6: Sequential Deep Sweep, Synthesis, and DB Persist Per Company
    for idx, (company_name, domain, firmographics) in enumerate(top_5_pool):
        logger.info(f"Fetching deep signals for [{idx + 1}/{len(top_5_pool)}]: {company_name}")
        try:
            import httpx
            from backend.pipeline.enrichment import fetch_reddit_posts, fetch_twitter_posts
            
            raw_signals = await fetch_public_intent_signals(company_name)
            
            # ScrapeBadger native 3-times exponential backoff handles 429s automatically
            async with httpx.AsyncClient(timeout=45.0) as client:
                reddit_posts = await fetch_reddit_posts(client, company_name, domain)
                twitter_posts = await fetch_twitter_posts(client, company_name, domain)
                
            for reddit_post in reddit_posts:
                date_str = reddit_post.get("date", "Unknown Date")
                raw_signals.append({
                    "company_name": company_name,
                    "domain": domain,
                    "raw_text": f"Reddit Post:\nDate: {date_str}\nTitle: {reddit_post.get('title', '')}\nText: {reddit_post.get('text', '')}",
                    "source_api": "Reddit",
                    "url": reddit_post.get("url")
                })
                
            for twitter_post in twitter_posts:
                date_str = twitter_post.get("created_at") or twitter_post.get("date") or "Unknown Date"
                raw_signals.append({
                    "company_name": company_name,
                    "domain": domain,
                    "raw_text": f"X/Twitter Post:\nDate: {date_str}\nText: {twitter_post.get('text', '')}",
                    "source_api": "X",
                    "url": twitter_post.get("url")
                })

            signals = _heuristic_signal_filter(raw_signals)
        except Exception as e:
            logger.error(f"Error fetching signals for {company_name}: {e}")
            signals = []
            
        logger.info(f"Processing Synthesis for Top [{idx + 1}/{len(top_5_pool)}]: {company_name} with {len(signals)} signals")
        try:
            res = await run_pipeline_for_company(
                company_name, 
                domain, 
                firmographics,
                pre_fetched_signals=signals
            )
            if res.get("status") == "success":
                success_count += 1
                if res.get("lead", {}).get("ai_verdict", "").startswith("API Error"):
                    logger.warning(f"API Error detected for {company_name}. Halting pipeline execution.")
                    break
        except Exception as e:
            logger.error(f"Error orchestrating {company_name}: {e}")
            errors = True

        # Rate limit: 10s delay between companies
        logger.info("Sleeping 10s to respect rate limits...")
        await asyncio.sleep(10)

    return {
        "companies_processed": len(discovered),
        "successes": success_count,
        "had_errors": errors,
    }


# ======================================================================
# Helpers
# ======================================================================

def _heuristic_signal_filter(signals: list[dict]) -> list[dict]:
    """
    Applies a zero-cost Regex/keyword pass to raw signals to demote generic PR fluff.
    Only allows signals that contain intent keywords or are purely neutral.
    """
    import os

    # 1. Dynamically read allowlist from settings
    try:
        config_path = os.path.join(os.path.dirname(__file__), "..", "intent_config.json")
        with open(config_path, "r") as f:
            intent_cfg = json.load(f)
            allowlist = intent_cfg.get("extraction_keywords", [])
    except Exception:
        allowlist = []
        
    if not allowlist:
        allowlist = ["hiring", "series a", "series b", "series c", "seed", "raises", "appoints", "expands"]
        
    allowlist = [w.lower() for w in allowlist]
    
    # 2. Hardcoded denylist for PR fluff
    denylist = ["stock price", "shares", "earnings", "product launch", "acquires", "partners with"]
    
    filtered = []
    for sig in signals:
        text = sig.get("raw_text", "").lower()
        if not text:
            continue
            
        has_allowlist = any(term in text for term in allowlist)
        has_denylist = any(term in text for term in denylist)
        
        # Strict Time-Decay Threshold (Discard > 180 days)
        from backend.pipeline.time_decay import calculate_time_decay
        date_str = sig.get("date_posted") or sig.get("event_date") or ""
        multiplier, _ = calculate_time_decay(date_str)
        if multiplier < 0.20:
            continue # Drop anything older than 180 days
            
        if has_allowlist:
            filtered.append(sig)  # Strong intent, pass immediately
        elif has_denylist and not has_allowlist:
            continue  # Fluff article, throw in the trash
        else:
            filtered.append(sig)  # Neutral, let Gemini decide
            
    return filtered


def _get_icp_rejection_reason(firmographics: dict) -> str:
    """Generates a human-readable ICP rejection reason."""
    emp = firmographics.get("employee_count")
    if emp is not None:
        if emp > 500:
            return "Exceeds employee ceiling (>500)"
        if emp < 5:
            return "Under-resourced/pre-revenue (<5 employees)"

    funding = firmographics.get("funding_stage", "")
    if funding and funding.lower() in ["series d", "series e", "public", "m&a"]:
        return f"Stagnant funding stage ({funding})"

    return "Industry mismatch or scale constraints"


def _persist_lead(
    lead_id: str, domain: str, company_name: str, lead_payload: dict
) -> None:
    """Writes a lead snapshot to SQLite. Updates if company_name already exists to prevent duplicates."""
    db = SessionLocal()
    try:
        from backend.models import LeadSnapshot
        existing = db.query(LeadSnapshot).filter(LeadSnapshot.company_name == company_name).first()
        if existing:
            lead_payload["id"] = existing.id
            existing.domain = domain
            existing.industry = lead_payload.get("industry")
            existing.employee_count = lead_payload.get("employee_count")
            existing.intent_score = lead_payload.get("intent_score", 0)
            existing.signal_freshness = lead_payload.get("signal_freshness")
            existing.tier = lead_payload.get("tier")
            existing.icp_fit = lead_payload.get("icp_fit")
            existing.badge = lead_payload.get("badge")
            existing.why_now = lead_payload.get("why_now")
            existing.ai_verdict = lead_payload.get("ai_verdict")
            existing.full_payload = lead_payload
        else:
            snapshot = LeadSnapshot(
                id=lead_id,
                domain=domain,
                company_name=company_name,
                industry=lead_payload.get("industry"),
                employee_count=lead_payload.get("employee_count"),
                intent_score=lead_payload.get("intent_score", 0),
                signal_freshness=lead_payload.get("signal_freshness"),
                tier=lead_payload.get("tier"),
                icp_fit=lead_payload.get("icp_fit"),
                badge=lead_payload.get("badge"),
                why_now=lead_payload.get("why_now"),
                ai_verdict=lead_payload.get("ai_verdict"),
                full_payload=lead_payload,
            )
            db.add(snapshot)
        db.commit()
        logger.info(f"Successfully persisted {company_name}")
    except Exception as e:
        logger.error(f"Failed to persist {company_name}: {e}")
    finally:
        db.close()

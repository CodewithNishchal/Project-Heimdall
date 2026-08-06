import asyncio
import json
import os
import re
import uuid
import logging
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone


def extract_revenue_from_exa_text(text: str, structured_out: Optional[dict] = None) -> Optional[str]:
    def clean_rev_string(val_str: str) -> str:
        if not val_str or not any(c.isdigit() for c in val_str):
            return "N/A"
        # Convert words like million/billion to M/B
        s = re.sub(r'(?i)\s*million\b', 'M', val_str)
        s = re.sub(r'(?i)\s*billion\b', 'B', s)
        s = re.sub(r'(?i)\s*thousand\b', 'K', s)

        m = re.search(r'(~?\s*\$?\s*[\d\.]+(?:\s*-\s*\$?\s*[\d\.]+)?)\s*([MKBmkb])?', s)
        if m:
            raw_num = m.group(1).replace("~", "").replace("$", "").strip()
            unit = (m.group(2) or "").upper()
            if not unit:
                try:
                    num_val = float(raw_num.split("-")[0].strip())
                    if 0 < num_val < 1000:
                        unit = "M"
                except Exception:
                    pass
            prefix = "~$" if "~" in s else "$"
            return f"{prefix}{raw_num}{unit}"
        return "N/A"

    if structured_out and isinstance(structured_out, dict):
        content = structured_out.get("content") if isinstance(structured_out.get("content"), dict) else structured_out
        rev_val = content.get("arr_estimate") or content.get("annual_revenue") or content.get("revenueAnnual")

        if isinstance(rev_val, (int, float)) and rev_val > 0:
            if rev_val >= 1_000_000_000:
                return f"${rev_val / 1_000_000_000:.1f}B"
            elif rev_val >= 1_000_000:
                return f"${rev_val / 1_000_000:.1f}M"
            elif rev_val < 1000:
                return f"${rev_val:.1f}M"
            else:
                return f"${rev_val:,.0f}"
        elif isinstance(rev_val, str) and rev_val.strip():
            res = clean_rev_string(rev_val)
            if res != "N/A":
                return res

    if not text:
        return None

    patterns = [
        r'(?i)(?:annual\s+revenue|revenue|arr)\s*(?:of|is|=|:)?\s*~\s*\$?\s*([\d\.]+\s*(?:million|billion|M|B)?)',
        r'(?i)\$\s*([\d\.]+\s*(?:million|billion|M|B)?)\s*(?:annual\s+revenue|arr|revenue)',
        r'(?i)(?:annual\s+revenue|revenue|arr)\s*(?:of|is|=|:)?\s*\$?\s*([\d\.]+\s*-\s*\$?[\d\.]+\s*(?:million|billion|M|B)?)',
        r'(?i)USD\s+([\d,]+)'
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return clean_rev_string(m.group(1))
    return None
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from backend.pipeline.scorer import process_hybrid_lead_scoring
from backend.pipeline.airtable_connector import get_ui_test_batch, get_midnight_cron_batch
from backend.pipeline.dns_audit import audit_domain_email_infrastructure
from backend.database import SessionLocal
from backend.models import LeadSnapshot
from google import genai
from google.genai import types

logger = logging.getLogger("StreamingOrchestrator")

EXA_API_KEY = os.getenv("EXA_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
SCRAPEBADGER_API_KEY = os.getenv("SCRAPEBADGER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
APIFY_INSIGHTS_API_KEY = os.getenv("APIFY_INSIGHTS_API_KEY") or os.getenv("APIFY_API_KEY")
THEIRSTACK_API_KEY = os.getenv("THEIRSTACK_API_KEY")
LINKUP_API_KEY = os.getenv("LINKUP_API_KEY")

from backend.pipeline.linkedin_id_resolver import resolve_linkedin_company_id

TECH_AND_TA_KEYWORDS = [
    "engineer", "developer", "architect", "systems", "ml", "ai", "security", 
    "tech", "software", "infrastructure", "data", "product", "manager",
    "talent acquisition", "recruiter", "recruitment", "head of people", "hr", "people partner"
]
ENTRY_LEVEL_EXCLUSIONS = ["junior", "intern", "internship", "trainee"]


def is_entry_level_associate(title_lower: str) -> bool:
    if "associate" not in title_lower:
        return False
    senior_modifiers = ["director", "senior", "vp", "vice president", "head", "lead", "principal", "manager", "solutions architect"]
    return not any(mod in title_lower for mod in senior_modifiers)


def is_valid_company_job(title: str, link: str, snippet: str, company_name: str, company_slug: str) -> bool:
    t_lower = title.lower()
    l_lower = link.lower()
    c_lower = company_name.lower()
    slug_lower = company_slug.lower()

    if any(ex in t_lower for ex in ENTRY_LEVEL_EXCLUSIONS):
        return False
    if is_entry_level_associate(t_lower):
        return False

    has_qualified_role = any(kw in t_lower or kw in snippet.lower() for kw in TECH_AND_TA_KEYWORDS)
    if not has_qualified_role:
        return False

    target_domains = [
        f"ashbyhq.com/{slug_lower}",
        f"greenhouse.io/{slug_lower}",
        f"lever.co/{slug_lower}",
        f"workable.com/{slug_lower}",
        f"indeed.com/cmp/{slug_lower}",
        f"linkedin.com/company/{slug_lower}",
        f"linkedin.com/jobs",
        f"{slug_lower}.com"
    ]
    if any(dom in l_lower for dom in target_domains):
        return True

    title_anchors = [
        f"@ {c_lower}", f"at {c_lower}", f"- {c_lower}", f"| {c_lower}", 
        f", {c_lower}", f"{c_lower} -", f"{c_lower}:", f"{c_lower} jobs"
    ]
    if any(anchor in t_lower for anchor in title_anchors):
        return True

    return False


async def fetch_linkedin_company_insights(company_id: str, company_slug: str) -> Optional[Dict[str, Any]]:
    if not APIFY_INSIGHTS_API_KEY or not company_id:
        return None

    url = "https://api.apify.com/v2/acts/freshdata~linkedin-company-insights-scraper/run-sync-get-dataset-items"
    params = {"token": APIFY_INSIGHTS_API_KEY}
    payload = {"company_id": company_id, "company_name": company_slug}

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, params=params, json=payload)
            if resp.status_code in [200, 201]:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get("data")
                elif isinstance(data, dict):
                    return data.get("data")
    except Exception as e:
        logger.error(f"Error fetching Apify LinkedIn Insights for company_id {company_id}: {e}")

async def fetch_company_job_theirstack(company_name: str, domain: str, company_slug: str) -> Optional[Dict[str, Any]]:
    """
    Fetches strictly 1 active job for the company using TheirStack Jobs API.
    Uses domain or company LinkedIn URL. Falls back to None if API fails or returns 0 jobs.
    """
    if not THEIRSTACK_API_KEY:
        logger.info("TheirStack API key not configured. Will use Serper fallback.")
        return None

    url = "https://api.theirstack.com/v1/jobs/search"
    headers = {
        "Authorization": f"Bearer {THEIRSTACK_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    linkedin_url = f"https://www.linkedin.com/company/{company_slug}" if company_slug else None

    # Priority payload: domain or company linkedin url with limit 1
    payload = {
        "company_domain_or": [domain] if domain else [],
        "posted_at_max_age_days": 90,
        "limit": 1,
        "page": 0
    }
    if linkedin_url:
        payload["company_linkedin_url_or"] = [linkedin_url]

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                jobs = data.get("data", [])
                if isinstance(jobs, list) and len(jobs) > 0:
                    j = jobs[0]
                    company_info = j.get("company_object", {})
                    qualified_job = {
                        "title": j.get("job_title", "Position Open"),
                        "link": j.get("url") or j.get("source_url") or f"https://www.linkedin.com/company/{company_slug}/jobs",
                        "snippet": (j.get("description") or "")[:250].replace("\n", " ").replace("**", ""),
                        "date": j.get("date_posted", "Recent"),
                        "ats_platform": "TheirStack API (LinkedIn)",
                        "seniority": j.get("seniority", "mid_level"),
                        "location": j.get("location", ""),
                        "technologies": company_info.get("technology_names", [])
                    }
                    logger.info(f"🎯 TheirStack successfully returned 1 job for {company_name}: '{qualified_job['title']}'")
                    return {
                        "total_results": 1,
                        "used_fallback": False,
                        "source": "theirstack",
                        "qualified_jobs": [qualified_job]
                    }
            logger.warning(f"TheirStack API returned status {resp.status_code} or 0 jobs for {company_name}. Falling back to Serper...")
    except Exception as e:
        logger.error(f"Error calling TheirStack API for {company_name}: {e}. Falling back to Serper...")

    return None


async def fetch_company_jobs_serper(company_name: str, company_slug: str, domain: str) -> Dict[str, Any]:
    if not SERPER_API_KEY:
        return {"total_results": 0, "qualified_jobs": []}

    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}

    single_ats_queries = [
        f"site:jobs.ashbyhq.com/{company_slug}",
        f"site:boards.greenhouse.io/{company_slug}",
        f"site:jobs.lever.co/{company_slug}",
        f"site:apply.workable.com/{company_slug}"
    ]

    qualified = []
    platform_stats = {}

    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            for q in single_ats_queries:
                platform_name = q.split("site:")[1].split("/")[0]
                payload = {"q": q, "num": 10, "tbs": "qdr:m", "autocorrect": False}
                resp = await client.post(url, headers=headers, json=payload)
                raw_items = resp.json().get("organic", []) if resp.status_code == 200 else []
                
                p_qual = []
                for item in raw_items:
                    t = item.get("title", "")
                    l = item.get("link", "")
                    s = item.get("snippet", "")
                    if is_valid_company_job(t, l, s, company_name, company_slug):
                        p_qual.append({
                            "title": t,
                            "link": l,
                            "snippet": s,
                            "date": item.get("date", "Past 30 Days"),
                            "ats_platform": platform_name
                        })
                        qualified.append(p_qual[-1])

                platform_stats[platform_name] = len(p_qual)

            if len(qualified) > 0:
                return {"total_results": len(qualified), "used_fallback": False, "platform_stats": platform_stats, "qualified_jobs": qualified}

            # Fallback
            fallback_query = f'site:linkedin.com/company/{company_slug}/jobs OR site:indeed.com/cmp/{company_slug}/jobs OR site:{domain}/careers OR ("{company_name}" ("Engineer" OR "Manager" OR "Recruiter") (site:ashbyhq.com OR site:greenhouse.io OR site:lever.co OR site:workable.com OR site:linkedin.com/jobs OR site:indeed.com))'
            f_payload = {"q": fallback_query, "num": 10, "tbs": "qdr:m", "autocorrect": False}
            f_resp = await client.post(url, headers=headers, json=f_payload)
            f_raw = f_resp.json().get("organic", []) if f_resp.status_code == 200 else []

            for item in f_raw:
                t = item.get("title", "")
                l = item.get("link", "")
                s = item.get("snippet", "")
                if is_valid_company_job(t, l, s, company_name, company_slug):
                    qualified.append({
                        "title": t,
                        "link": l,
                        "snippet": s,
                        "date": item.get("date", "Past 30 Days"),
                        "ats_platform": "FALLBACK_SERP"
                    })

            return {"total_results": len(qualified), "used_fallback": True, "platform_stats": platform_stats, "qualified_jobs": qualified}

    except Exception as e:
        logger.error(f"Error fetching Serper Jobs for {company_name}: {e}")
        return {"total_results": 0, "error": str(e)}


async def process_single_company(
    candidate: Dict[str, Any],
    semaphore: asyncio.Semaphore
) -> Optional[Dict[str, Any]]:
    """
    Processes a single candidate domain through the approved multi-source pipeline:
    1. Stage 1: Exa AI (Canonical Identity & Deep Signals) -> Sent directly to Gemini 2.5 Flash
    2. Stage 2: Unified Gemini 2.5 Flash Intent Synthesis & Codebase Math Engine (`scorer.py`)
    3. Stage 3: High-Intent Gate (intent_score >= 80) -> Apify LinkedIn Insights & TheirStack (1-job limit) with Serper fallback
    """
    async with semaphore:
        company_name = candidate.get("company_name", "")
        domain = candidate.get("domain", "")
        firmographics = candidate.get("firmographics", {})

        if not company_name or not domain:
            return None

        logger.info(f"🚀 Processing candidate: {company_name} ({domain})...")

        combined_raw_text = ""
        url_index_map = {}
        source_counter = 1
        structured_out = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            # -----------------------------------------------------------------
            # EXA AI: REFINED 2-CALL ARCHITECTURE (CANONICAL IDENTITY + DEEP FRESH SIGNALS)
            # -----------------------------------------------------------------
            if EXA_API_KEY:
                exa_headers = {
                    "accept": "application/json",
                    "content-type": "application/json",
                    "x-api-key": EXA_API_KEY
                }

                # 1. Canonical Identity Call (Self-reported site facts)
                identity_payload = {
                    "query": f"{company_name} company profile leadership services products",
                    "type": "neural",
                    "category": "company",
                    "numResults": 2,
                    "includeDomains": [domain] if domain else [],
                    "contents": {"text": True, "summary": True}
                }

                # 2. Deep Fresh Signal Call (Structured extraction + maxAgeHours)
                company_schema = {
                    "type": "object",
                    "properties": {
                        "headcount": {"type": "string"},
                        "industry": {"type": "string"},
                        "funding_stage": {"type": "string"},
                        "funding_amount": {"type": "string"},
                        "funding_date": {"type": "string"},
                        "arr_estimate": {"type": "string"},
                        "open_roles_count": {"type": "string"},
                        "recent_hiring_signal": {"type": "string"}
                    },
                    "required": ["headcount", "industry"]
                }

                signal_payload = {
                    "query": f"{company_name} recent funding valuation hiring open roles growth press release news",
                    "type": "deep",
                    "maxAgeHours": 168,
                    "numResults": 3,
                    "excludeDomains": ["clutch.co", "upcity.com", "designrush.com", "goodfirms.co"],
                    "contents": {"text": True, "summary": True},
                    "outputSchema": company_schema
                }

                try:
                    # Call 1: Canonical
                    res1 = await client.post("https://api.exa.ai/search", json=identity_payload, headers=exa_headers)
                    if res1.status_code == 200:
                        for item in res1.json().get("results", []):
                            src_id = f"S{source_counter}"
                            source_counter += 1
                            t_title = item.get("title", "Canonical Profile")
                            t_url = item.get("url", f"https://{domain}")
                            summary = item.get("summary", "")
                            snippet = item.get("text", "")
                            url_index_map[src_id] = t_url

                            combined_raw_text += f"\n--- [{src_id}] CANONICAL IDENTITY: {t_title} ({t_url}) ---\n"
                            if summary:
                                combined_raw_text += f"SUMMARY: {summary}\n"
                            if snippet:
                                combined_raw_text += f"DETAILS: {snippet[:500]}\n"

                    # Call 2: Deep Signals
                    res2 = await client.post("https://api.exa.ai/search", json=signal_payload, headers=exa_headers)
                    if res2.status_code != 200:
                        # Fallback if camelCase parameter key is output_schema
                        signal_payload["output_schema"] = signal_payload.pop("outputSchema", company_schema)
                        res2 = await client.post("https://api.exa.ai/search", json=signal_payload, headers=exa_headers)

                    if res2.status_code == 200:
                        data2 = res2.json()
                        for item in data2.get("results", []):
                            src_id = f"S{source_counter}"
                            source_counter += 1
                            t_title = item.get("title", "Signal Mention")
                            t_url = item.get("url", "")
                            summary = item.get("summary", "")
                            snippet = item.get("text", "")
                            url_index_map[src_id] = t_url

                            combined_raw_text += f"\n--- [{src_id}] FRESH SIGNAL EVIDENCE: {t_title} ({t_url}) ---\n"
                            if summary:
                                combined_raw_text += f"SUMMARY: {summary}\n"
                            if snippet:
                                combined_raw_text += f"SIGNAL HIGHLIGHTS: {snippet[:500]}\n"

                        # Inject Exa Structured Output if available
                        structured_out = data2.get("output")
                        if structured_out:
                            combined_raw_text += f"\n--- EXA STRUCTURED FACTS ---\n{json.dumps(structured_out)}\n"

                except Exception as e:
                    logger.error(f"Exa search error for {company_name}: {e}")

            # -----------------------------------------------------------------
            # LINKUP.SO FALLBACK (Triggers if Exa AI fails or returns empty text)
            # -----------------------------------------------------------------
            if not combined_raw_text and LINKUP_API_KEY:
                logger.info(f"Exa AI empty/failed for {company_name}. Triggering Linkup.so Standard SourcedAnswer Fallback...")
                linkup_headers = {
                    "Authorization": f"Bearer {LINKUP_API_KEY}",
                    "Content-Type": "application/json"
                }
                linkup_payload = {
                    "q": f"Provide a detailed overview for {company_name} (domain: {domain}) including its core business, recent funding, employee headcount, and leadership.",
                    "depth": "standard",
                    "outputType": "sourcedAnswer"
                }
                try:
                    res_l = await client.post("https://api.linkup.so/v1/search", json=linkup_payload, headers=linkup_headers, timeout=25.0)
                    if res_l.status_code == 200:
                        l_data = res_l.json()
                        answer = l_data.get("answer") or l_data.get("sourcedAnswer", "")
                        if answer:
                            src_id = "S_LINKUP"
                            url_index_map[src_id] = f"https://{domain}"
                            combined_raw_text = f"\n--- [S_LINKUP] LINKUP DEEP SYNTHESIZED EVIDENCE ---\n{answer}\n"
                            logger.info(f"✅ Linkup.so fallback successfully retrieved evidence for {company_name}")
                except Exception as e_l:
                    logger.error(f"Linkup fallback error for {company_name}: {e_l}")

        if not combined_raw_text:
            logger.warning(f"No evidence retrieved for {company_name}.")
            return None

        # ---------------------------------------------------------------------
        # STAGE 2 & 3: UNIFIED GEMINI 2.5 FLASH INTENT SYNTHESIS & HYBRID SCORING
        # ---------------------------------------------------------------------
        from backend.pipeline.scorer import analyze_lead_intent_with_llm

        raw_signals_list = []
        for src_id, full_url in url_index_map.items():
            raw_signals_list.append({
                "url": full_url,
                "title": f"Source {src_id}",
                "text": combined_raw_text
            })

        math_result = await analyze_lead_intent_with_llm(
            company_name=company_name,
            cleaned_html=combined_raw_text,
            firmographics=firmographics,
            icp_fit_label="Strong",
            raw_signals=raw_signals_list
        )

        gemini_tokens = math_result.get("gemini_token_usage", {})
        token_str = f"Prompt: {gemini_tokens.get('prompt_tokens', 0)} | Output: {gemini_tokens.get('completion_tokens', 0)} | Total: {gemini_tokens.get('total_tokens', 0)}" if isinstance(gemini_tokens, dict) else str(gemini_tokens)

        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            dns_res = await audit_domain_email_infrastructure(domain)
        except Exception:
            dns_res = {"spf": "Pass", "dkim": "Pass", "dmarc": "Pass", "issues": []}

        valid_signals = [s for s in math_result.get("signals", []) if s.get("quote_validated")]

        raw_funding = firmographics.get("total_funding")
        if isinstance(raw_funding, (int, float)) and raw_funding > 0:
            if raw_funding >= 1_000_000_000:
                funding_stage = f"${raw_funding / 1_000_000_000:.1f}B raised"
            elif raw_funding >= 1_000_000:
                funding_stage = f"${raw_funding / 1_000_000:.0f}M raised"
            else:
                funding_stage = f"${raw_funding:,.0f} raised"
        elif isinstance(raw_funding, str) and raw_funding:
            funding_stage = raw_funding
        else:
            funding_stage = "Venture Backed"

        SIGNAL_COLOR_MAP = {
            "FUNDING_RAISE": "indigo",
            "HIRING_SPIKE": "emerald",
            "SOCIAL_INTENT": "rose",
            "REVENUE_MILESTONE": "amber",
            "EXECUTIVE_EXPANSION": "indigo",
            "PRODUCT_LAUNCH": "amber",
        }
        raw_signal_tags = math_result.get("signal_tags", [])
        enriched_signal_tags = []
        for st in raw_signal_tags:
            cat = st.get("category", "")
            enriched_signal_tags.append({
                "tag": cat.replace("_", " ").title(),
                "category": cat,
                "color_theme": SIGNAL_COLOR_MAP.get(cat, "indigo")
            })

        extracted_rev = extract_revenue_from_exa_text(combined_raw_text, structured_out=structured_out) or firmographics.get("annual_revenue")

        full_lead_payload = {
            **math_result,
            "id": str(uuid.uuid4()),
            "domain": domain,
            "company_name": company_name,
            "employee_count": firmographics.get("employee_count") or 150,
            "funding_stage": funding_stage,
            "annual_revenue": extracted_rev,
            "signal_tags": enriched_signal_tags,
            "badge": "new_today",
            "confidence": {
                "label": "Verified Intention",
                "color": "emerald",
                "verified": len(valid_signals),
                "total": max(1, len(math_result.get("signals", [])))
            },
            "dns_audit": dns_res if isinstance(dns_res, dict) else {
                "spf": "Pass",
                "dkim": "Pass",
                "dmarc": "Pass",
                "issues": []
            },
            "contacts": [],
            "last_updated": now_iso,
            "groq_token_usage": token_str,
            "gemini_token_usage": token_str,
            "mistral_token_usage": token_str
        }

        final_score = full_lead_payload.get("intent_score", 0)
        logger.info(f"✅ {company_name} ({domain}) scored {final_score} ({full_lead_payload.get('tier')} / {full_lead_payload.get('intent_classification')}) | ♊ Gemini Tokens: [{token_str}]")

        # ---------------------------------------------------------------------
        # STAGE 4: HIGH-INTENT DEEP ENRICHMENT GATE (intent_score >= 80)
        # ---------------------------------------------------------------------
        candidate_slug = candidate.get("linkedin_slug")
        company_slug = candidate_slug or (domain.split(".")[0].lower() if domain else company_name.lower().replace(" ", ""))

        
        if final_score >= 80:
            logger.info(f"🔥 Triggering High-Intent Jobs & Insights Enrichment for {company_name} (intent_score={final_score} >= 80)...")

            # Contact Extraction (4-tier: regex → spaCy NER → email gen → LinkedIn Serper)
            try:
                from backend.pipeline.contact_extractor import extract_contacts
                import asyncio
                loop = asyncio.get_running_loop()
                extracted_contacts = await loop.run_in_executor(None, extract_contacts, domain, company_name)
                if extracted_contacts:
                    full_lead_payload["contacts"] = extracted_contacts
                    logger.info(f"📇 Extracted {len(extracted_contacts)} contacts for {company_name}")
            except Exception as e:
                logger.warning(f"Contact extraction failed for {company_name}: {e}")

            # 1. Resolve numeric LinkedIn Company ID ($0 cost)
            company_id = await resolve_linkedin_company_id(company_slug)
            full_lead_payload["company_linkedin_id"] = company_id
            
            # 2. Fetch LinkedIn Insights via Apify if ID resolved
            if company_id:
                insights = await fetch_linkedin_company_insights(company_id, company_slug)
                full_lead_payload["company_insights"] = insights
            else:
                full_lead_payload["company_insights"] = None

            # 3. Fetch Active Job via TheirStack (1 job limit using LinkedIn URL / domain), fallback to Serper on error/0 results
            jobs_res = await fetch_company_job_theirstack(company_name, domain, company_slug)
            if not jobs_res or jobs_res.get("total_results", 0) == 0:
                logger.info(f"TheirStack returned 0 jobs or failed. Fallback triggered -> Fetching Serper Jobs for {company_name}...")
                jobs_res = await fetch_company_jobs_serper(company_name, company_slug, domain)

            full_lead_payload["job_openings"] = jobs_res
        else:
            logger.info(f"Skipping Jobs & Insights fetching for {company_name} (intent_score={final_score} < 80)")
            full_lead_payload["company_linkedin_id"] = None
            full_lead_payload["company_insights"] = None
            full_lead_payload["job_openings"] = None

        return full_lead_payload


def save_lead_to_db(lead_payload: Dict[str, Any]) -> None:
    """Persists qualified leads to the lead_snapshots database table."""
    db = SessionLocal()
    try:
        domain = lead_payload.get("domain")
        existing = db.query(LeadSnapshot).filter(LeadSnapshot.domain == domain).first()

        now_dt = datetime.now(timezone.utc)
        if existing:
            existing.company_name = lead_payload.get("company_name")
            existing.industry = lead_payload.get("industry")
            existing.employee_count = lead_payload.get("employee_count")
            existing.funding_stage = str(lead_payload.get("funding_stage"))
            existing.annual_revenue = lead_payload.get("annual_revenue")
            existing.intent_score = lead_payload.get("intent_score", 0)
            existing.tier = lead_payload.get("tier")
            existing.icp_fit = lead_payload.get("icp_fit")
            existing.badge = lead_payload.get("badge", "score_up")
            existing.why_now = lead_payload.get("why_now")
            existing.signal_tags = lead_payload.get("signal_tags")
            existing.ai_verdict = lead_payload.get("ai_verdict")
            existing.company_linkedin_id = lead_payload.get("company_linkedin_id")
            existing.company_insights = lead_payload.get("company_insights")
            existing.job_openings = lead_payload.get("job_openings")
            existing.full_payload = lead_payload
            existing.last_updated = now_dt
        else:
            snapshot = LeadSnapshot(
                id=lead_payload.get("id") or str(uuid.uuid4()),
                domain=domain,
                company_name=lead_payload.get("company_name"),
                company_segment=lead_payload.get("company_segment", "Growth Scale-up"),
                industry=lead_payload.get("industry"),
                employee_count=lead_payload.get("employee_count"),
                funding_stage=str(lead_payload.get("funding_stage")),
                annual_revenue=lead_payload.get("annual_revenue"),
                intent_score=lead_payload.get("intent_score", 0),
                signal_freshness=100,
                tier=lead_payload.get("tier"),
                icp_fit=lead_payload.get("icp_fit"),
                badge=lead_payload.get("badge", "new_today"),
                why_now=lead_payload.get("why_now"),
                signal_tags=lead_payload.get("signal_tags"),
                ai_verdict=lead_payload.get("ai_verdict"),
                company_linkedin_id=lead_payload.get("company_linkedin_id"),
                company_insights=lead_payload.get("company_insights"),
                job_openings=lead_payload.get("job_openings"),
                full_payload=lead_payload,
                last_updated=now_dt
            )
            db.add(snapshot)

        db.commit()
        logger.info(f"💾 Successfully saved {lead_payload.get('company_name')} ({domain}) to DB snapshot table.")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save lead snapshot for {lead_payload.get('domain')}: {e}")
    finally:
        db.close()

async def run_pipeline_batch(candidates: List[Dict[str, Any]], concurrency_limit: int = 2) -> List[Dict[str, Any]]:
    """Runs a batch of candidate companies through the streaming pipeline."""
    semaphore = asyncio.Semaphore(concurrency_limit)
    
    async def process_with_stagger(idx: int, cand: Dict[str, Any]):
        if idx > 0:
            await asyncio.sleep(idx * 0.5)
        return await process_single_company(cand, semaphore)

    tasks = [process_with_stagger(i, cand) for i, cand in enumerate(candidates)]
    
    results = await asyncio.gather(*tasks)
    
    qualified_leads = []
    for res in results:
        if res and isinstance(res, dict):
            # Save all qualified leads (Medium tier and above) to preserve data from expensive API calls
            if res.get("intent_score", 0) >= 40:
                save_lead_to_db(res)
                qualified_leads.append(res)
                
    return qualified_leads

async def trigger_ui_test_run(limit: int = 2) -> Dict[str, Any]:
    """Executed when user clicks 'Run Pipeline Test' on the UI."""
    batch, state = await get_ui_test_batch(limit=limit)
    if not batch:
        return {"status": "empty", "message": "No candidates to process.", "qualified_leads": [], "state": state}

    qualified_leads = await run_pipeline_batch(batch, concurrency_limit=2)
    return {
        "status": "success",
        "processed_count": len(batch),
        "qualified_count": len(qualified_leads),
        "qualified_leads": qualified_leads,
        "state": state
    }

async def trigger_midnight_cron_run(daily_quota: int = 30) -> Dict[str, Any]:
    """Executed automatically at 2:00 AM daily."""
    batch, state = await get_midnight_cron_batch(daily_quota=daily_quota)
    if not batch:
        return {"status": "empty", "message": "No candidates needed for midnight cron.", "qualified_leads": [], "state": state}

    qualified_leads = await run_pipeline_batch(batch, concurrency_limit=2)
    return {
        "status": "success",
        "processed_count": len(batch),
        "qualified_count": len(qualified_leads),
        "qualified_leads": qualified_leads,
        "state": state
    }


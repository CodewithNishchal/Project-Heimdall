import os
import json
import logging
import httpx
import re
from typing import Dict, Any
from backend.config import settings

from dotenv import dotenv_values, load_dotenv
from backend.config_manager import load_intent_config

logger = logging.getLogger("SocialClassifier")

async def classify_social_intent(post_text: str, author_bio: str = "") -> Dict[str, Any]:
    """
    Evaluates a social media post using Qwen2.5-7B on OpenRouter
    to determine if the author is seeking marketing/agency services.
    Returns a structured JSON dict.
    """
    env_vars = dotenv_values("backend/.env")
    openrouter_key = env_vars.get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY") or getattr(settings, "OPENROUTER_API_KEY", "")

    if openrouter_key:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {openrouter_key}",
            "HTTP-Referer": "https://heimdall.app",
            "X-Title": "Heimdall Lead Intel",
            "Content-Type": "application/json"
        }
        model_name = "inclusionai/ling-3.0-flash:free"
        provider_label = "OpenRouter Ling Flash (100% Free)"
    else:
        logger.warning("[OpenRouter Classifier] OPENROUTER_API_KEY is not set. Defaulting to seeking_provider.")
        return {"intent": "seeking_provider", "service_category": "marketing_agency", "confidence": 0.9}

    config = load_intent_config()
    target_topics = config.get("social_topics", ["B2B services"])
    topics_str = "/".join(target_topics)

    prompt = f"""
Classify this post about {topics_str}.
Return JSON ONLY matching this schema:
{{
  "intent": "seeking_provider" | "is_provider" | "unrelated" | "unclear",
  "service_category": "<extract the specific service they are seeking related to {topics_str}, or 'other'>",
  "confidence": 0.0-1.0
}}

Post: "{post_text}"
Author bio: "{author_bio}"
"""

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are a precise classifier that strictly outputs valid raw JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 200
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                logger.error(f"[{provider_label} HTTP {resp.status_code}] Response: {resp.text}")
                # Fallback to alternative active free model if primary free endpoint is temporarily busy
                payload["model"] = "openai/gpt-oss-20b:free"
                resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            # Safe JSON extraction
            cleaned_content = content.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(cleaned_content)
            logger.info(f"[{provider_label} Result] {parsed} for text: {post_text[:60]}...")
            return parsed
    except Exception as e:
        logger.error(f"[{provider_label} Classification Error]: {e}")
        return {"intent": "unclear", "service_category": "unknown", "confidence": 0.0, "error": str(e)}

# Tier 1 — Safe General Self-ID & Noise Pre-Filter Patterns (Zero False-Positive Risk for Buyers)
PRE_FILTER_SKIP_PATTERNS = [
    # Agency self-promotion (the seller, not the buyer)
    r"(?i)(we('re| are) (a|an|the)|our (agency|firm|company)) .*(help|specialize|offer|provide)",
    r"(?i)(book a (free )?call|schedule (a )?demo|link in bio|DM (us|me) for)",
    r"(?i)(taking on|accepting) (new )?(clients|projects)",
    r"(?i)(free (audit|consultation|strategy session))",

    # Job posts FROM agencies (they're hiring, not buying)
    r"(?i)(we('re| are) hiring|join our team|open (role|position) at .*(agency|marketing|staffing|recruiting))",

    # Already solved (past tense = no longer in market)
    r"(?i)(just hired|already found|went with|signed with|partnered with) .*(agency|firm|recruiter|consultant)",

    # Award and PR announcements
    r"(?i)(won (the|an) award|named (top|best)|ranked #|inc\.? (5000|500))",

    # Job Seekers & Candidates
    r"\bopen to work\b",
    r"\blooking for my next (role|opportunity|position)\b",
    r"\bactively (job hunting|seeking (new )?opportunities)\b",
    r"\blooking for (a |an )?(job|position|role|opportunity)\b",
    r"\bmy (resume|cv)\b",
    r"\bfree for candidates\b",
    r"\b(place|placing) (me|you|candidates) in\b",
    r"\bwe(’|')ve filled (the|this) (role|position)\b",
    # FIX: Negative lookahead spares VP/Chief/Head of/Director/President announcements
    r"\bplease welcome (our|the) (newest|newly hired)\b(?!.{0,40}\b(VP|Chief|Head of|Director|President)\b)",
]

AGENCY_PROMO_DENYLIST_GENERAL = [
    r"\bbook a call\b",
    r"\bdm (us|me) (for|to)\b",
    r"\bschedule a (free )?(call|consultation)\b",
    r"\bour (recruiters|placements)\b",
    r"\bwe(’|')ve placed (over )?\d+\b",
    r"\bcase stud(y|ies)\b",
    r"\brun our (free )?(diagnostic|audit)\b",
]

NICHE_SAFE_SELF_ID_PHRASES = {
    "recruitment": ["our staffing firm", "our RPO services", "leading headhunter firm", "our recruiting agency"],
    "recruitment_agencies": ["our staffing firm", "our RPO services", "leading headhunter firm", "our recruiting agency"],
    "marketing": ["our marketing agency", "our growth agency", "our PPC agency", "our performance marketing agency"],
    "marketing_agencies": ["our marketing agency", "our growth agency", "our PPC agency", "our performance marketing agency"],
    "appointment_setting": ["our SDR agency", "our outbound agency", "our appointment setting agency", "our cold email agency"],
}

def is_prefiltered(text: str, niche_id: str = "recruitment") -> tuple[bool, str]:
    text_lower = text.lower()
    patterns = (
        PRE_FILTER_SKIP_PATTERNS
        + AGENCY_PROMO_DENYLIST_GENERAL
        + [rf"\b{re.escape(p)}\b" for p in NICHE_SAFE_SELF_ID_PHRASES.get(niche_id, [])]
    )
    for pattern in patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True, pattern
    return False, ""

NICHE_CONFIG_TABLE = {
    "recruitment": {
        "niche_label": "RECRUITMENT / STAFFING AGENCY",
        "service_desc": "recruitment/staffing service or help filling roles",
        "hot_desc": "The author is directly looking to hire a recruitment/staffing service OR explicitly asking for help filling roles.",
        "warm_desc": "The author is expressing hiring pain that a recruitment agency could solve, but is NOT explicitly asking for a recruiter.",
        "skip_desc": "- A recruitment agency or recruiter promoting their own services\n- A job posting FROM a staffing firm\n- General industry news or thought leadership\n- Advice posts ('here's how to hire better')\n- Someone who already found their solution ('just hired an agency')\n- Internal company 'we're hiring' announcements",
        "guidance": "When in doubt between WARM and SKIP, lean toward WARM. When in doubt between HOT and WARM, lean toward HOT only if there's an explicit ask for external help."
    },
    "recruitment_agencies": {
        "niche_label": "RECRUITMENT / STAFFING AGENCY",
        "service_desc": "recruitment/staffing service or help filling roles",
        "hot_desc": "The author is directly looking to hire a recruitment/staffing service OR explicitly asking for help filling roles.",
        "warm_desc": "The author is expressing hiring pain that a recruitment agency could solve, but is NOT explicitly asking for a recruiter.",
        "skip_desc": "- A recruitment agency or recruiter promoting their own services\n- A job posting FROM a staffing firm\n- General industry news or thought leadership\n- Advice posts ('here's how to hire better')\n- Someone who already found their solution ('just hired an agency')\n- Internal company 'we're hiring' announcements",
        "guidance": "When in doubt between WARM and SKIP, lean toward WARM. When in doubt between HOT and WARM, lean toward HOT only if there's an explicit ask for external help."
    },
    "marketing": {
        "niche_label": "MARKETING AGENCY",
        "service_desc": "marketing agency, consultant, or specific marketing service provider",
        "hot_desc": "The author is directly looking for a marketing agency, consultant, or specific marketing service provider.",
        "warm_desc": "The author is expressing marketing pain that an agency could solve, but is NOT explicitly asking for an agency.",
        "skip_desc": "- A marketing agency promoting their own services or results\n- Thought leadership posts about marketing strategy\n- Marketing tool/software reviews\n- Generic marketing tips or how-to content\n- Someone who already has an agency ('our agency just launched')\n- Job postings for in-house marketing roles at an agency",
        "guidance": "CRITICAL DISTINCTION: A post saying 'just hired a great agency' is SKIP. A post saying 'thinking about hiring an agency' is HOT. A post saying 'our marketing sucks' without mentioning agencies is WARM."
    },
    "marketing_agencies": {
        "niche_label": "MARKETING AGENCY",
        "service_desc": "marketing agency, consultant, or specific marketing service provider",
        "hot_desc": "The author is directly looking for a marketing agency, consultant, or specific marketing service provider.",
        "warm_desc": "The author is expressing marketing pain that an agency could solve, but is NOT explicitly asking for an agency.",
        "skip_desc": "- A marketing agency promoting their own services or results\n- Thought leadership posts about marketing strategy\n- Marketing tool/software reviews\n- Generic marketing tips or how-to content\n- Someone who already has an agency ('our agency just launched')\n- Job postings for in-house marketing roles at an agency",
        "guidance": "CRITICAL DISTINCTION: A post saying 'just hired a great agency' is SKIP. A post saying 'thinking about hiring an agency' is HOT. A post saying 'our marketing sucks' without mentioning agencies is WARM."
    },
    "appointment_setting": {
        "niche_label": "APPOINTMENT SETTING / OUTBOUND SALES AGENCY",
        "service_desc": "outbound sales help, SDR services, appointment setting, cold email agencies, or lead generation partners",
        "hot_desc": "The author is directly looking for outbound sales help, SDR services, appointment setting, cold email agencies, or lead generation partners.",
        "warm_desc": "The author is expressing sales pipeline pain that an appointment setting agency could solve, but is NOT explicitly asking for one.",
        "skip_desc": "- An appointment setting or lead gen agency promoting their own services\n- Cold email tips and outbound advice content\n- SDR tool reviews\n- Job postings for SDR/BDR roles at a lead gen agency\n- Success stories ('we hired an outbound agency')\n- General sales advice or sales methodology discussions",
        "guidance": "CRITICAL DISTINCTION: 'How do I improve my cold email?' is usually someone doing their own outbound (SKIP unless they express frustration/failure). 'Our cold email isn't working and we've tried everything' is WARM because they've hit a wall."
    }
}


async def batch_classify_social_intent(posts: list[dict], return_usage: bool = False):
    """
    Evaluates a batch of social media posts (max 20) using Ling/Qwen or Mistral AI.
    Applies PRE_FILTER_SKIP_PATTERNS first to save token costs.
    Returns a list of structured JSON dicts matching qualified HOT/WARM leads.
    """
    if not posts:
        return ([], {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}) if return_usage else []

    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0

    config = load_intent_config()
    active_niche = config.get("active_niche", "recruitment")
    if active_niche not in NICHE_CONFIG_TABLE:
        active_niche = "recruitment"

    # Step 1: Pre-filter out obvious agency noise/self-promo using regex (Zero LLM Cost)
    candidates_for_llm = []
    skipped_pre_filter = 0

    for i, p in enumerate(posts):
        text = str(p.get("content") or p.get("raw_text") or "").strip()
        filtered, pat = is_prefiltered(text, niche_id=active_niche)
        if filtered:
            skipped_pre_filter += 1
            continue
        candidates_for_llm.append((i, p, text))

    if skipped_pre_filter > 0:
        logger.info(f"[Pre-Filter] Saved LLM calls on {skipped_pre_filter}/{len(posts)} posts for niche '{active_niche}'.")

    if not candidates_for_llm:
        return ([], {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}) if return_usage else []

    env_vars = dotenv_values("backend/.env")
    mistral_key = env_vars.get("MISTRAL_API_KEY") or os.getenv("MISTRAL_API_KEY") or getattr(settings, "MISTRAL_API_KEY", "")
    gemini_key = env_vars.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", "")
    openrouter_key = env_vars.get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY") or getattr(settings, "OPENROUTER_API_KEY", "")

    niches_dict = config.get("niches", {})
    niche_info = niches_dict.get(active_niche, {})
    target_industries = ", ".join(niche_info.get("target_industries", ["Technology", "B2B SaaS"]))
    min_emp = niche_info.get("min_employees", 20)
    max_emp = niche_info.get("max_employees", 2000)
    company_size_range = f"{min_emp}-{max_emp}"

    spec = NICHE_CONFIG_TABLE[active_niche]
    
    system_instruction = "You are a strict JSON classifier. Output ONLY a valid JSON array — no markdown code fences, no preamble, no text outside the array. If nothing qualifies, output exactly: []"

    id_to_post_map = {orig_idx: p for orig_idx, p, _ in candidates_for_llm}
    relevant_posts = []

    # Process candidates in sub-batches of 15 to prevent max_tokens truncation
    chunk_size = 15
    for chunk_start in range(0, len(candidates_for_llm), chunk_size):
        chunk = candidates_for_llm[chunk_start:chunk_start + chunk_size]
        lean_indexed_input = []
        for orig_idx, p, text in chunk:
            lines = [l for l in text.splitlines() if l.strip()]
            extracted_text = "\n".join(lines[:10]) if len(lines) > 10 else text
            headcount_info = p.get("employee_count") or p.get("company_size") or "Unknown"
            lean_indexed_input.append({
                "id": orig_idx,
                "content": extracted_text,
                "headcount_context": f"Estimated Company Size: {headcount_info}"
            })

        prompt = f"""You are classifying social media posts for a {spec['niche_label']}'s lead generation tool.

Read the post and determine: Is the author someone who could become a client of a {spec['service_desc']}?

TARGET ICP: {target_industries}, {company_size_range} employees.

CLASSIFY AS:
HOT — {spec['hot_desc']}
WARM — {spec['warm_desc']}
SKIP — Any of the following:
{spec['skip_desc']}

{spec['guidance']}

OUTPUT SCHEMA (JSON array of objects ONLY):
[
  {{
    "id": <integer, must match input id — never invent ids>,
    "classification": "HOT" | "WARM" | "SKIP",
    "category": "funding" | "hiring" | "agency_intent" | "product" | "expansion" | "leadership" | "social_intent",
    "reason": "<one sentence explaining why — shown on lead card>",
    "confidence": <integer 0-100>,
    "buyer_signal_quote": "<verbatim quote max 12 words>",
    "location_mentioned": "<city/state or null>",
    "budget_mentioned": "<budget or null>",
    "urgency_indicators": ["<ASAP etc>"],
    "company_size_mentioned": "<size or null>",
    "industry_mentioned": "<industry or null>",
    "competitor_mentioned": "<competing agency or null>",
    "pain_indicators": ["<specific pain phrases>"]
  }}
]

Input batch of indexed posts:
{json.dumps(lean_indexed_input, indent=2)}
"""

        content = None

        # Route 1: Mistral AI (ministral-3b-2512)
        if mistral_key:
            m_url = "https://api.mistral.ai/v1/chat/completions"
            m_headers = {
                "Authorization": f"Bearer {mistral_key}",
                "Content-Type": "application/json"
            }
            m_payload = {
                "model": "ministral-3b-2512",
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 4000
            }
            try:
                logger.info(f"[SocialClassifier] Classifying chunk ({len(chunk)} posts) using Mistral AI (ministral-3b-2512)...")
                async with httpx.AsyncClient(timeout=45.0) as client:
                    resp = await client.post(m_url, headers=m_headers, json=m_payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content")
                        usage = data.get("usage", {})
                        total_prompt_tokens += usage.get("prompt_tokens", 0)
                        total_completion_tokens += usage.get("completion_tokens", 0)
                        total_tokens += usage.get("total_tokens", 0)
                    else:
                        m_payload["model"] = "ministral-3b-latest"
                        resp = await client.post(m_url, headers=m_headers, json=m_payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            content = data.get("choices", [{}])[0].get("message", {}).get("content")
                            usage = data.get("usage", {})
                            total_prompt_tokens += usage.get("prompt_tokens", 0)
                            total_completion_tokens += usage.get("completion_tokens", 0)
                            total_tokens += usage.get("total_tokens", 0)
            except Exception as m_err:
                logger.warning(f"[SocialClassifier] Mistral AI chunk error ({m_err}).")

        # Route 2: Gemini API fallback
        if not content and gemini_key:
            try:
                from google import genai
                logger.info(f"[SocialClassifier] Classifying chunk ({len(chunk)} posts) using Gemini API...")
                g_client = genai.Client(api_key=gemini_key)
                g_response = g_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"{system_instruction}\n\n{prompt}"
                )
                content = g_response.text
            except Exception as g_err:
                logger.warning(f"[SocialClassifier] Gemini API chunk error ({g_err}).")

        # Route 3: OpenRouter fallback
        if not content and openrouter_key:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {openrouter_key}",
                "HTTP-Referer": "https://heimdall.app",
                "X-Title": "Heimdall Lead Intel",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "openrouter/free",
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 4000
            }
            try:
                async with httpx.AsyncClient(timeout=45.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content")
            except Exception as or_err:
                logger.error(f"[OpenRouter Error] {or_err}")

        if not content:
            continue

        cleaned_content = content.replace("```json", "").replace("```", "").strip()
        match = re.search(r'\[.*\]', cleaned_content, re.DOTALL)
        if match:
            cleaned_content = match.group(0)
        
        parsed_array = None
        try:
            parsed_array = json.loads(cleaned_content)
        except json.JSONDecodeError:
            # Attempt 1: Automatically recover truncated JSON array by closing after last complete object
            try:
                last_brace = cleaned_content.rfind("}")
                if last_brace != -1:
                    fixed_str = cleaned_content[:last_brace + 1] + "\n]"
                    parsed_array = json.loads(fixed_str)
                    logger.info("[SocialClassifier] Successfully recovered truncated JSON chunk via auto-closure.")
            except Exception:
                parsed_array = None

        if not parsed_array or not isinstance(parsed_array, list):
            logger.warning(f"[SocialClassifier] JSON parsing failed for chunk. Snippet: {cleaned_content[:80]}...")
            continue
            
        for item in parsed_array:
            if isinstance(item, dict) and "id" in item:
                idx = item.get("id")
                classification = str(item.get("cls") or item.get("classification") or "SKIP").upper()
                
                if classification in ["HOT", "WARM"] and idx in id_to_post_map:
                    original_post = dict(id_to_post_map[idx])
                    reason = item.get("rsn") or item.get("reason") or "Buying signal detected."
                    quote = item.get("qte") or item.get("buyer_signal_quote") or ""
                    conf_raw = item.get("conf") if item.get("conf") is not None else item.get("confidence")
                    
                    original_post["classification"] = classification
                    original_post["reason"] = reason
                    original_post["summary"] = f'"{quote}" - {reason}' if quote else reason
                    original_post["category"] = item.get("category") or "social_intent"
                    original_post["confidence"] = (conf_raw or 90) / 100.0 if isinstance(conf_raw, (int, float)) else 0.90
                    original_post["location_mentioned"] = item.get("loc") if "loc" in item else item.get("location_mentioned")
                    original_post["budget_mentioned"] = item.get("bdg") if "bdg" in item else item.get("budget_mentioned")
                    original_post["urgency_indicators"] = (item.get("urg") if "urg" in item else item.get("urgency_indicators")) or []
                    original_post["company_size_mentioned"] = item.get("company_size_mentioned")
                    original_post["industry_mentioned"] = item.get("industry_mentioned")
                    original_post["competitor_mentioned"] = item.get("cmp") if "cmp" in item else item.get("competitor_mentioned")
                    original_post["pain_indicators"] = item.get("pain_indicators") or []
                    relevant_posts.append(original_post)

    usage_stats = {
        "prompt_tokens": total_prompt_tokens,
        "completion_tokens": total_completion_tokens,
        "total_tokens": total_tokens
    }

    logger.info(f"[SocialClassifier] Filtered {len(posts)} posts -> {len(candidates_for_llm)} to LLM -> Matched {len(relevant_posts)} HOT/WARM leads.")
    logger.info(f"[Mistral Token Usage] Prompt: {total_prompt_tokens} | Completion: {total_completion_tokens} | Total: {total_tokens} tokens")

    if return_usage:
        return relevant_posts, usage_stats
    return relevant_posts

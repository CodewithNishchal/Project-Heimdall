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
]

NICHE_PROMPTS = {
    "recruitment_agencies": """You are classifying social media posts for a RECRUITMENT / STAFFING AGENCY's lead generation tool.

Read the post and determine: Is the author someone who could become a client of a recruitment agency?

CLASSIFY AS:
HOT — The author is directly looking to hire a recruitment/staffing service OR explicitly asking for help filling roles.
WARM — The author is expressing hiring pain that a recruitment agency could solve, but is NOT explicitly asking for a recruiter.
SKIP — Recruitment agency promoting own services, job posting FROM a staffing firm, thought leadership, advice, or internal company hiring announcements.

OUTPUT SCHEMA (JSON array of objects ONLY):
[
  {
    "id": <integer, must match input id>,
    "classification": "HOT" | "WARM" | "SKIP",
    "reason": "<one sentence explaining why — shown on lead card>",
    "confidence": <integer 0-100>,
    "buyer_signal_quote": "<verbatim quote max 12 words>",
    "location_mentioned": "<city/state or null>",
    "budget_mentioned": "<budget or null>",
    "urgency_indicators": ["<ASAP etc>"],
    "competitor_mentioned": "<competitor name or null>"
  }
]""",

    "marketing_agencies": """You are classifying social media posts for a MARKETING AGENCY's lead generation tool.

Read the post and determine: Is the author someone who could become a client of a marketing agency?

CLASSIFY AS:
HOT — The author is directly looking for a marketing agency, consultant, or specific marketing service provider.
WARM — The author is expressing marketing pain that an agency could solve, but is NOT explicitly asking for an agency.
SKIP — Marketing agency promoting own services, thought leadership, tool reviews, generic tips, or past-tense "just hired an agency".

OUTPUT SCHEMA (JSON array of objects ONLY):
[
  {
    "id": <integer, must match input id>,
    "classification": "HOT" | "WARM" | "SKIP",
    "reason": "<one sentence explaining why — shown on lead card>",
    "confidence": <integer 0-100>,
    "buyer_signal_quote": "<verbatim quote max 12 words>",
    "location_mentioned": "<city/state or null>",
    "budget_mentioned": "<budget or null>",
    "urgency_indicators": ["<ASAP etc>"],
    "competitor_mentioned": "<competitor name or null>"
  }
]""",

    "appointment_setting": """You are classifying social media posts for an APPOINTMENT SETTING / OUTBOUND SALES AGENCY's lead generation tool.

Read the post and determine: Is the author someone who could become a client of an appointment setting or outbound sales agency?

CLASSIFY AS:
HOT — The author is directly looking for outbound sales help, SDR services, appointment setting, cold email agencies, or lead gen partners.
WARM — The author is expressing sales pipeline pain that an appointment setting agency could solve, but is NOT explicitly asking for one.
SKIP — SDR agency self-promotion, cold email tips, SDR tool reviews, or success stories.

OUTPUT SCHEMA (JSON array of objects ONLY):
[
  {
    "id": <integer, must match input id>,
    "classification": "HOT" | "WARM" | "SKIP",
    "reason": "<one sentence explaining why — shown on lead card>",
    "confidence": <integer 0-100>,
    "buyer_signal_quote": "<verbatim quote max 12 words>",
    "location_mentioned": "<city/state or null>",
    "budget_mentioned": "<budget or null>",
    "urgency_indicators": ["<ASAP etc>"],
    "competitor_mentioned": "<competitor name or null>"
  }
]"""
}


async def batch_classify_social_intent(posts: list[dict]) -> list[dict]:
    """
    Evaluates a batch of social media posts (max 20) using Ling/Qwen on OpenRouter.
    Applies PRE_FILTER_SKIP_PATTERNS first to save token costs.
    Returns a list of structured JSON dicts matching qualified HOT/WARM leads.
    """
    if not posts:
        return []

    # Step 1: Pre-filter out obvious agency noise/self-promo using regex (Zero LLM Cost)
    candidates_for_llm = []
    skipped_pre_filter = 0

    for i, p in enumerate(posts):
        text = str(p.get("content") or p.get("raw_text") or "").strip()
        if any(re.search(pat, text) for pat in PRE_FILTER_SKIP_PATTERNS):
            skipped_pre_filter += 1
            continue
        candidates_for_llm.append((i, p, text))

    if skipped_pre_filter > 0:
        logger.info(f"[Pre-Filter] Saved LLM calls on {skipped_pre_filter}/{len(posts)} posts (agency self-promo/noise filtered).")

    if not candidates_for_llm:
        return []

    env_vars = dotenv_values("backend/.env")
    openrouter_key = env_vars.get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY") or getattr(settings, "OPENROUTER_API_KEY", "")

    if not openrouter_key:
        logger.warning("[OpenRouter Classifier] OPENROUTER_API_KEY is not set. Defaulting to pre-filtered candidate list.")
        return [dict(p) for _, p, _ in candidates_for_llm]

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "HTTP-Referer": "https://heimdall.app",
        "X-Title": "Heimdall Lead Intel",
        "Content-Type": "application/json"
    }
    model_name = "meta-llama/llama-3.3-70b-instruct"
    provider_label = "OpenRouter Llama-3.3-70B (Batch)"

    # Extract lean indexed JSON containing only id and up to 10 lines of content
    lean_indexed_input = []
    for orig_idx, p, text in candidates_for_llm:
        lines = [l for l in text.splitlines() if l.strip()]
        extracted_text = "\n".join(lines[:10]) if len(lines) > 10 else text
        lean_indexed_input.append({
            "id": orig_idx,
            "content": extracted_text
        })

    config = load_intent_config()
    active_niche = config.get("active_niche", "marketing_agencies")
    active_subtype = config.get("active_subtype", "tech_recruitment")
    
    subtypes_dict = config.get("recruitment_subtypes", {})
    subtype_info = subtypes_dict.get(active_subtype, {})
    subtype_label = subtype_info.get("label", "General ICP Target")
    subtype_rules = subtype_info.get("rules", "Prioritize active team expansion and hiring signals.")
    exclude_terms = ", ".join(subtype_info.get("exclude_terms", ["service agency", "consultancy", "staffing firm"]))

    niche_prompt = NICHE_PROMPTS.get(active_niche, NICHE_PROMPTS["marketing_agencies"])

    system_instruction = "You are a strict JSON classifier. Output ONLY a valid JSON array — no markdown code fences, no preamble, no text outside the array. If nothing qualifies, output exactly: []"

    prompt = f"""{niche_prompt}

ACTIVE SUB-TYPE SPECIFIC RULES ({subtype_label}):
- Core Focus Rule: {subtype_rules}
- Explicit Disqualifications: Skip posts from agencies or service providers matching: {exclude_terms}

Input batch of indexed posts:
{json.dumps(lean_indexed_input, indent=2)}
"""

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 2000
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                logger.warning(f"[{provider_label} HTTP {resp.status_code}] Falling back to deepseek/deepseek-chat")
                payload["model"] = "deepseek/deepseek-chat"
                resp = await client.post(url, headers=headers, json=payload)
            
            resp.raise_for_status()
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content")
            
            if not content:
                logger.error(f"[{provider_label}] LLM returned empty content: {data}")
                return []
                
            cleaned_content = content.replace("```json", "").replace("```", "").strip()
            match = re.search(r'\[.*\]', cleaned_content, re.DOTALL)
            if match:
                cleaned_content = match.group(0)
            
            try:
                parsed_array = json.loads(cleaned_content)
            except json.JSONDecodeError as e:
                logger.warning(f"[{provider_label}] JSON parsing failed. Snippet: {cleaned_content[:80]}...")
                return []
            
            if not isinstance(parsed_array, list):
                return []
                
            id_to_post_map = {orig_idx: p for orig_idx, p, _ in candidates_for_llm}
            relevant_posts = []
            
            for item in parsed_array:
                if isinstance(item, dict) and "id" in item:
                    idx = item.get("id")
                    classification = str(item.get("classification", "SKIP")).upper()
                    
                    if classification in ["HOT", "WARM"] and idx in id_to_post_map:
                        original_post = dict(id_to_post_map[idx])
                        reason = item.get("reason") or "Buying signal detected."
                        quote = item.get("buyer_signal_quote") or ""
                        
                        original_post["classification"] = classification
                        original_post["reason"] = reason
                        original_post["summary"] = f'"{quote}" - {reason}' if quote else reason
                        original_post["confidence"] = (item.get("confidence") or 90) / 100.0 if isinstance(item.get("confidence"), (int, float)) else 0.90
                        original_post["location_mentioned"] = item.get("location_mentioned")
                        original_post["budget_mentioned"] = item.get("budget_mentioned")
                        original_post["urgency_indicators"] = item.get("urgency_indicators") or []
                        original_post["competitor_mentioned"] = item.get("competitor_mentioned")
                        relevant_posts.append(original_post)
                
            logger.info(f"[{provider_label}] Filtered {len(posts)} posts -> {len(candidates_for_llm)} to LLM -> Matched {len(relevant_posts)} HOT/WARM leads.")
            return relevant_posts
            
    except Exception as e:
        logger.error(f"[{provider_label} Classification Error]: {e}")
        return [{"intent": "unclear", "confidence": 0.0, "error": str(e)} for _ in posts]


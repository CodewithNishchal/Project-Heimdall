import os
import json
import logging
import httpx
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

async def batch_classify_social_intent(posts: list[dict]) -> list[dict]:
    """
    Evaluates a batch of social media posts (max 20) using Ling/Qwen on OpenRouter.
    Returns a list of structured JSON dicts matching the input order.
    """
    if not posts:
        return []

    env_vars = dotenv_values("backend/.env")
    openrouter_key = env_vars.get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY") or getattr(settings, "OPENROUTER_API_KEY", "")

    if not openrouter_key:
        logger.warning("[OpenRouter Classifier] OPENROUTER_API_KEY is not set. Defaulting all to seeking_provider.")
        return [{"intent": "seeking_provider", "service_category": "marketing_agency", "confidence": 0.9} for _ in posts]

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "HTTP-Referer": "https://heimdall.app",
        "X-Title": "Heimdall Lead Intel",
        "Content-Type": "application/json"
    }
    model_name = "openai/gpt-oss-20b:free"
    provider_label = "OpenRouter Auto-OSS (Batch)"

    input_data = []
    for i, p in enumerate(posts):
        input_data.append({
            "id": i,
            "text": p.get("content", "")[:300],
            "author": p.get("author_name", "")
        })

    config = load_intent_config()
    target_topics = config.get("social_topics", ["B2B services"])
    topics_str = "/".join(target_topics)

    prompt = f"""
You are an expert lead classifier for {topics_str}.
Evaluate this batch of {len(posts)} social media posts.

For EACH post, determine if the author is seeking services related to: {topics_str}.
Return a JSON array of objects. EACH object MUST have this exact schema and match the input 'id':
[
  {{
    "id": <integer>,
    "intent": "seeking_provider" | "is_provider" | "unrelated" | "unclear",
    "service_category": "<extract the specific service they are seeking related to {topics_str}, or 'other'>",
    "confidence": 0.0-1.0
  }}
]

Input batch:
{json.dumps(input_data, indent=2)}
"""

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You strictly output a valid JSON array of objects."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 4000
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                logger.error(f"[{provider_label} HTTP {resp.status_code}] Response: {resp.text}")
                payload["model"] = "openai/gpt-oss-20b:free"
                resp = await client.post(url, headers=headers, json=payload)
            
            resp.raise_for_status()
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content")
            
            if not content:
                logger.error(f"[{provider_label}] LLM returned empty content: {data}")
                return [{"intent": "unclear"} for _ in posts]
                
            cleaned_content = content.replace("```json", "").replace("```", "").strip()
            
            try:
                parsed_array = json.loads(cleaned_content)
            except json.JSONDecodeError as e:
                logger.error(f"[{provider_label}] JSON parsing failed: {e}. Raw content: {cleaned_content}")
                return [{"intent": "unclear", "confidence": 0.0, "error": f"JSON Error: {e}"} for _ in posts]
            
            if not isinstance(parsed_array, list):
                logger.error(f"[{provider_label}] LLM returned a non-array: {parsed_array}")
                return [{"intent": "unclear"} for _ in posts]
                
            # Create a lookup dictionary mapping id to result
            result_map = {item.get("id"): item for item in parsed_array if isinstance(item, dict) and "id" in item}
            
            # Map back to original posts ensuring order is perfectly maintained
            final_results = []
            for i in range(len(posts)):
                final_results.append(result_map.get(i, {"intent": "unclear", "confidence": 0.0}))
                
            logger.info(f"[{provider_label}] Successfully batch-classified {len(final_results)} posts.")
            return final_results
            
    except Exception as e:
        logger.error(f"[{provider_label} Classification Error]: {e}")
        return [{"intent": "unclear", "confidence": 0.0, "error": str(e)} for _ in posts]


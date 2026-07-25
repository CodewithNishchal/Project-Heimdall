import os
import json
import logging
import httpx
from typing import Dict, Any
from backend.config import settings

from dotenv import dotenv_values, load_dotenv

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

    prompt = f"""
Classify this post about marketing/advertising services.
Return JSON ONLY matching this schema:
{{
  "intent": "seeking_provider" | "is_provider" | "unrelated" | "unclear",
  "service_category": "marketing_agency" | "ppc" | "seo" | "cmo" | "facebook_ads" | "growth_marketing" | "lead_gen" | "franchise_marketing" | "other",
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

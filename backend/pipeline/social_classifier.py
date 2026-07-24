import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger("SocialClassifier")

def get_groq_client():
    try:
        from groq import Groq
    except ImportError:
        logger.error("groq package not installed. Run: uv pip install groq")
        return None
        
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.error("GROQ_API_KEY is not set in the environment.")
        return None
    return Groq(api_key=api_key)

async def classify_social_intent(post_text: str, author_bio: str = "") -> Dict[str, Any]:
    """
    Evaluates a social media post to determine if the author is seeking marketing/agency services.
    Returns a structured JSON dict.
    """
    client = get_groq_client()
    if not client:
        # Fallback to seeking_provider if Groq is not configured, so we don't lose the lead
        return {"intent": "seeking_provider", "service_category": "unknown", "confidence": 1.0}

    prompt = f"""
Classify this post about marketing/advertising services.
Return JSON only matching this schema:
{{
  "intent": "seeking_provider" | "is_provider" | "unrelated" | "unclear",
  "service_category": "marketing_agency" | "ppc" | "seo" | "cmo" | "facebook_ads" | "growth_marketing" | "lead_gen" | "franchise_marketing" | "other",
  "confidence": 0.0-1.0
}}

Post: "{post_text}"
Author bio: "{author_bio}"
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a precise classifier that strictly outputs valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=150,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        logger.error(f"Groq classification error: {e}")
        # Fallback in case of error
        return {"intent": "unclear", "service_category": "unknown", "confidence": 0.0}

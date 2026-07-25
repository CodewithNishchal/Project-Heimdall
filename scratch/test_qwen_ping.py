import os
import asyncio
import time
import httpx
from dotenv import dotenv_values

async def test_ling_flash():
    env_vars = dotenv_values("backend/.env")
    openrouter_key = env_vars.get("OPENROUTER_API_KEY")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "HTTP-Referer": "https://heimdall.app",
        "X-Title": "Heimdall Lead Intel",
        "Content-Type": "application/json"
    }
    
    post_text = "Looking for a performance marketing agency in the US to scale our e-commerce supplement brand. Must have experience with Meta & Google Ads."
    prompt = f"""
Classify this post about marketing/advertising services.
Return JSON ONLY matching this schema:
{{
  "intent": "seeking_provider" | "is_provider" | "unrelated" | "unclear",
  "service_category": "marketing_agency" | "ppc" | "seo" | "cmo" | "facebook_ads" | "growth_marketing" | "lead_gen" | "other",
  "confidence": 0.0-1.0
}}

Post: "{post_text}"
"""

    payload = {
        "model": "inclusionai/ling-3.0-flash:free",
        "messages": [
            {"role": "system", "content": "You are a precise classifier that strictly outputs valid raw JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 150
    }
    
    print("Pinging model: inclusionai/ling-3.0-flash:free ...\n")
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            elapsed = time.time() - start
            print(f"Latency: {elapsed:.2f}s | HTTP Status: {resp.status_code}")
            print(f"Response: {resp.text}\n")
    except Exception as e:
        print(f"Error testing model: {e}\n")

if __name__ == "__main__":
    asyncio.run(test_ling_flash())

import asyncio
import logging
import sys
import os
import httpx
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.pipeline.enrichment import (
    fetch_reddit_posts,
    fetch_twitter_posts
)
from backend.config import settings
from dotenv import dotenv_values

# Discard obvious end-user chatter BEFORE hitting Llama
DISCARD_PHRASES = [
    "alternative to", "alternatives to", "cheaper than", 
    "vs", "how to fix", "error code", "is down", 
    "pricing is too high", "anyone else having issues"
]

def pre_filter_social_posts(posts: list[dict], company_domain: str) -> list[dict]:
    clean_posts = []
    for post in posts:
        text = (post.get("title", "") + " " + post.get("selftext", "") + " " + post.get("text", "")).lower()
        
        # If the post contains negative end-user phrases AND does not mention official domain/handles, skip it
        if any(phrase in text for phrase in DISCARD_PHRASES) and company_domain not in text:
            continue
            
        clean_posts.append(post)
    return clean_posts

# Enable concise logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpx").setLevel(logging.WARNING)

async def filter_relevant_posts(posts: list[dict], company_name: str, domain: str) -> list[dict]:
    env_vars = dotenv_values("backend/.env")
    openrouter_key = env_vars.get("OPENROUTER_API_KEY") or getattr(settings, "OPENROUTER_API_KEY", "")
    if not openrouter_key:
        print("Missing OpenRouter API Key")
        return []

    prompt = f"""You are a B2B Sales Intelligence Classifier. Your sole job is to evaluate social media posts (Reddit/X) and keep ONLY high-intent lead generation signals or company growth milestones.

TARGET COMPANY: {company_name} ({domain})

==================================================
1. INCLUSION CRITERIA (Keep if ANY apply):
==================================================
- Execs/Founders announcing new funding, revenue milestones ($1M+ ARR), or major product launches.
- Company leaders explicitly hiring for new roles or seeking external agencies/vendors (e.g., "Looking for a security auditor", "Need a dev agency").
- Verified media/press reporting on corporate expansion, partnerships, or scale.

==================================================
2. EXCLUSION CRITERIA (STRICTLY REJECT if ANY apply):
==================================================
- End-users seeking software alternatives (e.g., "Any cheaper alternative to Resend?", "Resend vs SendGrid").
- End-users asking for tech support, bug fixes, or documentation help.
- General product reviews, individual developer opinions, or casual forum banter.
- Non-English posts or posts about unrelated physical products/places with the same name.

==================================================
3. REQUIRED CLASSIFICATION STEPS:
==================================================
Step 1: Identify WHO is speaking (Company Founder/Exec vs. Random End-User).
Step 2: Identify WHAT is being expressed (Company Buying/Scaling Intent vs. End-User Software Usage).
Step 3: If it is an End-User asking questions or comparing software, set "is_lead_intent": false.

==================================================
OUTPUT FORMAT (JSON ONLY):
==================================================
Return an array of evaluations matching the exact number of Input Posts:
[
  {{
    "is_lead_intent": true | false,
    "signal_category": "COMPANY_GROWTH | HIRING_SPIKE | VENDOR_REQUEST | END_USER_CHATTER | SUPPORT",
    "rejection_reason": "Brief explanation if set to false, or empty if true",
    "confidence_score": 0.0 - 1.0,
    "verbatim_quote": "Exact quote from text if is_lead_intent is true"
  }}
]

Here are examples of how you should classify:
[
  {{
    "input_text": "Any cheaper alternative to Resend for transactional emails?",
    "output": {{
      "is_lead_intent": false,
      "signal_category": "END_USER_CHATTER",
      "rejection_reason": "Post is from an end-user asking for software alternatives, not a company buying trigger.",
      "confidence_score": 0.95,
      "verbatim_quote": ""
    }}
  }},
  {{
    "input_text": "We just closed our $18M Series A led by a16z to scale Resend! We are hiring 5 senior engineers in SF.",
    "output": {{
      "is_lead_intent": true,
      "signal_category": "COMPANY_GROWTH",
      "rejection_reason": "",
      "confidence_score": 0.99,
      "verbatim_quote": "We just closed our $18M Series A led by a16z to scale Resend!"
    }}
  }}
]
    
Raw Input Posts:
{json.dumps(posts, indent=2)}
"""

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "HTTP-Referer": "https://heimdall.app",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a JSON-only data filter. Output ONLY a raw JSON array of objects."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            cleaned = content.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned)
    except Exception as e:
        print(f"LLM Error: {e}")
        return []

async def main():
    print("\n" + "="*50)
    print("🚀 SCRAPEBADGER + OPENROUTER ISOLATED TESTER")
    print("="*50 + "\n")
    
    if len(sys.argv) > 1:
        company_name = sys.argv[1]
        domain = sys.argv[2] if len(sys.argv) > 2 else ""
    else:
        company_name = input("Enter Target Company Name: ").strip()
        domain = input("Enter Domain (optional): ").strip()

    print(f"\n[1/3] FETCHING SCRAPEBADGER POSTS FOR: {company_name}")
    print("-" * 50)

    async with httpx.AsyncClient(timeout=15.0) as client:
        print("🦡 Sweeping Reddit and X concurrently...")
        rd_posts, tw_posts = await asyncio.gather(
            fetch_reddit_posts(client, company_name, domain),
            fetch_twitter_posts(client, company_name, domain)
        )
        
        print(f"   => Found Reddit Discussions: {len(rd_posts)}")
        print(f"   => Found X/Twitter Posts: {len(tw_posts)}")

    all_posts = []
    for p in rd_posts: p["_platform"] = "Reddit"; all_posts.append(p)
    for p in tw_posts: p["_platform"] = "X"; all_posts.append(p)

    if not all_posts:
        print("\nNo posts found. Exiting.")
        return
        
    print(f"\n[2/3] APPLYING PYTHON KEYWORD PRE-FILTER...")
    clean_posts = pre_filter_social_posts(all_posts, domain)
    print(f"   => Filter dropped {len(all_posts) - len(clean_posts)} generic support/chatter threads.")
    print(f"   => Sending {len(clean_posts)} posts to Llama API for Deep Classification...\n")
    
    if not clean_posts:
        print("\nNo posts survived the pre-filter. Exiting.")
        return

    filtered = await filter_relevant_posts(clean_posts, company_name, domain)
    
    print("\n[3/3] LLM FILTERED RESULTS (JSON)")
    print("-" * 50)
    print(json.dumps(filtered, indent=2))

if __name__ == "__main__":
    asyncio.run(main())

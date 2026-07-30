import os
import sys
import json
import httpx
from dotenv import dotenv_values

def test_mistral_basic():
    print("=" * 70)
    print("🚀 MISTRAL AI BASIC PROMPT & CLASSIFICATION PING TEST")
    print("=" * 70)

    env_vars = dotenv_values("backend/.env")
    key = env_vars.get("MISTRAL_API_KEY") or os.getenv("MISTRAL_API_KEY", "")

    if not key:
        print("❌ MISTRAL_API_KEY missing in backend/.env")
        return

    print(f"Key: {key[:8]}...{key[-4:] if len(key) > 4 else ''}\n")

    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    # Sample prompt with 3 posts
    sample_posts = [
        {"id": 0, "content": "Looking for a digital marketing agency to manage our Meta and Google ads for our e-commerce store. Recommendations appreciated!"},
        {"id": 1, "content": "We are a full service growth marketing agency helping SaaS companies scale to $10M ARR. DM for a free audit."},
        {"id": 2, "content": "Hiring a senior digital marketing manager to join our internal marketing team in London."}
    ]

    prompt = f"""You are a strict JSON classifier.
Determine if each post author is looking to hire a marketing agency.

CLASSIFY AS:
HOT - Explicitly looking for a marketing agency or service provider.
SKIP - Agency self-promotion or internal job hiring.

Return JSON array ONLY:
[
  {{
    "id": <int>,
    "classification": "HOT" | "SKIP",
    "reason": "<one sentence explanation>"
  }}
]

Input Posts:
{json.dumps(sample_posts, indent=2)}
"""

    payload = {
        "model": "ministral-3b-2512",
        "messages": [
            {"role": "system", "content": "Output ONLY a valid raw JSON array."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 1000
    }

    print("Sending prompt to Mistral AI (ministral-3b-2512)...")

    try:
        with httpx.Client(timeout=25.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            print(f"HTTP Status Code: {resp.status_code}")

            if resp.status_code == 200:
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                print("\n✅ RAW MISTRAL AI RESPONSE:")
                print("-" * 50)
                print(content)
                print("-" * 50)
            else:
                print(f"❌ HTTP Error {resp.status_code}: {resp.text}")

    except Exception as e:
        print(f"❌ Execution Error: {e}")

if __name__ == "__main__":
    test_mistral_basic()

import asyncio
import os
import sys
import json
import httpx
from dotenv import dotenv_values

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.config import settings

async def test_openrouter_ping():
    print("=" * 70)
    print("OPENROUTER LLM LIVE MODEL DISCOVERY TEST")
    print("=" * 70)

    env_vars = dotenv_values("backend/.env")
    openrouter_key = (
        env_vars.get("OPENROUTER_API_KEY") or
        os.getenv("OPENROUTER_API_KEY") or
        getattr(settings, "OPENROUTER_API_KEY", "")
    )

    if not openrouter_key:
        print("❌ Error: OPENROUTER_API_KEY is not set.")
        return

    print(f"--> Found OpenRouter Key: {openrouter_key[:12]}...")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "HTTP-Referer": "https://heimdall.app",
        "X-Title": "Heimdall Lead Intel",
        "Content-Type": "application/json"
    }

    # List of candidate models to test (both free & standard slugs)
    candidate_models = [
        "meta-llama/llama-3.3-70b-instruct",
        "meta-llama/llama-3.1-8b-instruct:free",
        "google/gemma-2-9b-it:free",
        "qwen/qwen-2.5-coder-32b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
        "deepseek/deepseek-chat",
        "google/gemini-2.0-flash-001"
    ]

    working_models = []

    for model in candidate_models:
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "Output raw JSON only."
                },
                {
                    "role": "user",
                    "content": "Return JSON: {\"status\": \"ok\", \"model\": \"" + model + "\"}"
                }
            ],
            "temperature": 0.1,
            "max_tokens": 100
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    print(f"✅ WORKING MODEL: {model}")
                    print(f"   Response: {content.strip()}")
                    working_models.append(model)
                else:
                    err_msg = response.json().get("error", {}).get("message", response.text[:100])
                    print(f"❌ {model} -> HTTP {response.status_code}: {err_msg}")
        except Exception as e:
            print(f"❌ {model} -> Exception: {e}")

    print("\n" + "=" * 70)
    print(f"SUMMARY OF WORKING OPENROUTER MODELS ({len(working_models)} found):")
    for wm in working_models:
        print(f" - {wm}")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_openrouter_ping())

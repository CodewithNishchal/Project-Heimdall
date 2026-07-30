import os
import sys
import json
import httpx
from dotenv import dotenv_values

def test_openrouter_models():
    print("=" * 70)
    print("🚀 OPENROUTER MODEL AVAILABILITY PING TEST")
    print("=" * 70)

    env_vars = dotenv_values("backend/.env")
    key = env_vars.get("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY", "")

    if not key:
        print("❌ OPENROUTER_API_KEY missing in backend/.env")
        return

    print(f"API Key: {key[:8]}...{key[-4:] if len(key) > 4 else ''}\n")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "HTTP-Referer": "https://heimdall.app",
        "X-Title": "Heimdall Test",
        "Content-Type": "application/json"
    }

    # Candidate active free/standard models on OpenRouter
    candidate_models = [
        "openrouter/free",
        "openrouter/auto",
        "deepseek/deepseek-r1:free",
        "meta-llama/llama-3.1-8b-instruct:free"
    ]

    working_models = []

    with httpx.Client(timeout=15.0) as client:
        for model in candidate_models:
            print(f"Testing [{model}]... ", end="", flush=True)
            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": "Respond with 'OK'"}
                ],
                "max_tokens": 10
            }
            try:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    print("✅ WORKING (200 OK)")
                    working_models.append(model)
                else:
                    print(f"❌ {resp.status_code} ({resp.text[:60]}...)")
            except Exception as e:
                print(f"❌ Error: {e}")

    print("\n" + "=" * 70)
    if working_models:
        print(f"🎉 ACTIVE WORKING OPENROUTER MODELS: {working_models}")
        print(f"RECOMMENDED PRIMARY MODEL: '{working_models[0]}'")
    else:
        print("⚠️ No working free models found. Check OpenRouter key or balance.")
    print("=" * 70)

if __name__ == "__main__":
    test_openrouter_models()

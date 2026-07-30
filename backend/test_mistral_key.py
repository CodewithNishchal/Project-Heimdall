import os
import sys
import json
import httpx
from dotenv import dotenv_values

def test_mistral():
    print("=" * 70)
    print("🚀 MISTRAL AI API VALIDATION & CLASSIFICATION TEST")
    print("=" * 70)

    env_vars = dotenv_values("backend/.env")
    key = env_vars.get("MISTRAL_API_KEY") or os.getenv("MISTRAL_API_KEY", "")

    # Fallback to key in env if defined
    if not key:
        print("❌ MISTRAL_API_KEY is missing in backend/.env")
        print("Please add MISTRAL_API_KEY=your_key to backend/.env or pass your key.")
        return

    print(f"Key: {key[:8]}...{key[-4:] if len(key) > 4 else ''}\n")

    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }

    # Candidate Mistral models
    candidate_models = [
        "ministral-3b-2512",
        "ministral-3b-latest",
        "ministral-8b-2512",
        "mistral-small-latest",
        "open-mistral-7b"
    ]

    working_model = None

    with httpx.Client(timeout=20.0) as client:
        for model in candidate_models:
            print(f"Testing model [{model}]... ", end="", flush=True)
            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": "Respond with 'Mistral API is Working'"}
                ],
                "max_tokens": 20
            }
            try:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    print(f"✅ WORKING (200 OK) -> \"{content}\"")
                    working_model = model
                    break
                else:
                    print(f"❌ {resp.status_code} ({resp.text[:80]})")
            except Exception as e:
                print(f"❌ Error: {e}")

    print("\n" + "=" * 70)
    if working_model:
        print(f"🎉 SUCCESS: Mistral Model '{working_model}' is active and ready!")
    else:
        print("⚠️ No working Mistral model found on this key.")
    print("=" * 70)

if __name__ == "__main__":
    test_mistral()

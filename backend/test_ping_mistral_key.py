import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

print("=================================================================")
print("🔑 MISTRAL AI API KEY VALIDATION TEST")
print("=================================================================")

if not MISTRAL_API_KEY:
    print("❌ MISTRAL_API_KEY is missing in backend/.env!")
    exit(1)

print(f"Key Prefix: {MISTRAL_API_KEY[:8]}... (Length: {len(MISTRAL_API_KEY)})")

headers = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

models_to_test = ["mistral-small-latest", "mistral-large-latest", "open-mistral-7b"]

with httpx.Client(timeout=20.0) as client:
    for model in models_to_test:
        print(f"\n📡 Pinging Mistral model: {model}...")
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": "Say 'Mistral AI API connection successful!'"}
            ],
            "max_tokens": 50
        }
        try:
            res = client.post("https://api.mistral.ai/v1/chat/completions", json=payload, headers=headers)
            if res.status_code == 200:
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                print(f"✅ SUCCESS on {model}!")
                print(f"   Response: {content.strip()}")
                print(f"   Usage: Prompt={usage.get('prompt_tokens')}, Output={usage.get('completion_tokens')}, Total={usage.get('total_tokens')}")
            else:
                print(f"❌ Status {res.status_code}: {res.text}")
        except Exception as e:
            print(f"❌ FAILED on {model}: {e}")

print("\n=================================================================")

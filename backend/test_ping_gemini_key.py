import os
import sys
from dotenv import load_dotenv
from google import genai

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

print("=================================================================")
print("🔑 GEMINI API KEY VERIFICATION PING")
print("=================================================================")

if not GEMINI_API_KEY:
    print("❌ ERROR: GEMINI_API_KEY is not set in backend/.env!")
    sys.exit(1)

print(f"Key Prefix: {GEMINI_API_KEY[:8]}... (Length: {len(GEMINI_API_KEY)})")

client = genai.Client(api_key=GEMINI_API_KEY)

models_to_test = ["gemini-2.5-flash", "gemini-1.5-flash"]

for model_name in models_to_test:
    print(f"\n📡 Pinging model: {model_name}...")
    try:
        response = client.models.generate_content(
            model=model_name,
            contents="Say 'Heimdall Gemini API key ping successful!'"
        )
        if response and response.text:
            print(f"✅ SUCCESS on {model_name}!")
            print(f"   Response: {response.text.strip()}")
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                print(f"   Usage: Prompt={response.usage_metadata.prompt_token_count}, Output={response.usage_metadata.candidates_token_count}")
    except Exception as e:
        print(f"❌ FAILED on {model_name}: {e}")

print("\n=================================================================")

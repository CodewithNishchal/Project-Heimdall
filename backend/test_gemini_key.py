import os
import sys
import json
from google import genai

from dotenv import dotenv_values
env_vars = dotenv_values("backend/.env")
GEMINI_TEST_KEY = env_vars.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY", "")

def test_gemini_key():
    print("=" * 60)
    print("🚀 GEMINI API KEY VALIDATION TEST")
    print("=" * 60)
    print(f"Testing Key: {GEMINI_TEST_KEY[:8]}...{GEMINI_TEST_KEY[-4:]}\n")

    try:
        client = genai.Client(api_key=GEMINI_TEST_KEY)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="Explain in one concise sentence why the sky is blue."
        )

        print("✅ GEMINI API KEY IS WORKING PERFECTLY!\n")
        print(f"Model    : gemini-2.0-flash")
        print(f"Response : {response.text.strip()}")

    except Exception as e:
        print(f"❌ Gemini API Call Failed. Exception: {e}")

if __name__ == "__main__":
    test_gemini_key()

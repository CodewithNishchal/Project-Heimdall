import asyncio
import os
import sys
import httpx
from dotenv import load_dotenv

# Load env variables directly from backend/.env
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
load_dotenv(env_path, override=True)

APIFY_API_KEY = os.getenv("APIFY_API_KEY")
APIFY_INSIGHTS_API_KEY = os.getenv("APIFY_INSIGHTS_API_KEY")

async def ping_apify_key(key_name: str, key_val: str):
    print(f"\n🔑 Checking {key_name}: '{key_val}'")
    if not key_val:
        print(f"❌ {key_name} is missing in backend/.env!")
        return False
        
    url = f"https://api.apify.com/v2/users/me?token={key_val}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            res = await client.get(url)
            if res.status_code == 200:
                data = res.json().get("data", {})
                username = data.get("username")
                plan = data.get("plan", {}).get("name")
                print(f"  ✅ SUCCESS! Valid User: '{username}' | Plan: '{plan}'")
                return True
            else:
                print(f"  ❌ FAILED! HTTP Status: {res.status_code} - {res.text}")
                return False
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            return False

async def main():
    print("🚀 Pinging Apify API Keys...")
    
    key1_valid = await ping_apify_key("APIFY_API_KEY", APIFY_API_KEY)
    key2_valid = await ping_apify_key("APIFY_INSIGHTS_API_KEY", APIFY_INSIGHTS_API_KEY)

    print("\n--- Summary ---")
    if not key1_valid or not key2_valid:
        print("⚠️ One or both keys are invalid, expired, or out of credits!")
    else:
        print("🎉 Both Apify keys are valid and responsive!")

if __name__ == "__main__":
    asyncio.run(main())

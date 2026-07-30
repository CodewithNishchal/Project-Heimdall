import os
import httpx
import asyncio
from dotenv import dotenv_values

env_vars = dotenv_values("backend/.env")
GROQ_TEST_KEY = env_vars.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY", "")

async def test_groq_api_key():
    print("=" * 80)
    print("🧪 TESTING GROQ API KEY VALIDITY")
    print(f"Key: {GROQ_TEST_KEY[:10]}...{GROQ_TEST_KEY[-5:] if len(GROQ_TEST_KEY) > 5 else ''}")
    print("=" * 80)

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_TEST_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Respond with 'Groq API Key is VALID' and nothing else."}
        ],
        "max_tokens": 50,
        "temperature": 0.0
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            print(f"\nHTTP Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                print(f"Response Status:  ✅ SUCCESS")
                print(f"Model Used:       {data.get('model', 'llama-3.1-8b-instant')}")
                print(f"Groq Response:    \"{content.strip()}\"")
            else:
                print(f"Response Status:  ❌ FAILED")
                print(f"Error Response:   {response.text}")
    except Exception as e:
        print(f"Execution Error:  ❌ {e}")

if __name__ == "__main__":
    asyncio.run(test_groq_api_key())

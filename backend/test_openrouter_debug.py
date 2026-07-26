"""Test OpenRouter API for ling-3.0-flash:free"""
import asyncio
import os
import httpx
from dotenv import dotenv_values

async def main():
    env_vars = dotenv_values("backend/.env")
    openrouter_key = env_vars.get("OPENROUTER_API_KEY")
    if not openrouter_key:
        print("No API key found in backend/.env")
        return

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "HTTP-Referer": "https://heimdall.app",
        "X-Title": "Heimdall Lead Intel",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "inclusionai/ling-3.0-flash:free",
        "messages": [
            {"role": "system", "content": "You are a precise JSON data extraction engine. Output raw JSON only with no markdown formatting."},
            {"role": "user", "content": "Extract data for Read Ai. It recently raised $10M and is hiring marketing roles."}
        ],
        "temperature": 0.1,
        "max_tokens": 1000
    }
    
    print("Testing inclusionai/ling-3.0-flash:free ...")
    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        print(f"Status: {response.status_code}")
        try:
            data = response.json()
            print("Response JSON:")
            import json
            print(json.dumps(data, indent=2))
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            print(f"Raw Text: {response.text}")

if __name__ == "__main__":
    asyncio.run(main())

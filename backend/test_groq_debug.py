"""Test Groq API for llama3-8b-8192"""
import asyncio
import os
import httpx
from dotenv import dotenv_values
import json

async def main():
    env_vars = dotenv_values("backend/.env")
    groq_key = env_vars.get("GROQ_API_KEY")
    if not groq_key:
        print("No GROQ_API_KEY found in backend/.env")
        return

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are a precise JSON data extraction engine. Output raw JSON only with no markdown formatting. Do not include any reasoning or explanatory text."},
            {"role": "user", "content": "Extract intent signals as JSON ONLY with keys: company_name, intent_score (0-100), and ai_verdict. Text: Read.ai is hiring 20 new marketers."}
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    
    print(f"Testing Groq API (llama-3.1-8b-instant)... Key length: {len(groq_key)}")
    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        print(f"Status: {response.status_code}")
        try:
            data = response.json()
            print("Response JSON:")
            print(json.dumps(data, indent=2))
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            print(f"Raw Text: {response.text}")

if __name__ == "__main__":
    asyncio.run(main())

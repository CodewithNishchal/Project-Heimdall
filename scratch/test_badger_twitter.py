import asyncio
import httpx
from dotenv import dotenv_values

async def test_twitter_fetch():
    env_vars = dotenv_values("backend/.env")
    api_key = env_vars.get("SCRAPEBADGER_API_KEY")
    
    url = "https://scrapebadger.com/v1/twitter/tweets/advanced_search"
    headers = {"x-api-key": api_key}
    
    # Raw query without extra filters
    query = '("looking for" OR "need a" OR "recommend" OR "any recommendations") "marketing agency"'
    params = {"query": query, "count": 25}
    
    print(f"Testing ScrapeBadger Twitter Endpoint ...")
    print(f"URL: {url}")
    print(f"Params: {params}\n")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            print(f"HTTP Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("tweets") or data.get("data") or data.get("results") or []
                if isinstance(data, list):
                    items = data
                print(f"Success! Received {len(items)} tweets.")
                if items:
                    print("Sample Tweet 1:")
                    print(items[0].get("text") or items[0].get("full_text") or items[0])
            else:
                print(f"Error Response: {resp.text[:300]}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_twitter_fetch())

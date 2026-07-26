import asyncio
import httpx
import sys
import os

# Ensure backend module can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import settings

async def test_scrapebadger():
    print("=== Testing ScrapeBadger API ===")
    
    api_key = settings.SCRAPEBADGER_API_KEY
    if not api_key or api_key == "mock_key_if_empty":
        print("WARNING: SCRAPEBADGER_API_KEY is missing or set to a mock key in your .env.")
    
    # We'll use one of the LinkedIn URLs that failed in your previous log
    test_target_url = "https://www.linkedin.com/posts/michelleshummel_looking-to-meet-more-women-in-the-ai-space-activity-7477487327875891200-ScTO"
    
    import urllib.parse
    parsed_url = urllib.parse.urlparse(test_target_url)
    # Extracts the last part of the path as the slug
    post_slug = parsed_url.path.strip('/').split('/')[-1]
    
    endpoint = f"https://scrapebadger.com/v1/linkedin/posts/{post_slug}"
    
    print(f"Targeting LinkedIn Post: {test_target_url}")
    print(f"Extracted Slug: {post_slug}")
    print(f"Hitting API Endpoint: {endpoint}\n")
    
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.get(
                endpoint,
                headers={"x-api-key": api_key or "test_key"}
            )
            
            print(f"Status Code: {res.status_code}")
            
            if res.status_code == 200:
                print("\n[SUCCESS] Extracted Data Preview:")
                data = res.json()
                text = data.get("text", "") or data.get("content", "")
                print(text[:500] + "...\n" if len(text) > 500 else text)
            else:
                print(f"\n[FAILURE] Error Response: {res.text}")
                
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Connection Failed: {e}")
        print("Note: If you get a 'getaddrinfo failed' error here, it means the 'scrapebadger.com' domain itself is either invalid or experiencing DNS issues on your network.")

if __name__ == "__main__":
    asyncio.run(test_scrapebadger())

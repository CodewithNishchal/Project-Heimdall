"""
Diagnostic script to inspect public LinkedIn HTML and Serper responses for 'modal-labs'
and find the exact tag or JSON object containing numeric company ID 79045818.
"""
import os
import re
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv("backend/.env")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")


async def inspect_linkedin_sources():
    company_slug = "modal-labs"
    target_url = f"https://www.linkedin.com/company/{company_slug}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }

    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        # Diagnostic 1: Public Page Source
        resp = await client.get(target_url, headers=headers)
        print(f"=== PUBLIC PAGE (Status {resp.status_code}) ===")
        all_digits_7904 = [m.start() for m in re.finditer(r"79045818", resp.text)]
        print(f"Found '79045818' in raw HTML {len(all_digits_7904)} times!")
        
        for pos in all_digits_7904[:3]:
            print("\nSnippet around match:")
            print(resp.text[max(0, pos-100):min(len(resp.text), pos+150)])

        # Diagnostic 2: Serper search for modal-labs
        if SERPER_API_KEY:
            print("\n=== SERPER SEARCH DIAGNOSTIC ===")
            s_url = "https://google.serper.dev/search"
            s_headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
            s_payload = {"q": f'site:linkedin.com/company/modal-labs', "num": 5}
            s_resp = await client.post(s_url, headers=s_headers, json=s_payload)
            s_text = s_resp.text
            s_digits = [m.start() for m in re.finditer(r"79045818", s_text)]
            print(f"Found '79045818' in Serper JSON {len(s_digits)} times!")


if __name__ == "__main__":
    asyncio.run(inspect_linkedin_sources())

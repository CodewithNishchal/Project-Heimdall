"""
Test script: Demonstrates 3 FREE methods to resolve LinkedIn company slug (e.g., 'modal-labs')
to its numeric LinkedIn Company ID (e.g., '79045818').
"""
import re
import asyncio
import httpx


def extract_company_id_from_text(html_or_json_str: str) -> str | None:
    """
    Parses HTML or text string for LinkedIn company URN patterns like:
    1. urn:li:company:79045818
    2. "objectUrn":"urn:li:company:79045818"
    3. companyId=79045818
    4. "company":79045818
    """
    patterns = [
        r"urn:li:company:(\d+)",
        r'"objectUrn":"urn:li:company:(\d+)"',
        r'company[I|i]d["\s:=]+(\d+)',
        r'com\.linkedin\.voyager\.organization\.Company/(\d+)',
        r'organizationId["\s:=]+(\d+)'
    ]

    for p in patterns:
        match = re.search(p, html_or_json_str)
        if match:
            return match.group(1)

    return None


async def free_resolve_linkedin_company_id(slug_or_url: str) -> str | None:
    company_slug = slug_or_url.rstrip("/").split("/")[-1]
    target_url = f"https://www.linkedin.com/company/{company_slug}/"

    print("=" * 70)
    print(f"🔍 RESOLVING LINKEDIN COMPANY ID FOR: '{company_slug}'")
    print(f"🔗 Target URL: {target_url}")
    print("=" * 70)

    # METHOD 1: Free Public HTTP Fetch & URN Extraction
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            resp = await client.get(target_url, headers=headers)
            print(f"\n[Method 1] Public Page GET Status: {resp.status_code}")

            if resp.status_code == 200:
                comp_id = extract_company_id_from_text(resp.text)
                if comp_id:
                    print(f"   🎉 SUCCESS! Extracted numeric Company ID: '{comp_id}'")
                    return comp_id
                else:
                    print("   ⚠️ Public HTML redirected to authwall. Trying Method 2...")
            else:
                print(f"   ⚠️ Status {resp.status_code}. Trying Method 2...")

    except Exception as e:
        print(f"   ⚠️ Method 1 Exception: {e}")

    # METHOD 2: Free Serper Google Cache URN Extraction
    print("\n[Method 2] Google Serper Search URN Extraction...")
    import os
    from dotenv import load_dotenv
    load_dotenv("backend/.env")

    serper_key = os.getenv("SERPER_API_KEY")
    if serper_key:
        query = f'site:linkedin.com/company/{company_slug} "urn:li:company"'
        serper_url = "https://google.serper.dev/search"
        s_headers = {"X-API-KEY": serper_key, "Content-Type": "application/json"}
        s_payload = {"q": query, "num": 5}

        async with httpx.AsyncClient(timeout=15.0) as client:
            s_resp = await client.post(serper_url, headers=s_headers, json=s_payload)
            if s_resp.status_code == 200:
                comp_id = extract_company_id_from_text(s_resp.text)
                if comp_id:
                    print(f"   🎉 SUCCESS via Serper! Extracted numeric Company ID: '{comp_id}'")
                    return comp_id

    print("\n❌ Could not resolve numeric Company ID automatically.")
    return None


if __name__ == "__main__":
    asyncio.run(free_resolve_linkedin_company_id("modal-labs"))

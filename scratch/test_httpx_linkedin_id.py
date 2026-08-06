"""
Test script: Robust HTTPX & Regex extraction to resolve a LinkedIn company slug 
(e.g., 'modal-labs') to its numeric Company ID (e.g., '79045818') without browser downloads.

Saves output to scratch/httpx_linkedin_id_output.json.
"""
import re
import os
import json
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv("backend/.env")

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
OUTPUT_FILE = os.path.join("scratch", "httpx_linkedin_id_output.json")


def extract_company_id_from_text(text_data: str) -> str | None:
    """
    Scans HTML page source, headers, or JSON for LinkedIn numeric ID patterns.
    """
    patterns = [
        # Voyager & Normalized URNs
        r"urn:li:fs_normalized_company:(\d+)",
        r"urn:li:fs_miniCompany:(\d+)",
        r"urn:li:company:(\d+)",
        r"urn:li:organization:(\d+)",
        # Object & Meta tags
        r'"objectUrn"\s*:\s*"urn:li:[^"]+:(\d+)"',
        r'companyId["\s:=]+(\d+)',
        r'organizationId["\s:=]+(\d+)',
        r'data-company-id=["\'](\d+)["\']',
        r'com\.linkedin\.voyager\.organization\.Company/(\d+)',
        r'linkedin\.com/company/(\d+)',
        # Script / JSON LD patterns
        r'"id"\s*:\s*(\d{7,10})',
        r'"entityUrn"\s*:\s*"[^"]+:(\d+)"'
    ]

    for p in patterns:
        matches = re.findall(p, text_data)
        for match in matches:
            # Basic sanity check: LinkedIn company IDs are usually 6 to 10 digits
            if match and 6 <= len(match) <= 10 and match != "120000":
                return match

    return None


async def resolve_company_id_httpx(company_slug_or_url: str) -> dict:
    company_slug = company_slug_or_url.rstrip("/").split("/")[-1]
    target_url = f"https://www.linkedin.com/company/{company_slug}/"

    print("=" * 75)
    print(f"⚡ HTTPX + REGEX LINKEDIN COMPANY ID RESOLVER")
    print(f"🏢 Company Slug: '{company_slug}'")
    print(f"🔗 Target URL  : {target_url}")
    print("=" * 75 + "\n")

    company_id = None
    method_used = None

    # User-Agents to test (Googlebot often gets SSR HTML with full meta tags!)
    user_agents = [
        ("googlebot", "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"),
        ("bingbot", "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)"),
        ("desktop_chrome", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    ]

    async with httpx.AsyncClient(follow_redirects=True, timeout=12.0) as client:
        for ua_name, ua_str in user_agents:
            print(f"🔹 Trying HTTP GET with User-Agent: '{ua_name}'...")
            headers = {
                "User-Agent": ua_str,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9"
            }

            try:
                resp = await client.get(target_url, headers=headers)
                print(f"   HTTP Status: {resp.status_code}")

                # Check headers for redirect location containing numeric ID
                if resp.history:
                    for h_resp in resp.history:
                        loc = h_resp.headers.get("location", "")
                        comp_match = re.search(r"/company/(\d+)", loc)
                        if comp_match:
                            company_id = comp_match.group(1)
                            method_used = f"http_header_redirect_{ua_name}"
                            print(f"   🎉 SUCCESS via Header Redirect! Numeric ID: '{company_id}'")
                            break

                if not company_id and resp.status_code == 200:
                    found_id = extract_company_id_from_text(resp.text)
                    if found_id:
                        company_id = found_id
                        method_used = f"html_regex_{ua_name}"
                        print(f"   🎉 SUCCESS! Extracted numeric Company ID: '{company_id}'")
                        break

            except Exception as e:
                print(f"   ⚠️ Exception ({ua_name}): {e}")

    # Fallback: Google Serper JSON regex search
    if not company_id and SERPER_API_KEY:
        print("\n🔹 Triggering Google Serper URN extraction fallback...")
        serper_url = "https://google.serper.dev/search"
        s_headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        # Search for company page + URN footprint
        query = f'site:linkedin.com/company/{company_slug}'
        s_payload = {"q": query, "num": 10}

        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                s_resp = await client.post(serper_url, headers=s_headers, json=s_payload)
                if s_resp.status_code == 200:
                    found_id = extract_company_id_from_text(s_resp.text)
                    if found_id:
                        company_id = found_id
                        method_used = "serper_json_regex"
                        print(f"   🎉 SUCCESS via Serper Fallback! Company ID: '{company_id}'")
        except Exception as e:
            print(f"   ⚠️ Serper Exception: {e}")

    result = {
        "company_slug": company_slug,
        "target_url": target_url,
        "numeric_company_id": company_id,
        "method_used": method_used,
        "resolution_success": company_id is not None
    }

    os.makedirs("scratch", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"\n💾 Saved output to: '{OUTPUT_FILE}'\n")
    return result


if __name__ == "__main__":
    asyncio.run(resolve_company_id_httpx("panopto"))

"""
Test script: Uses Playwright (headless browser) & Regex extraction in Python
to resolve any LinkedIn company slug (e.g. 'modal-labs') to its numeric Company ID (e.g. '79045818').
"""
import re
import asyncio
import os
import json
from playwright.async_api import async_playwright

OUTPUT_FILE = os.path.join("scratch", "playwright_linkedin_id_output.json")


def extract_company_id_from_html(html_str: str) -> str | None:
    """
    Applies regex patterns to extract numeric LinkedIn Company ID from HTML page source.
    """
    patterns = [
        r"urn:li:company:(\d+)",
        r'"objectUrn":"urn:li:company:(\d+)"',
        r'company[I|i]d["\s:=]+(\d+)',
        r'com\.linkedin\.voyager\.organization\.Company/(\d+)',
        r'organizationId["\s:=]+(\d+)'
    ]

    for p in patterns:
        match = re.search(p, html_str)
        if match:
            return match.group(1)

    return None


async def resolve_company_id_with_playwright(company_slug: str) -> dict:
    target_url = f"https://www.linkedin.com/company/{company_slug}/"

    print("=" * 75)
    print(f"🚀 PLAYWRIGHT & REGEX LINKEDIN COMPANY ID RESOLVER")
    print(f"🏢 Company Slug: '{company_slug}'")
    print(f"🔗 Target URL  : {target_url}")
    print("=" * 75 + "\n")

    company_id = None
    page_title = None

    async with async_playwright() as p:
        print("🔹 Launching headless Chromium browser...")
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )

        page = await context.new_page()

        try:
            print(f"🔹 Navigating to {target_url}...")
            response = await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            status = response.status if response else 0
            page_title = await page.title()

            print(f"   HTTP Status: {status}")
            print(f"   Page Title : {page_title}")

            # Get rendered HTML content
            content = await page.content()

            # Apply Regex Extraction
            company_id = extract_company_id_from_html(content)

            if company_id:
                print(f"\n🎉 SUCCESS! Extracted numeric Company ID: '{company_id}'")
            else:
                print("\n⚠️ Company ID not found in page HTML source.")

        except Exception as e:
            print(f"❌ Error during navigation: {e}")

        finally:
            await browser.close()

    result = {
        "company_slug": company_slug,
        "target_url": target_url,
        "page_title": page_title,
        "numeric_company_id": company_id,
        "resolution_success": company_id is not None
    }

    # Save to scratch directory
    os.makedirs("scratch", exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"\n💾 Saved result to: '{OUTPUT_FILE}'\n")
    return result


if __name__ == "__main__":
    asyncio.run(resolve_company_id_with_playwright("panopto"))

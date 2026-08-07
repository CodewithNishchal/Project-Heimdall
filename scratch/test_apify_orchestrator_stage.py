import asyncio
import sys
import os
import json
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.pipeline.streaming_orchestrator import (
    fetch_linkedin_company_insights,
    fetch_company_jobs_apify
)

async def test_apify_stage_flow():
    mock_company_name = "Hyperce"
    mock_domain = "hyperce.io"
    mock_company_slug = "hyperce"
    mock_intent_score = 85
    
    mock_lead_payload = {
        "company_name": mock_company_name,
        "domain": mock_domain,
        "company_slug": mock_company_slug,
        "intent_score": mock_intent_score,
        "exa_evidence_chars": 3450,
        "gemini_summary": "High intent score detected. E-commerce technology scale-up expansion."
    }

    print("=========================================================================")
    print(f"🚀 MOCK STAGE 1 & 2 PASSED: '{mock_company_name}' scored {mock_intent_score}/100")
    print("🔥 STAGE 3 GATE PASSED (85 >= 80)! Triggering Stage 4 Apify Enrichment...")
    print("=========================================================================\n")

    # -------------------------------------------------------------------------
    # Stage 4 Step A: Fetch Apify riceman Insights directly via company LinkedIn URL
    # -------------------------------------------------------------------------
    target_linkedin_url = f"https://www.linkedin.com/company/{mock_company_slug}/"
    print(f"📈 [Stage 4/5] Step A: Fetching riceman Insights for '{target_linkedin_url}'...")
    insights = await fetch_linkedin_company_insights(target_linkedin_url, mock_company_slug)

    if isinstance(insights, dict):
        # Map firmographics directly
        mock_lead_payload["company_linkedin_id"] = insights.get("company_id")
        if insights.get("logo_url"):
            mock_lead_payload["logo_url"] = insights.get("logo_url")
        if insights.get("tagline"):
            mock_lead_payload["tagline"] = insights.get("tagline")
        if insights.get("description"):
            mock_lead_payload["description"] = insights.get("description")
        if insights.get("hq_full_address"):
            mock_lead_payload["hq_address"] = insights.get("hq_full_address")
        if insights.get("locations"):
            mock_lead_payload["locations"] = insights.get("locations")
        if insights.get("phone"):
            mock_lead_payload["phone"] = insights.get("phone")
        if insights.get("year_founded"):
            mock_lead_payload["year_founded"] = insights.get("year_founded")
        if insights.get("follower_count"):
            mock_lead_payload["follower_count"] = insights.get("follower_count")

        now_dt = datetime.now()
        hires_by_date = {}
        new_hires_raw = insights.get("new_hires", [])
        if isinstance(new_hires_raw, list):
            for item in new_hires_raw:
                d_str = str(item.get("date", "")).strip()
                if d_str:
                    parts = d_str.split("-")
                    if len(parts) >= 2:
                        try:
                            norm_key = f"{int(parts[0])}-{int(parts[1])}"
                            hires_by_date[norm_key] = item
                        except Exception:
                            pass

        trend = []
        for i in range(5, -1, -1):
            m_val = now_dt.month - i
            y_val = now_dt.year
            while m_val <= 0:
                m_val += 12
                y_val -= 1

            month_dt = datetime(y_val, m_val, 1)
            date_key = f"{y_val}-{m_val}"
            label = month_dt.strftime("%b")

            match_item = hires_by_date.get(date_key, {})
            s_hires = match_item.get("senior_hires", 0)
            t_hires = match_item.get("total_hires", 0)

            trend.append({
                "date": date_key,
                "label": label,
                "senior_hires": s_hires,
                "total_hires": t_hires
            })

        insights["hiring_trend"] = trend
        insights["senior_hiring_trend"] = trend

        emp_c = insights.get("employee_count")
        if emp_c and isinstance(emp_c, (int, float)):
            insights["total_employees"] = int(emp_c)
            mock_lead_payload["employee_count"] = int(emp_c)

        mock_lead_payload["company_insights"] = insights
        print("  ✅ LinkedIn Insights & Firmographic Mapping Complete!")
    else:
        mock_lead_payload["company_insights"] = None
        print("  ⚠️ Skipping LinkedIn Insights (Apify riceman actor returned None)")

    print()

    # -------------------------------------------------------------------------
    # Stage 4 Step B: 3-Tier Job Fetching Cascade (Tier 1 Apify Career Scraper)
    # -------------------------------------------------------------------------
    print("💼 [Stage 4/5] Step B: Fetching Apify Career Scraper Jobs...")
    jobs_res = await fetch_company_jobs_apify(mock_company_name, mock_domain, mock_company_slug)
    mock_lead_payload["job_openings"] = jobs_res

    # -------------------------------------------------------------------------
    # Print Final Payload
    # -------------------------------------------------------------------------
    print("\n=========================================================================")
    print("🎉 FINAL COMBINED STAGE 4 ENRICHED PAYLOAD:")
    print("=========================================================================")
    print(json.dumps(mock_lead_payload, indent=2))

if __name__ == "__main__":
    asyncio.run(test_apify_stage_flow())

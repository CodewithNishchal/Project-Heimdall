import asyncio
import sys
import os
import json
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.pipeline.linkedin_id_resolver import resolve_linkedin_company_id
from backend.pipeline.streaming_orchestrator import (
    fetch_linkedin_company_insights,
    fetch_company_jobs_apify
)

async def test_apify_stage_flow():
    # -------------------------------------------------------------------------
    # Mock Stage 1 (Exa) & Stage 2 (Gemini intent score >= 80) output
    # -------------------------------------------------------------------------
    mock_company_name = "Hyperce"
    mock_domain = "hyperce.io"
    mock_company_slug = "hyperce"
    mock_intent_score = 85  # >= 80 intent gate passed!
    
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
    # Stage 4 Step A: Resolve Numeric LinkedIn Company ID
    # -------------------------------------------------------------------------
    print("🔎 [Stage 4/5] Step A: Resolving numeric LinkedIn Company ID...")
    company_id = await resolve_linkedin_company_id(mock_company_slug)
    mock_lead_payload["company_linkedin_id"] = company_id
    print(f"  -> Resolved Company ID: {company_id}\n")

    # -------------------------------------------------------------------------
    # Stage 4 Step B: Fetch Apify LinkedIn Insights & Post-Process
    # -------------------------------------------------------------------------
    print("📈 [Stage 4/5] Step B: Fetching Apify LinkedIn Insights (freshdata actor)...")
    if company_id:
        insights = await fetch_linkedin_company_insights(company_id, mock_company_slug)
        if isinstance(insights, dict):
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

            h_month = insights.get("headcount_by_month", [])
            if isinstance(h_month, list) and len(h_month) > 0:
                latest_count = h_month[-1].get("employee_count")
                if latest_count and isinstance(latest_count, (int, float)):
                    insights["total_employees"] = int(latest_count)
                    mock_lead_payload["employee_count"] = int(latest_count)

        mock_lead_payload["company_insights"] = insights
        print("  ✅ LinkedIn Insights Post-Processing Complete!")
    else:
        mock_lead_payload["company_insights"] = None
        print("  ⚠️ Skipping LinkedIn Insights (company_id unresolvable)")

    print()

    # -------------------------------------------------------------------------
    # Stage 4 Step C: 3-Tier Job Fetching Cascade (Tier 1 Apify Career Scraper)
    # -------------------------------------------------------------------------
    print("💼 [Stage 4/5] Step C: Fetching Apify Career Scraper Jobs (piotrv1001 actor)...")
    jobs_res = await fetch_company_jobs_apify(mock_company_name, mock_domain, mock_company_slug)
    mock_lead_payload["job_openings"] = jobs_res

    # -------------------------------------------------------------------------
    # Print Final Combined Payload
    # -------------------------------------------------------------------------
    print("\n=========================================================================")
    print("🎉 FINAL COMBINED STAGE 4 ENRICHED PAYLOAD:")
    print("=========================================================================")
    print(json.dumps(mock_lead_payload, indent=2))

if __name__ == "__main__":
    asyncio.run(test_apify_stage_flow())

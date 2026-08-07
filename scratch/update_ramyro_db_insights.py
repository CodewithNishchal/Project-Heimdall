import sys
import os
import json
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal
from backend.models import LeadSnapshot

# Raw insights payload for RAMYRO Inc.
insights = {
  "company_name": "RAMYRO Inc.",
  "company_id": "105115546",
  "tagline": "Transforming Healthcare with Intelligence",
  "description": "RAMYRO integrates intelligent solutions across the healthcare echosystem, leveraging the power of artificial intelligence, with a focus on preventive health measures that prioritize proactive care, delivering precision diagnosis and support cutting-edge therapeutic treatments.\n\nFounded in early 2024 in the USA, the company is rapidly growing through strategic partnerships with key players in the healthcare sector and its first acquisition of an AI software development firm in Egypt, enhancing its portfolio.\n\nLed by founders with deep expertise in strategic management, marketing, radiology, medical devices, and healthcare, RAMYRO is committed to revolutionizing the healthcare industry with intelligent, next-generation solutions driven by a team of experts in medical devices, healthcare software, and artificial intelligence.",
  "logo_url": "https://media.licdn.com/dms/image/v2/D4D0BAQEf2zS7vDikFw/company-logo_400_400/company-logo_400_400/0/1727367113340/ramyro_inc_logo?e=1787788800&v=beta&t=ImmgUGMBONRE-50v4MyB3A_v701-wPDpxe0oAuC1KB0",
  "linkedin_url": "https://www.linkedin.com/company/ramyro-inc/",
  "website": "www.ramyro.com",
  "hq_full_address": "964 High House Rd #3274, Cary, NC 27513 United States, Raleigh, US",
  "hq_city": "Raleigh",
  "hq_region": "",
  "hq_country": "US",
  "hq_postalcode": "",
  "locations": [
    {
      "city": "Raleigh",
      "country": "US",
      "full_address": "964 High House Rd #3274, Cary, NC 27513 United States, Raleigh, US",
      "is_headquarter": True,
      "line1": "964 High House Rd #3274, Cary, NC 27513 United States",
      "line2": "",
      "region": "",
      "zipcode": ""
    }
  ],
  "phone": "",
  "email": "",
  "domain": "ramyro.com",
  "industries": [
    "Technology, Information and Internet"
  ],
  "specialties": "AI, medical imaging, artificial intelligence, healthcare software, medical IT software, software, software integration, cloud SAAS, radiology, cardiology, oncology",
  "year_founded": 2024,
  "funding_info": {
    "crunchbase_url": None,
    "last_funding_round_amount": None,
    "last_funding_round_currency": None,
    "last_funding_round_month": None,
    "last_funding_round_type": None,
    "last_funding_round_year": None,
    "num_funding_rounds": None
  },
  "employee_count": 20,
  "employee_range": "11-50",
  "follower_count": 2810,
  "affiliated_companies": [],
  "headcount_by_function": {
    "Administrative": {
      "count": 1,
      "percentage": 5
    },
    "Business Development": {
      "count": 4,
      "percentage": 20
    },
    "Engineering": {
      "count": 9,
      "percentage": 45
    },
    "Healthcare Services": {
      "count": 1,
      "percentage": 5
    },
    "Information Technology": {
      "count": 4,
      "percentage": 20
    },
    "Sales": {
      "count": 1,
      "percentage": 5
    }
  },
  "headcount_by_month": [
    {"date": "2024-8-1", "employee_count": 4},
    {"date": "2024-9-1", "employee_count": 10},
    {"date": "2024-10-1", "employee_count": 14},
    {"date": "2024-11-1", "employee_count": 16},
    {"date": "2024-12-1", "employee_count": 17},
    {"date": "2025-1-1", "employee_count": 17},
    {"date": "2025-2-1", "employee_count": 17},
    {"date": "2025-3-1", "employee_count": 16},
    {"date": "2025-4-1", "employee_count": 17},
    {"date": "2025-5-1", "employee_count": 20},
    {"date": "2025-6-1", "employee_count": 19},
    {"date": "2025-7-1", "employee_count": 22},
    {"date": "2025-8-1", "employee_count": 21},
    {"date": "2025-9-1", "employee_count": 21},
    {"date": "2025-10-1", "employee_count": 21},
    {"date": "2025-11-1", "employee_count": 21},
    {"date": "2025-12-1", "employee_count": 21},
    {"date": "2026-1-1", "employee_count": 21},
    {"date": "2026-2-1", "employee_count": 21},
    {"date": "2026-3-1", "employee_count": 21},
    {"date": "2026-4-1", "employee_count": 21},
    {"date": "2026-5-1", "employee_count": 20},
    {"date": "2026-6-1", "employee_count": 21},
    {"date": "2026-7-1", "employee_count": 20},
    {"date": "2026-8-1", "employee_count": 20}
  ],
  "headcount_growth": {
    "1y": "-5%",
    "2y": "400%",
    "6m": "-5%"
  },
  "median_employee_tenure": 1.8,
  "new_hires": [
    {"date": "2024-8", "senior_hires": 0, "total_hires": 2},
    {"date": "2024-9", "senior_hires": 0, "total_hires": 6},
    {"date": "2024-10", "senior_hires": 0, "total_hires": 4},
    {"date": "2024-11", "senior_hires": 0, "total_hires": 2},
    {"date": "2024-12", "senior_hires": 0, "total_hires": 1},
    {"date": "2025-4", "senior_hires": 0, "total_hires": 1},
    {"date": "2025-5", "senior_hires": 0, "total_hires": 3},
    {"date": "2025-7", "senior_hires": 0, "total_hires": 3},
    {"date": "2025-8", "senior_hires": 0, "total_hires": 1},
    {"date": "2025-10", "senior_hires": 0, "total_hires": 1},
    {"date": "2026-6", "senior_hires": 0, "total_hires": 1}
  ]
}

def main():
    print("🚀 Updating RAMYRO Inc. company_insights in Backend Database...")

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
    insights["total_employees"] = 20

    db = SessionLocal()
    try:
        lead = db.query(LeadSnapshot).filter(
            (LeadSnapshot.domain.ilike("%ramyro%")) |
            (LeadSnapshot.company_name.ilike("%ramyro%"))
        ).first()

        if lead:
            lead.company_insights = insights
            if isinstance(lead.full_payload, dict):
                lead.full_payload["company_insights"] = insights
                lead.full_payload["company_linkedin_id"] = insights.get("company_id")
                lead.full_payload["logo_url"] = insights.get("logo_url")
                lead.full_payload["tagline"] = insights.get("tagline")
                lead.full_payload["description"] = insights.get("description")
                lead.full_payload["hq_address"] = insights.get("hq_full_address")
                lead.full_payload["locations"] = insights.get("locations")
                lead.full_payload["year_founded"] = insights.get("year_founded")
                
            db.commit()
            print("✅ Successfully updated RAMYRO Inc. in DB snapshot table!")
            print(f"   median_employee_tenure: {lead.company_insights.get('median_employee_tenure')} yrs")
        else:
            print("⚠️ RAMYRO Inc. not found in DB snapshot table.")
    except Exception as e:
        print(f"❌ Error updating database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()

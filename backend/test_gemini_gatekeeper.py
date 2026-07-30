import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import json
import time
import logging
from backend.config_manager import load_intent_config
from backend.pipeline.orchestrator import select_top_5_leads
from backend.pipeline.discovery import apply_deterministic_filter

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TestGeminiGatekeeper")

async def test_gemini_gatekeeper():
    print("=" * 75)
    print("🚀 HEIMDALL GEMINI 2.5 FLASH GROUNDED GATEKEEPER TEST")
    print("=" * 75)

    # config = load_intent_config()
    active_niche = "recruitment_agencies"
    active_subtype = "healthcare_recruitment"
    
    # We load config just to fetch the rules for the deterministic filter
    config = load_intent_config()

    print(f"📌 Active Niche:    {active_niche}")
    print(f"📌 Active Sub-Type: {active_subtype}")

    # Load 10 mock healthcare candidates
    raw_candidates = [
        {
            "company_name": "MedTech Innovators",
            "url": "https://medtechinnovators.com",
            "summary": "MedTech Innovators is a HealthTech company. 300 employees.",
            "text_snippet": "MedTech Innovators is a HealthTech company with 300 employees. We are hiring 50 new clinical roles this quarter due to rapid regulatory expansion."
        },
        {
            "company_name": "BioHealth Solutions",
            "url": "https://biohealthsolutions.com",
            "summary": "BioHealth Solutions is a Biotech company. 1500 employees.",
            "text_snippet": "BioHealth Solutions is a Biotech company employing 1500 people. We are actively discussing our current clinical staff shortages and looking for external partners to scale our workforce."
        },
        {
            "company_name": "PharmaCare Plus",
            "url": "https://pharmacareplus.com",
            "summary": "PharmaCare Plus is a Pharma company. 100 employees.",
            "text_snippet": "PharmaCare Plus is a Pharma company. 100 employees. We just announced the opening of a massive new testing facility next month and need to hire immediately."
        },
        {
            "company_name": "CareStaffing Pro",
            "url": "https://carestaffingpro.com",
            "summary": "CareStaffing Pro is a healthcare staffing agency. 200 employees.",
            "text_snippet": "CareStaffing Pro is a healthcare staffing agency. 200 employees. We place nurses in top hospitals across the country. Partner with our agency today."
        },
        {
            "company_name": "General Hospital LA",
            "url": "https://generalhospital-la.com",
            "summary": "General Hospital LA is a Healthcare institution. 4000 employees.",
            "text_snippet": "General Hospital LA is a Healthcare institution with 4000 employees. We are hiring 100 registered nurses due to our new pediatric wing opening."
        },
        {
            "company_name": "TechSolve Agency",
            "url": "https://techsolveagency.com",
            "summary": "TechSolve Agency is a recruitment agency. 50 employees.",
            "text_snippet": "TechSolve Agency is a recruitment agency focusing on HealthTech. 50 employees. We are the leading headhunters for the healthcare tech space."
        },
        {
            "company_name": "VirtualCare MD",
            "url": "https://virtualcaremd.com",
            "summary": "VirtualCare MD is a HealthTech company. 200 employees.",
            "text_snippet": "VirtualCare MD is a HealthTech company. 200 employees. We are hiring for an internal recruiter to help us build out our telemedicine platform team."
        },
        {
            "company_name": "MediDevice Sales Inc",
            "url": "https://medidevice.com",
            "summary": "MediDevice Sales Inc is a medical device sales agency. 80 employees.",
            "text_snippet": "MediDevice Sales Inc is a medical device sales agency. 80 employees. We help you distribute your healthcare products to hospitals."
        },
        {
            "company_name": "Acme Biotech Tractors",
            "url": "https://acmebiotractors.com",
            "summary": "Acme Biotech Tractors is a Biotech company. 300 employees.",
            "text_snippet": "Acme Biotech Tractors is a Biotech company. 300 employees. We manufacture agricultural equipment and have absolutely zero hiring needs right now."
        },
        {
            "company_name": "Locum Tenens Hub",
            "url": "https://locumtenenshub.com",
            "summary": "Locum Tenens Hub is a locum tenens firm. 150 employees.",
            "text_snippet": "Locum Tenens Hub is a locum tenens firm. 150 employees. We provide temporary physician staffing for clinics."
        }
    ]

    print(f"\n📦 Real Input Pool Size: {len(raw_candidates)} Candidate Companies from Exa AI")
    print(f"   Companies: {', '.join([c['company_name'] for c in raw_candidates])}")
    
    # Build filter config from intent_config
    subtype_dict = config.get("recruitment_subtypes", {}).get(active_subtype, {})
    filter_config = {
        "allowed_categories": subtype_dict.get("target_industries", []),
        "headcount_min": subtype_dict.get("min_employees", 5),
        "headcount_max": subtype_dict.get("max_employees", 500)
    }

    # Apply zero-token deterministic pre-filter (matches production orchestrator pipeline)
    print("🧹 Running Zero-Token Deterministic Pre-Filter (Regex & Headcount bounds)...")
    survivor_candidates = apply_deterministic_filter(raw_candidates, icp_config=filter_config)
    print(f"📊 Pre-Filter Result: {len(raw_candidates)} Raw -> {len(survivor_candidates)} SURVIVORS passed headcount & category bounds.")

    if not survivor_candidates:
        print("⚠️ 0 survivors passed pre-filter. Using raw candidates fallback.")
        test_survivors = raw_candidates[:10]
    else:
        test_survivors = survivor_candidates[:10]

    print(f"\n📦 Fast Test Input Pool Size: {len(test_survivors)} Candidate Companies (Tailored for '{active_subtype}')")
    print(f"   Companies: {', '.join([c['company_name'] for c in test_survivors])}")

    print("🌐 Google Search Grounding: ENABLED (Batched Chunking)")
    print("\n⏳ Executing Gemini Grounded Gatekeeper Selection on Survivors...")

    start_time = time.time()
    top_5_leads = await select_top_5_leads(test_survivors)
    elapsed = time.time() - start_time

    print("\n" + "=" * 75)
    print(f"✅ GEMINI GATEKEEPER COMPLETED IN {elapsed:.2f} SECONDS")
    print(f"🏆 TOP 5 LEADS RANKED BY GEMINI 2.5 FLASH:")
    print("=" * 75)

    for idx, lead in enumerate(top_5_leads, 1):
        name = lead.get("company_name", "Unknown")
        domain = lead.get("domain", "Unverified Domain")
        fits = lead.get("fits_icp", True)
        category = lead.get("primary_signal_category", "HIRING/GROWTH")
        recency = lead.get("signal_recency", "Recent")
        reason = lead.get("disqualification_reason")

        print(f"[{idx}] {name}")
        print(f"    Domain: {domain}")
        print(f"    Fits ICP: {fits}")
        print(f"    Primary Signal Category: {category}")
        print(f"    Recency: ~{recency} days ago")
        if reason:
            print(f"    Disqualification Note: {reason}")
        print()

    output_path = "backend/gemini_gatekeeper_test_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "active_niche": active_niche,
            "active_subtype": active_subtype,
            "execution_time_seconds": round(elapsed, 2),
            "input_candidates_count": len(raw_candidates),
            "top_5_leads": top_5_leads
        }, f, indent=2)

    print(f"💾 Full results saved to: {output_path}")
    print("=" * 75)

if __name__ == "__main__":
    asyncio.run(test_gemini_gatekeeper())

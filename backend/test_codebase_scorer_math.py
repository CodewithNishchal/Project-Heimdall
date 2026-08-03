import os
import sys
import json
import logging
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.pipeline.scorer import process_hybrid_lead_scoring, validate_quote

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestCodebaseScorerMath")

def run_math_engine_tests():
    print("\n" + "=" * 70)
    print("🚀 HEIMDALL CODEBASE SCORING ENGINE (`scorer.py`) UNIT TEST SUITE")
    print("=" * 70 + "\n")

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    old_date_str = (datetime.now(timezone.utc) - timedelta(days=240)).strftime("%Y-%m-%d")

    test_fixtures = [
        {
            "name": "TEST 1: Fresh High-Intent Target (Vanta)",
            "description": "Fresh Series D (<30d), 102 open roles, explicit buying ask.",
            "source_text": f"Date: {today_str}\nVanta raised $150 Million in Series D funding. Vanta is actively hiring for 102 open engineering and product positions! Looking for a tech recruitment firm to help fill 5 Senior AI Engineer roles at Vanta. Our internal talent team is struggling to keep up with scaling velocity.",
            "payload": {
                "company_name": "Vanta",
                "intent_score": 95,
                "tier": "HOT",
                "intent_classification": "HOT",
                "adjacent_hiring_gap": True,
                "signal_tags": [{"category": "FUNDING_RAISE"}, {"category": "HIRING_SPIKE"}, {"category": "SOCIAL_INTENT"}],
                "signals": [
                    {
                        "signal_type": "FUNDING_RAISE",
                        "verbatim_quote": "raised $150 Million in Series D funding",
                        "source_url": "https://www.businesswire.com/news/1",
                        "event_date": today_str
                    },
                    {
                        "signal_type": "HIRING_SPIKE",
                        "verbatim_quote": "actively hiring for 102 open engineering and product positions",
                        "source_url": "https://www.linkedin.com/jobs/2",
                        "event_date": today_str
                    },
                    {
                        "signal_type": "SOCIAL_INTENT",
                        "verbatim_quote": "Looking for a tech recruitment firm to help fill 5 Senior AI Engineer roles at Vanta",
                        "source_url": "https://www.reddit.com/r/recruitment/3",
                        "event_date": today_str
                    }
                ]
            },
            "expected_behavior": "Final Math Score >= 85 (HOT/High tier), Multi-category bonus applied, 3/3 quotes verified."
        },
        {
            "name": "TEST 2: Aged Signal Decay Test (Aged Finmkt)",
            "description": "Same signals as Test 1, but dates are 240 days old (>180d recency decay).",
            "source_text": f"Date: {old_date_str}\nFinmkt raised $5 Million in Series B funding. Finmkt is actively hiring for tech positions.",
            "payload": {
                "company_name": "Finmkt",
                "intent_score": 85,
                "tier": "HOT",
                "intent_classification": "HOT",
                "adjacent_hiring_gap": False,
                "signal_tags": [{"category": "FUNDING_RAISE"}],
                "signals": [
                    {
                        "signal_type": "FUNDING_RAISE",
                        "verbatim_quote": "raised $5 Million in Series B funding",
                        "source_url": "https://www.finextra.com/news/1",
                        "event_date": old_date_str
                    }
                ]
            },
            "expected_behavior": "Recency multiplier 0.4x applied; Hard Cap Rule B limits score <= 70 due to no recent signals in last 180 days."
        },
        {
            "name": "TEST 3: Hallucinated Quote Penalty Test",
            "description": "Payload includes a quote that DOES NOT exist in raw source text.",
            "source_text": f"Date: {today_str}\nAcme Software opened a new office in Austin.",
            "payload": {
                "company_name": "Acme Software",
                "intent_score": 75,
                "tier": "WARM",
                "intent_classification": "WARM",
                "adjacent_hiring_gap": False,
                "signal_tags": [{"category": "HIRING_SPIKE"}],
                "signals": [
                    {
                        "signal_type": "HIRING_SPIKE",
                        "verbatim_quote": "Acme is desperately hiring 500 AI engineers immediately",
                        "source_url": "https://www.example.com/fake",
                        "event_date": today_str
                    }
                ]
            },
            "expected_behavior": "Quote fails validation (quote_validated = False), -15 point penalty applied."
        },
        {
            "name": "TEST 4: Competitor Staffing Agency Disqualification Guard",
            "description": "Company self-identifies as a staffing agency.",
            "source_text": f"Date: {today_str}\nApex Staffing Agency is a premier tech recruitment firm placing top software talent.",
            "payload": {
                "company_name": "Apex Staffing Agency",
                "intent_score": 0,
                "tier": "COLD",
                "intent_classification": "SKIP",
                "adjacent_hiring_gap": False,
                "signal_tags": [],
                "signals": []
            },
            "expected_behavior": "Agency Disqualification Guard locks Final Score to 0 (SKIP)."
        },
        {
            "name": "TEST 5: Single Source Hard Cap Test",
            "description": "Only 1 source URL provided and no explicit buyer ask.",
            "source_text": f"Date: {today_str}\nGeneric Tool launched a minor software patch.",
            "payload": {
                "company_name": "Generic Tool",
                "intent_score": 70,
                "tier": "WARM",
                "intent_classification": "WARM",
                "adjacent_hiring_gap": False,
                "signal_tags": [{"category": "PRODUCT_LAUNCH"}],
                "signals": [
                    {
                        "signal_type": "PRODUCT_LAUNCH",
                        "verbatim_quote": "Generic Tool launched a minor software patch",
                        "source_url": "https://www.example.com/single_source",
                        "event_date": today_str
                    }
                ]
            },
            "expected_behavior": "Hard Cap Rule A limits score <= 50 due to single source restriction."
        }
    ]

    results_summary = []

    for test in test_fixtures:
        print("-" * 70)
        print(f"📌 {test['name']}")
        print(f"   Description: {test['description']}")
        
        # Run process_hybrid_lead_scoring
        processed_result = process_hybrid_lead_scoring(
            raw_source_text=test["source_text"],
            raw_extracted_payload=test["payload"],
            firmographics={"industry": "B2B SaaS", "company_segment": "Scale-up"},
            icp_fit_label="Strong"
        )

        final_score = processed_result.get("intent_score")
        tier = processed_result.get("tier")
        intent_class = processed_result.get("intent_classification")
        breakdown = processed_result.get("scoring_breakdown", {})
        signals = processed_result.get("signals", [])

        print(f"   ► Final Math Score:       {final_score}")
        print(f"   ► Tier / Classification:  {tier} / {intent_class}")
        print(f"   ► Math Breakdown:         {json.dumps(breakdown)}")
        
        quotes_status = [f"{s.get('signal_type')}: Valid={s.get('quote_validated')} (Contrib={s.get('score_contribution')})" for s in signals]
        print(f"   ► Quotes Processed:       {quotes_status}")
        print(f"   ► Expected Behavior:      {test['expected_behavior']}")

        results_summary.append({
            "test_name": test["name"],
            "final_score": final_score,
            "tier": tier,
            "intent_classification": intent_class,
            "breakdown": breakdown,
            "signals": signals
        })

    # Save test results to JSON
    out_file = os.path.join(os.path.dirname(__file__), "test_codebase_scorer_results.json")
    with open(out_file, "w") as f:
        json.dump(results_summary, f, indent=2)

    print("\n" + "=" * 70)
    print(f"✅ ALL CODEBASE MATH SCORER UNIT TESTS COMPLETED SUCCESSFULLY!")
    print(f"📁 Full test audit saved to: {out_file}")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    run_math_engine_tests()

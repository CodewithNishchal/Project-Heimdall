import json
import os
import sys
import re

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

print("=" * 80)
print("🧪 TESTING MULTI-NICHE CONFIG & PRE-FILTER REGEX PASS")
print("=" * 80)

# Test 1: Verify intent_config.json multi-niche structure
config_path = os.path.join(os.path.dirname(__file__), "intent_config.json")
with open(config_path, "r", encoding="utf-8") as f:
    cfg = json.load(f)

print(f"\n1. Config Loaded. Active Niche: '{cfg.get('active_niche')}'")
niches = cfg.get("niches", {})
print(f"   Available Niches: {list(niches.keys())}")

for niche_name, niche_data in niches.items():
    direct = len(niche_data.get("direct_ask_keywords", []))
    pain = len(niche_data.get("pain_signal_keywords", []))
    neg = len(niche_data.get("negative_keywords", []))
    print(f"   - [{niche_name}]: {direct} Direct Ask | {pain} Pain Signal | {neg} Negative Keywords")

# Test 2: Verify PRE_FILTER_SKIP_PATTERNS
from backend.pipeline.social_classifier import PRE_FILTER_SKIP_PATTERNS

test_posts = [
    {"id": 1, "text": "We are a marketing agency that helps B2B brands scale paid ads. Book a call!", "should_skip": True},
    {"id": 2, "text": "Looking for a recruitment agency to help us fill 3 senior engineering roles ASAP.", "should_skip": False},
    {"id": 3, "text": "Our hiring is taking forever, 4 months to fill one AE role.", "should_skip": False},
    {"id": 4, "text": "We just hired an agency and they increased our leads by 50%!", "should_skip": True},
    {"id": 5, "text": "Join our team! Open position at XYZ Marketing Agency.", "should_skip": True},
]

print("\n2. Testing Pre-Filter Regex Pass (Zero-Cost LLM Saver):")
passed = 0
for tp in test_posts:
    text = tp["text"]
    is_skipped = any(re.search(pat, text) for pat in PRE_FILTER_SKIP_PATTERNS)
    expected = tp["should_skip"]
    status = "✅ PASS" if is_skipped == expected else "❌ FAIL"
    if is_skipped == expected:
        passed += 1
    action = "SKIPPED (No LLM)" if is_skipped else "SENT TO LLM"
    print(f"   {status} | Post #{tp['id']}: [{action}] -> \"{text[:50]}...\"")

print(f"\nPre-Filter Test Result: {passed}/{len(test_posts)} Passed ({passed/len(test_posts)*100:.0f}%)")

# Test 3: Verify Scorer Single-Source Capping
from backend.pipeline.scorer import process_hybrid_lead_scoring

raw_payload = {
    "company_name": "TestCorp",
    "intent_score": 85,
    "why_now": "Raised $10M in funding.",
    "signals": [
        {
            "signal_type": "funding",
            "verbatim_quote": "Raised $10M",
            "source_url": "https://techcrunch.com/test",
            "event_date": "2026-07-01"
        }
    ]
}

result = process_hybrid_lead_scoring(raw_payload, {}, "Raised $10M in funding.")
print("\n3. Testing Single-Source Score Capping (<= 50):")
print(f"   Raw LLM Score: 85 | Signals: 1 | Final Capped Score: {result['intent_score']}")
if result["intent_score"] <= 50:
    print("   ✅ SUCCESS: Single-source lead correctly capped at <= 50")
else:
    print("   ❌ FAIL: Score not capped")

print("\n" + "=" * 80)
print("🎉 ALL MULTI-NICHE & CLASSIFIER CHECKS COMPLETE")
print("=" * 80)

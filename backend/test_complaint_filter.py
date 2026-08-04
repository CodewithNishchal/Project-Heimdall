import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.pipeline.social_classifier import is_prefiltered

test_cases = [
    {
        "name": "1. Buyer Post (Internal Hiring Announcement)",
        "author_headline": "VP of Engineering at TechScale",
        "content": "We're hiring 5 software engineers — join our team! Check out our open roles at techscale.io/careers.",
        "expected": False
    },
    {
        "name": "2. Buyer Post (Scaling Customer Support)",
        "author_headline": "Head of Customer Success",
        "content": "We are scaling our customer support team and hiring 10 technical support reps this quarter!",
        "expected": False
    },
    {
        "name": "3. Buyer Post (Seeking Recruiting Partner)",
        "author_headline": "Founder & CEO at SaaSify",
        "content": "We are a Series B SaaS company looking for a recruiting partner to help us scale our dev team.",
        "expected": False
    },
    {
        "name": "4. Agency Competitor Seller Pitch",
        "author_headline": "Helping companies hire exceptional Technology, Skilled Trades & ...",
        "content": "At Elite Acquisition Partners, I help companies find professionals who make a real impact. If you're planning to hire this quarter, I'd love to connect.",
        "expected": True
    },
    {
        "name": "5. Customer Complaint / Support Frustration",
        "author_headline": "Frustrated User",
        "content": "Wth are you hiring for when you can't deliver a product and there is no response from customer support on WhatsApp or email.",
        "expected": True
    },
    {
        "name": "6. Thought Leadership / Newsletter Promo",
        "author_headline": "Matchking's Business Beacon | Published monthly",
        "content": "The best candidates aren't applying for jobs anymore. For years, b2b recruitment has relied on CVs... matchking.com/newsletter",
        "expected": True
    }
]

print("=" * 70)
print("🧪 VERIFYING SOCIAL CLASSIFIER REGEX & PRE-FILTER CALIBRATION")
print("=" * 70)

all_passed = True
for tc in test_cases:
    content = tc["content"]
    bio = tc["author_headline"]
    filtered, pattern = is_prefiltered(content, bio=bio, niche_id="recruitment")
    
    passed_test = (filtered == tc["expected"])
    if not passed_test:
        all_passed = False

    status_str = "⛔ FILTERED (SKIP)" if filtered else "✅ PASSED (TO LLM)"
    test_result = "PASS ✅" if passed_test else "FAIL ❌"

    print(f"\n[{test_result}] {tc['name']}")
    print(f"   Headline : \"{bio}\"")
    print(f"   Content  : \"{content[:75]}...\"")
    print(f"   Status   : {status_str}")
    if filtered:
        print(f"   Pattern  : {pattern}")

print("\n" + "=" * 70)
if all_passed:
    print("🎉 ALL PRE-FILTER CALIBRATION TESTS PASSED!")
else:
    print("💥 SOME TESTS FAILED!")
print("=" * 70 + "\n")

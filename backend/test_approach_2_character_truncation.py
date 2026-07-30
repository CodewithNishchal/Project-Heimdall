import re
import json

# Realistic long-form scraped payloads (1,000 to 2,500 chars) with real scraper noise
LONG_SCRAPED_SIGNALS = [
    {
        "id": 1,
        "platform": "LinkedIn (Long Founder Storytelling)",
        "company": "Pylon",
        "raw_text": """
Posted by Sarah Chen • 2d • Follow • ...
1,420 reactions • 184 comments • 32 reposts

When we started Pylon 3 years ago, everyone told us the customer support space was overcrowded. They said Zendesk and Freshdesk owned the market and no new startup could ever compete. 

We spent the first 18 months grinding in a tiny garage in San Francisco. There were nights I didn't sleep at all. We faced 47 investor rejections in a row. I remember sitting in a coffee shop in Palo Alto ready to throw in the towel because we only had 2 months of runway left. 

But our early design partners kept telling us: "Existing support tools were built for email in 2005. Nobody built an AI-native platform designed for Slack and Teams first." That kept us going.

Today, I'm thrilled to share a massive milestone: Pylon has officially raised a $15.5M Series A led by Scale Venture Partners with participation from Y Combinator! 🚀

With this new capital, we are expanding our product team and aggressively hiring for 12 new roles across Senior Full-Stack Engineering, AI Infrastructure, and Enterprise Account Executive positions in SF and remote.

Check out our open roles here: https://usepylon.com/careers
Like • Comment • Share • Report post • About the Author: Sarah Chen is Co-Founder & CEO at Pylon.
""",
        "intent_location_char": 710, # Intent trigger starts around char ~710
        "expected_intent": "$15.5M Series A / hiring for 12 new roles"
    },
    {
        "id": 2,
        "platform": "Reddit (Long Community Post + Scraping Noise)",
        "company": "Ashby",
        "raw_text": """
r/SaaS • Posted by u/talent_lead_99 3 days ago • Join • 84 points • 42 comments
Cookie Policy | Privacy Policy | User Agreement | Help Center | Reddit Inc © 2026

Hey SaaS founders and GTM leaders, long time reader of r/SaaS here.

Over the last 2 years, our team at Ashby has been head down building out our all-in-one recruiting and applicant tracking platform. We started with just 8 people in a small co-working space trying to fix spreadsheet recruiting.

Fast forward to Q2 2026: we have officially surpassed 310 full-time employees, doubled our ARR year-over-year, and we are currently seeing massive hiring velocity across B2B enterprise tech clients.

Because our internal growth is accelerating so fast, our marketing team is looking for fractional CMOs and specialized B2B growth agency partners to help us scale our paid acquisition and demand gen channels.

If you run a top-tier growth or performance marketing agency with proven SaaS case studies, drop a comment or DM me!

View All 42 Comments • Sort by: Top • u/saas_guru: Great milestone! • Report Post • Share
""",
        "intent_location_char": 450,
        "expected_intent": "surpassed 310 full-time employees / looking for fractional CMOs and specialized B2B growth agency"
    },
    {
        "id": 3,
        "platform": "Serper News (Full Press Release & Corporate Boilerplate)",
        "company": "Orb",
        "raw_text": """
TechCrunch — Enterprise & AI Infrastructure News • Published July 2026 • 4 min read
Newsletter Signup | Advertise | Terms of Service

SAN FRANCISCO — Orb, the leading modern usage-based billing platform for AI infrastructure and B2B SaaS companies, today announced it has secured $25 million in Series B funding led by Bessemer Venture Partners, with continued participation from Matrix Partners and South Park Commons.

The funding round comes amid record demand for usage-based pricing infrastructure as AI companies scale rapidly. Orb's revenue has grown 300% year-over-year, processing billions of billing events for market leaders like Replit, Pinecone, and Perplexity.

"Billing for AI is fundamentally different than traditional SaaS subscription billing," said CEO Alvaro Morales. "As AI companies scale, they need real-time metering and dynamic pricing flexibility."

Orb will use the new capital to expand its core engineering team, accelerate global go-to-market operations, and open a new office in New York. The company is actively recruiting across engineering, product, and sales leadership.

About Orb: Orb is the billing engine for modern pricing models. Learn more at https://withorb.com.
Media Contact: press@withorb.com | Copyright 2026 TechCrunch Inc. All rights reserved.
""",
        "intent_location_char": 160,
        "expected_intent": "$25 million in Series B funding / expand its core engineering team"
    }
]

# Expanded real-world scraper junk patterns
ENHANCED_JUNK_PATTERNS = [
    r"^like\s*•\s*comment\s*•\s*share.*",
    r"^cookie policy.*",
    r"^posted by.*",
    r"^\d+,\d+ reactions.*",
    r"^newsletter signup.*",
    r"^about the author:.*",
    r"^media contact:.*",
    r"^copyright \d+.*",
    r"^r/\w+\s*•.*",
    r"^view all \d+ comments.*",
    r"^report post.*"
]

def clean_and_truncate_safe(text: str, max_chars: int = 1000) -> str:
    """
    1. Filters empty lines and scraper chrome.
    2. Truncates cleanly at word boundaries (rfind(' ')) to avoid mid-word cuts.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    cleaned_lines = []
    
    for line in lines:
        is_junk = any(re.search(pat, line, re.IGNORECASE) for pat in ENHANCED_JUNK_PATTERNS)
        if not is_junk:
            cleaned_lines.append(line)
            
    cleaned_text = "\n".join(cleaned_lines)
    
    if len(cleaned_text) <= max_chars:
        return cleaned_text
        
    # Cut cleanly at a word boundary
    truncated_raw = cleaned_text[:max_chars]
    last_space = truncated_raw.rfind(" ")
    if last_space > max_chars * 0.8:  # Don't cut back too far
        truncated_raw = truncated_raw[:last_space]
        
    return truncated_raw + "..."

def run_cap_benchmark():
    print("\n" + "=" * 95)
    print("🧪 BENCHMARK: TESTING TRUNCATION CAPS (500 vs 700 vs 1000 vs 1200 Chars)")
    print("=" * 95)

    caps_to_test = [500, 700, 1000, 1200]

    for cap in caps_to_test:
        print(f"\n" + "-" * 95)
        print(f"📊 EVALUATING CHARACTER CAP = {cap} CHARS")
        print("-" * 95)
        
        passed_count = 0
        total_orig = 0
        total_trunc = 0
        
        for item in LONG_SCRAPED_SIGNALS:
            raw = item["raw_text"]
            orig_len = len(raw)
            clean_trunc = clean_and_truncate_safe(raw, max_chars=cap)
            trunc_len = len(clean_trunc)
            
            total_orig += orig_len
            total_trunc += trunc_len
            
            # Check if intent survived
            intent_words = [w.lower() for w in item["expected_intent"].split(" / ")]
            survived = all(any(part in clean_trunc.lower() for part in w.split()) for w in intent_words)
            
            if survived:
                passed_count += 1
                
            print(f" • Sample #{item['id']} [{item['company']}] (Orig: {orig_len}c -> Trunc: {trunc_len}c) "
                  f"| Intent Loc: ~{item['intent_location_char']}c | Status: {'✅ SURVIVED' if survived else '❌ CUT OFF!'}")

        avg_savings = round((1 - total_trunc / total_orig) * 100, 1)
        print(f"   >>> CAP {cap} RESULTS: Survival = {passed_count}/{len(LONG_SCRAPED_SIGNALS)} ({round(passed_count/len(LONG_SCRAPED_SIGNALS)*100)}%) | Token Savings = {avg_savings}%")

if __name__ == "__main__":
    run_cap_benchmark()

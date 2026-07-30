import os
import json
import re

# Sample scraped posts simulating real-world scraper output (LinkedIn hooks, Reddit posts, News articles)
SAMPLE_POSTS = [
    {
        "id": 1,
        "source_api": "LinkedIn",
        "company": "Pylon",
        "raw_text": """
Like · Comment · Share · 142 reactions

Building a startup is a roller coaster. 3 years ago, we were working out of a small garage with 0 customers.

I remember thinking if we'd ever make it past month 6.

Today, I am thrilled to announce that Pylon has officially raised a $15.5M Series A led by Venture Partners! 🚀

We are actively hiring for 12 new engineering and sales positions in San Francisco.

Join our journey: https://usepylon.com/careers
""",
        "expected_intent": "$15.5M Series A / hiring for 12 new engineering"
    },
    {
        "id": 2,
        "source_api": "Reddit",
        "company": "Ashby",
        "raw_text": """
Cookie Notice · Privacy Policy · r/SaaS

Hey everyone, long time lurker first time poster here.

Our team has been grinding on our talent acquisition platform for the past 2 years.

We recently passed 300 employees and are seeing massive hiring velocity across B2B enterprise clients.

Looking for fractional CMO or agency recommendations to scale our paid customer acquisition channels.

Any recommendations for top-tier growth agencies?
""",
        "expected_intent": "passed 300 employees / looking for fractional CMO or agency"
    },
    {
        "id": 3,
        "source_api": "Serper News",
        "company": "Orb",
        "raw_text": """
TechCrunch — Tech & Business News

Orb Secures $25M Series B to Scale Billing Infrastructure for AI Companies.

San Francisco, CA — Orb, a leading modern billing platform for B2B SaaS and AI infrastructure scale-ups, today announced it has closed a $25 million Series B financing round.

The round was led by Bessemer Venture Partners with participation from existing investors. The new capital will be used to expand the engineering team and accelerate global go-to-market initiatives.
""",
        "expected_intent": "$25M Series B / expand engineering team"
    }
]

def naive_line_truncate(text: str, max_lines: int = 5) -> str:
    """Naive line-count truncation using splitlines()."""
    lines = text.strip().split("\n")
    return "\n".join(lines[:max_lines])

def clean_character_truncate(text: str, max_chars: int = 800) -> str:
    """
    Cleans junk UI chrome / empty lines first, then truncates predictably by character cap.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    # Remove obvious scraper UI chrome headers (e.g. 'Like · Comment', 'Cookie Notice')
    junk_patterns = [r"like\s*·\s*comment", r"cookie notice", r"privacy policy", r"r/\w+"]
    cleaned_lines = []
    for line in lines:
        if not any(re.search(pat, line, re.IGNORECASE) for pat in junk_patterns):
            cleaned_lines.append(line)
            
    cleaned_text = "\n".join(cleaned_lines)
    if len(cleaned_text) <= max_chars:
        return cleaned_text
    return cleaned_text[:max_chars] + "..."

def test_truncation_impact():
    print("\n" + "=" * 90)
    print("🧪 TEST: SIGNAL TRUNCATION & INTENT SURVIVAL EVALUATION")
    print("=" * 90)

    for item in SAMPLE_POSTS:
        print(f"\n📌 SAMPLE #{item['id']} ({item['source_api']} - {item['company']})")
        print("-" * 60)
        
        raw_len = len(item['raw_text'])
        naive = naive_line_truncate(item['raw_text'], max_lines=5)
        clean_char = clean_character_truncate(item['raw_text'], max_chars=700)
        
        naive_survived = any(word.lower() in naive.lower() for word in ["series a", "series b", "hiring", "cmo", "agency"])
        clean_survived = any(word.lower() in clean_char.lower() for word in ["series a", "series b", "hiring", "cmo", "agency"])

        print(f"Original Length: {raw_len} chars")
        print(f"Target Intent:   \"{item['expected_intent']}\"")
        
        print(f"\n[Approach 1: Naive Line Truncation (5 Lines)]")
        print(f"  Length: {len(naive)} chars")
        print(f"  Intent Survived? {'✅ YES' if naive_survived else '❌ NO (SIGNAL LOST!)'}")
        print(f"  Text Preview:\n\"\"\"\n{naive}\n\"\"\"")

        print(f"\n[Approach 2: Junk-Stripped Character Truncation (700 Chars)]")
        print(f"  Length: {len(clean_char)} chars")
        print(f"  Intent Survived? {'✅ YES' if clean_survived else '❌ NO'}")
        print(f"  Text Preview:\n\"\"\"\n{clean_char}\n\"\"\"")

if __name__ == "__main__":
    test_truncation_impact()

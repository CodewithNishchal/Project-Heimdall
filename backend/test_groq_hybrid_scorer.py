import asyncio
import json
import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.pipeline.scorer import analyze_lead_intent_with_llm

TEST_COMPANIES = [
    {
        "name": "Apex Scale Labs",
        "description": "HIGH INTENT (HOT) — Series A, NSF SBIR Grant, 8 SDR hiring gap, VP Sales hire, European expansion",
        "firmographics": {"employee_count": 85, "industry": "B2B SaaS", "company_segment": "Growth Scale-up"},
        "evidence_text": """
=== SOURCE EVIDENCE 0: EXA DISCOVERY SNIPPET ===
Apex Scale Labs is a fast-growing B2B SaaS company building AI analytics software for enterprise sales teams. 
Headquartered in Austin, TX with 85 employees. The company recently announced a major operational expansion.

=== SOURCE EVIDENCE 1: PRESS RELEASE (NEWS) ===
Date: 2026-07-15
Austin, TX — Apex Scale Labs announced today that it has raised $12.5 Million in Series A funding led by Horizon Ventures. 
In addition, Apex Scale Labs was awarded a $500,000 SBIR Phase II Grant by the National Science Foundation (NSF) to accelerate its AI research.
The company plans to use the capital to double its sales force and expand into European markets.

=== SOURCE EVIDENCE 2: REDDIT POST (r/sales) ===
Date: 2026-07-20
Title: Apex Scale Labs is hiring 8 SDRs and 3 Account Executives!
Text: Just saw Apex Scale Labs posted 8 new SDR openings and 3 AE roles on LinkedIn. They currently have zero internal marketing or demand-gen staff, so their sales reps are doing 100% outbound cold outreach.

=== SOURCE EVIDENCE 3: X / TWITTER POST ===
Date: 2026-07-22
Text: Excited to welcome Sarah Jenkins as our new Vice President of Sales at Apex Scale Labs! Sarah previously scaled revenue at CloudScale from $5M to $30M.
""",
        "raw_signals": [
            {"company_name": "Apex Scale Labs", "url": "https://apexscalelabs.com/about", "source_api": "Exa_Discovery"},
            {"company_name": "Apex Scale Labs", "url": "https://apexscalelabs.com/news/series-a", "source_api": "News"},
            {"company_name": "Apex Scale Labs", "url": "https://reddit.com/r/sales/comments/apex_hiring", "source_api": "Reddit"},
            {"company_name": "Apex Scale Labs", "url": "https://x.com/apexscalelabs/status/1001", "source_api": "X"}
        ]
    },
    {
        "name": "QuantumPulse Systems",
        "description": "MODERATE INTENT (WARM) — Seed funding 5 months old (150 days old), hiring 2 developers",
        "firmographics": {"employee_count": 35, "industry": "Cloud Software", "company_segment": "Early Stage"},
        "evidence_text": """
=== SOURCE EVIDENCE 0: EXA DISCOVERY SNIPPET ===
QuantumPulse Systems provides developer tools for distributed databases. Based in Seattle, WA.

=== SOURCE EVIDENCE 1: PRESS RELEASE (NEWS) ===
Date: 2026-03-01
Seattle, WA — QuantumPulse Systems raised $2.5 Million in Seed funding back in March 2026 to enhance database reliability.

=== SOURCE EVIDENCE 2: JOB BOARD POST ===
Date: 2026-07-10
Title: Hiring Senior Backend Engineer & Cloud Architect at QuantumPulse Systems.
Text: We are looking for 2 backend developers to help scale our infrastructure.
""",
        "raw_signals": [
            {"company_name": "QuantumPulse Systems", "url": "https://quantumpulse.io/about", "source_api": "Exa_Discovery"},
            {"company_name": "QuantumPulse Systems", "url": "https://techcrunch.com/quantumpulse-seed", "source_api": "News"},
            {"company_name": "QuantumPulse Systems", "url": "https://linkedin.com/jobs/quantumpulse-dev", "source_api": "JobBoard"}
        ]
    },
    {
        "name": "Vanguard Media Group",
        "description": "SELLER DISQUALIFIED (AGENCY GUARD) — Digital marketing agency offering PPC & SEO services",
        "firmographics": {"employee_count": 40, "industry": "Marketing & Advertising", "company_segment": "Agency"},
        "evidence_text": """
=== SOURCE EVIDENCE 0: EXA DISCOVERY SNIPPET ===
Vanguard Media Group is a full-service digital marketing agency helping B2B SaaS companies scale paid media and SEO.

=== SOURCE EVIDENCE 1: WEBSITE HOME PAGE ===
Vanguard Media Group is a leading digital marketing agency. We specialize in Meta ads, Google PPC, content marketing, and SEO for growing startups. Book a call with our team today to grow your pipeline.
""",
        "raw_signals": [
            {"company_name": "Vanguard Media Group", "url": "https://vanguardmedia.com", "source_api": "Exa_Discovery"},
            {"company_name": "Vanguard Media Group", "url": "https://vanguardmedia.com/services", "source_api": "Web"}
        ]
    },
    {
        "name": "Nexus Robotics",
        "description": "MEDIUM-HIGH INTENT (WARM) — $225k SBIR Phase I Grant (0.6x weight) + New VP Product hire",
        "firmographics": {"employee_count": 55, "industry": "Robotics & Hardware", "company_segment": "Scale-up"},
        "evidence_text": """
=== SOURCE EVIDENCE 0: EXA DISCOVERY SNIPPET ===
Nexus Robotics builds autonomous warehouse sorting robots for logistics operators.

=== SOURCE EVIDENCE 1: PRESS RELEASE (NEWS) ===
Date: 2026-07-20
Boston, MA — Nexus Robotics announced today it has received a $225,000 SBIR Phase I Grant from the US Department of Defense.

=== SOURCE EVIDENCE 2: LINKEDIN POST ===
Date: 2026-07-24
Text: We are thrilled to welcome Dr. Marcus Vance as our new Vice President of Product Engineering at Nexus Robotics!
""",
        "raw_signals": [
            {"company_name": "Nexus Robotics", "url": "https://nexusrobotics.com/about", "source_api": "Exa_Discovery"},
            {"company_name": "Nexus Robotics", "url": "https://nexusrobotics.com/press/sbir-grant", "source_api": "News"},
            {"company_name": "Nexus Robotics", "url": "https://linkedin.com/posts/nexusrobotics-vp-hire", "source_api": "LinkedIn"}
        ]
    },
    {
        "name": "Starlight Healthcare",
        "description": "LOW INTENT (SKIP) — Single old news mention > 14 months ago (triggers Rule A single-source cap at 40 & 0.1x recency)",
        "firmographics": {"employee_count": 120, "industry": "HealthTech", "company_segment": "Established"},
        "evidence_text": """
=== SOURCE EVIDENCE 0: NEWS ARCHIVE ===
Date: 2025-05-10
Starlight Healthcare published a research whitepaper on patient telemetry software back in May 2025.
""",
        "raw_signals": [
            {"company_name": "Starlight Healthcare", "url": "https://healthtechnews.com/starlight-2025", "source_api": "News"}
        ]
    },
    {
        "name": "Hyperion Logistics",
        "description": "HIGH INTENT (HOT) — $5M Seed round 20 days ago + hiring 12 SDRs with adjacent gap (no CMO)",
        "firmographics": {"employee_count": 65, "industry": "Logistics SaaS", "company_segment": "Growth Scale-up"},
        "evidence_text": """
=== SOURCE EVIDENCE 0: EXA DISCOVERY SNIPPET ===
Hyperion Logistics provides real-time freight tracking software for regional carriers.

=== SOURCE EVIDENCE 1: PRESS RELEASE (NEWS) ===
Date: 2026-07-11
Chicago, IL — Hyperion Logistics closed a $5.0 Million Seed funding round led by SupplyChain Capital to expand outbound sales operations.

=== SOURCE EVIDENCE 2: JOB BOARD POST ===
Date: 2026-07-18
Title: Hyperion Logistics is hiring 12 Sales Development Representatives (SDRs).
Text: Rapidly expanding outbound sales team. Hyperion has no internal marketing director or CMO, so SDRs lead all outbound pipeline generation.
""",
        "raw_signals": [
            {"company_name": "Hyperion Logistics", "url": "https://hyperionlogistics.io/about", "source_api": "Exa_Discovery"},
            {"company_name": "Hyperion Logistics", "url": "https://techcrunch.com/hyperion-seed", "source_api": "News"},
            {"company_name": "Hyperion Logistics", "url": "https://linkedin.com/jobs/hyperion-sdr-roles", "source_api": "JobBoard"}
        ]
    }
]

async def run_comparative_test():
    print("=" * 90)
    print(f"🧪 COMPARATIVE LEAD SCORING TEST ACROSS {len(TEST_COMPANIES)} DISTINCT PROSPECT PROFILES")
    print("=" * 90)

    total_tokens_consumed = 0
    token_breakdown = []

    for item in TEST_COMPANIES:
        name = item["name"]
        desc = item["description"]
        text = item["evidence_text"]
        firmos = item["firmographics"]
        signals = item["raw_signals"]

        print("\n\n" + "#" * 90)
        print(f"🏢 COMPANY: {name}")
        print(f"📋 PROFILE: {desc}")
        print("#" * 90)

        result = await analyze_lead_intent_with_llm(
            company_name=name,
            cleaned_html=text,
            firmographics=firmos,
            icp_fit_label="Strong ICP Fit",
            raw_signals=signals
        )

        tokens = result.get("groq_token_usage", 0)
        if isinstance(tokens, int):
            total_tokens_consumed += tokens
        token_breakdown.append((name, tokens))

        breakdown = result.get("scoring_breakdown", {})
        print(f"\n📊 RESULTS SUMMARY FOR '{name}':")
        print(f"   • Groq Tokens Consumed : {tokens} tokens")
        print(f"   • Intent Score         : {result.get('intent_score')}/100")
        print(f"   • Classification       : {result.get('intent_classification')} (Tier: {result.get('tier')})")
        print(f"   • Base Groq AI Score   : {breakdown.get('base_ai_score')}/100")
        print(f"   • Adjacent Hiring Gap  : {result.get('adjacent_hiring_gap')} (Bonus: +{breakdown.get('adjacent_hiring_bonus')} pts)")
        print(f"   • Multi-Category Bonus : +{breakdown.get('multi_category_bonus')} pts (Categories: {breakdown.get('signal_categories_detected')})")
        print(f"   • One-Line Reason      : {result.get('one_line_reason')}")
        print(f"   • Why Now              : {result.get('why_now')}")
        
        print("\n   📌 SIGNALS EXTRACTED & RECENCY DECAY BREAKDOWN:")
        for idx, sig in enumerate(result.get("signals", []), 1):
            print(f"      [{idx}] Type: {sig.get('signal_type')}")
            print(f"          Quote: \"{sig.get('verbatim_quote')}\"")
            print(f"          Recency: {sig.get('recency_label')} ({sig.get('days_old')} days old)")
            print(f"          Source URL: {sig.get('source_url')}")
            print(f"          Contribution: +{sig.get('score_contribution')} pts (Validated: {sig.get('quote_validated')})")

        print("\n⏳ Sleeping 2s to respect Groq API rate limits...")
        await asyncio.sleep(2)

    print("\n" + "=" * 90)
    print("💡 GROQ TOKEN CONSUMPTION SUMMARY")
    print("=" * 90)
    for comp_name, tok in token_breakdown:
        print(f"   • {comp_name:<30}: {tok} tokens")
    print(f"   🔥 TOTAL TOKENS CONSUMED ACROSS ALL {len(TEST_COMPANIES)} TESTS: {total_tokens_consumed} tokens")
    print("=" * 90)

if __name__ == "__main__":
    asyncio.run(run_comparative_test())

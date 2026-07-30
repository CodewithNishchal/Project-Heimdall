import re
import json
from datetime import datetime, timezone

COMPANY_RAW_SIGNALS = [
    {
        "id": 1,
        "source_type": "Serper News",
        "intent_category": "funding",
        "date_posted": "2026-07-28T10:00:00Z",
        "raw_text": """
TechCrunch — Enterprise & AI Infrastructure News • Published July 2026
Newsletter Signup | Terms of Service

Pylon Secures $15.5M Series A to Scale AI Support Infrastructure for Enterprise Teams.
San Francisco, CA — Pylon, an AI-native support platform, today announced a $15.5M Series A funding round led by Scale Venture Partners.
The company plans to double its engineering team and expand sales operations globally.
Media Contact: press@usepylon.com | Copyright 2026 TechCrunch Inc.
"""
    },
    {
        "id": 2,
        "source_type": "Serper News",
        "intent_category": "expansion",
        "date_posted": "2026-07-27T14:00:00Z",
        "raw_text": """
VentureBeat — AI & Cloud Intelligence • Deep Dive Report

Pylon Named Top 10 Enterprise AI Startup to Watch in 2026.

San Francisco-based Pylon continues rapid customer expansion across B2B SaaS verticals. The platform has seen explosive adoption among high-growth scale-ups who are migrating off legacy support infrastructure like Zendesk and Salesforce Service Cloud.

According to CEO Sarah Chen, "Legacy platforms were built for email tickets in 2005. Modern customer success teams live in Slack, Teams, and in-app chat. We built Pylon from the ground up to automate triage, routing, and resolution natively inside collaborative channels."

The company's proprietary LLM engine automatically analyzes inbound customer requests, categorizes urgency, and drafts context-aware responses with 92% precision. Early enterprise adopters report a 40% reduction in first-response times and a 3x increase in customer retention metrics.

In addition to product velocity, Pylon has expanded its executive leadership team, bringing on former VP of Sales from Datadog to lead enterprise go-to-market. The company is actively recruiting across product management, solutions engineering, and demand generation.

Financial terms of recent customer expansions were undisclosed, but industry analysts estimate Pylon's ARR has grown over 250% year-over-year. Investors include Scale Venture Partners, Y Combinator, and prominent AI founders.

Furthermore, Pylon's strategic expansion includes opening a new regional headquarters in London to support European enterprise accounts. The international office will house dedicated customer success, solutions architecture, and localized support teams.

About VentureBeat: VentureBeat is the leading source for transformative tech news. Copyright 2026. All rights reserved.
"""
    },
    {
        "id": 3,
        "source_type": "LinkedIn",
        "intent_category": "hiring",
        "date_posted": "2026-07-28T16:30:00Z",
        "raw_text": """
Like • Comment • Share • 1,420 reactions

Building Pylon has been an incredible journey. 3 years ago we started in a garage with 0 users.
Today, I'm thrilled to share that Pylon raised $15.5M Series A! 🚀
We are actively hiring 12 new roles across Senior Full-Stack Engineering, AI Infra, and Enterprise Sales in SF & Remote.
Apply at usepylon.com/careers
Report post • Author: CEO Sarah Chen
"""
    },
    {
        "id": 4,
        "source_type": "Reddit",
        "intent_category": "agency_ask",
        "date_posted": "2026-07-29T09:15:00Z",
        "raw_text": """
r/SaaS • Posted by u/support_lead_sf 1 day ago • Join
Cookie Notice | Privacy Policy | Reddit Inc © 2026

Has anyone switched their customer support stack from Zendesk to Pylon recently?
We are expanding our customer success team and looking for agency recommendations to set up automated Slack integrations.
Any recommendations for B2B ops consultancies?
View All Comments • Report Post
"""
    },
    {
        "id": 5,
        "source_type": "X/Twitter",
        "intent_category": "expansion",
        "date_posted": "2026-07-10T14:00:00Z",
        "raw_text": """
Retweets 5 • Likes 20
Catch our team at the Developer Experience Conference next week!
"""
    }
]

SOURCE_PRIORITY_WEIGHTS = {
    "Serper News": 100,
    "LinkedIn": 80,
    "Reddit": 60,
    "X/Twitter": 50
}

INLINE_JUNK_PATTERNS = [
    r"like\s*•\s*comment\s*•\s*share.*",
    r"report post.*",
    r"view all \d+ comments.*",
    r"author:.*",
    r"cookie notice.*",
    r"privacy policy.*",
    r"terms of service.*",
    r"newsletter signup.*",
    r"media contact:.*",
    r"copyright \d+.*",
    r"retweets \d+ • likes \d+"
]

def clean_and_truncate_per_source(text: str, source_type: str) -> str:
    """Per-Source Budget: News=1,200 chars / Social=800 chars."""
    max_chars = 1200 if "News" in source_type else 800
    
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    cleaned_lines = []
    for line in lines:
        cl = line
        for pat in INLINE_JUNK_PATTERNS:
            cl = re.sub(pat, "", cl, flags=re.IGNORECASE).strip()
        if cl:
            cleaned_lines.append(cl)
            
    cleaned = "\n".join(cleaned_lines)
    if len(cleaned) <= max_chars:
        return cleaned
        
    truncated = cleaned[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > max_chars * 0.8:
        truncated = truncated[:last_space]
    return truncated + "..."

def select_top_n_category_reservation(raw_signals: list[dict], max_n: int = 4) -> list[dict]:
    """
    2-Pass Category Reservation Selection:
    Pass 1: Reserves top scorer per DISTINCT available intent_category (guarantees multi-category bonus).
    Pass 2: Fills remaining slots up to max_n by rank score (capped at max 2 per category).
    """
    scored = []
    for sig in raw_signals:
        src_w = SOURCE_PRIORITY_WEIGHTS.get(sig.get("source_type", ""), 40)
        try:
            dt = datetime.fromisoformat(sig.get("date_posted").replace("Z", "+00:00"))
            days_old = (datetime.now(timezone.utc) - dt).days
            rec_score = max(0, 100 - days_old * 5)
        except Exception:
            rec_score = 50
            
        final_score = round(src_w * 0.6 + rec_score * 0.4, 1)
        scored.append({**sig, "rank_score": final_score, "src_w": src_w, "rec_score": rec_score})

    scored.sort(key=lambda s: s["rank_score"], reverse=True)

    selected = []
    category_counts = {}

    # Pass 1: Reserve highest-scoring signal for each DISTINCT category
    for sig in scored:
        if len(selected) >= max_n:
            break
        cat = sig.get("intent_category", "general")
        if cat not in category_counts:
            selected.append(sig)
            category_counts[cat] = 1

    # Pass 2: Fill remaining slots up to max_n (capping max 2 per category)
    for sig in scored:
        if len(selected) >= max_n:
            break
        cat = sig.get("intent_category", "general")
        if sig not in selected and category_counts.get(cat, 0) < 2:
            selected.append(sig)
            category_counts[cat] = category_counts.get(cat, 0) + 1

    return selected

def run_verified_benchmark():
    print("\n" + "=" * 95)
    print("🚀 VERIFIED BENCHMARK: 2-PASS CATEGORY RESERVATION + PER-SOURCE CHAR BUDGETS")
    print("=" * 95)

    true_raw_chars = sum(len(s["raw_text"]) for s in COMPANY_RAW_SIGNALS)
    selected = select_top_n_category_reservation(COMPANY_RAW_SIGNALS, max_n=4)

    print(f"\n📥 TRUE UN-TRUNCATED RAW INPUT: {len(COMPANY_RAW_SIGNALS)} Signals | Total Chars: {true_raw_chars} (~{int(true_raw_chars/4)} Tokens)")

    print(f"\n🏆 2-PASS CATEGORY RESERVED TOP-{len(selected)} SELECTION:")
    processed = []
    tot_proc_chars = 0
    for idx, s in enumerate(selected, start=1):
        clean_text = clean_and_truncate_per_source(s["raw_text"], s["source_type"])
        tot_proc_chars += len(clean_text)
        processed.append({**s, "clean_text": clean_text})
        print(f"  {idx}. [{s['source_type']} - Category: {s['intent_category']}] Score: {s['rank_score']} | Output: {len(clean_text)} chars")

    tok_savings = round((1 - tot_proc_chars / true_raw_chars) * 100, 1)
    print(f"\n📤 GROQ PAYLOAD: {len(processed)} Signals | Total Chars: {tot_proc_chars} (~{int(tot_proc_chars/4)} Tokens)")
    print(f"   🔥 RECONCILED TOKEN REDUCTION: {tok_savings}% SAVINGS!")

if __name__ == "__main__":
    run_verified_benchmark()

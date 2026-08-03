import os
import json
import asyncio
import logging
from datetime import datetime, timezone
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from backend.pipeline.scorer import process_hybrid_lead_scoring


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DummyMultiSourceTest")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

async def run_dummy_multisource_test():
    company_name = "Augment Code"
    domain = "augmentcode.com"

    print("=================================================================")
    print(f"🚀 RUNNING MULTI-SOURCE PIPELINE TEST FOR: {company_name} ({domain})")
    print("=================================================================")

    # 1. DUMMY EXA AI COMPANY PROFILE DATA (Field Filtered)
    dummy_exa_profile = {
        "title": "Augment Code - Company Profile",
        "url": "https://augmentcode.com/",
        "summary": "Augment Code is an AI software development platform. Headquartered in Palo Alto, CA. Employing 143 people (Technical ~64, Sales ~26). Total funding: $252 million. 2 open engineering positions.",
        "text_snippet": "Augment Code (Augment Computing, Inc.) is a privately held Software Development platform founded in 2022. Palo Alto HQ."
    }

    # 2. DUMMY SERPER NEWS ARTICLES & PRESS RELEASES
    dummy_serper_news = [
        {
            "title": "Augment Code Raises $227M Series C at $2B+ Valuation",
            "link": "https://shiporskip.io/news/augment-code-227m-series-c-enterprise-ai-coding",
            "date": "2026-08-03",
            "snippet": "Augment Code announced a $227 million Series C round led by Index Ventures, pushing its valuation past $2 billion. The enterprise AI coding assistant targets shared codebase refactoring."
        },
        {
            "title": "Augment Code launches Cosmos platform to bring agentic AI to software teams",
            "link": "https://siliconangle.com/2026/06/05/augment-code-launches-cosmos-bring-agentic-ai-software-development-teams/",
            "date": "2026-06-05",
            "snippet": "Augment Code Computing Inc. announced the launch of Cosmos, an AI software delivery lifecycle platform designed for engineering teams to collaborate with agentic AI."
        }
    ]

    # 3. DUMMY SCRAPEBADGER SOCIAL INTENT POSTS
    dummy_social_posts = [
        {
            "url": "https://linkedin.com/posts/augmentinc_hiring-vp-engineering-agentic-ai",
            "text": "We are expanding our engineering leadership team! Looking for a VP of Engineering to lead our agentic AI developer platform team in Palo Alto."
        }
    ]

    # 4. FORMAT SOURCE-INDEXED EVIDENCE TEXT ([S1], [S2], [S3], [S4])
    combined_raw_text = ""
    url_index_map = {}
    source_counter = 1

    # Add Exa Profile
    src_id = f"S{source_counter}"
    source_counter += 1
    url_index_map[src_id] = dummy_exa_profile["url"]
    combined_raw_text += f"\n--- [{src_id}] COMPANY PROFILE: {dummy_exa_profile['title']} ({dummy_exa_profile['url']}) ---\n"
    combined_raw_text += f"SUMMARY: {dummy_exa_profile['summary']}\n"
    combined_raw_text += f"HIGHLIGHTS: {dummy_exa_profile['text_snippet']}\n"

    # Add Serper News
    for news in dummy_serper_news:
        src_id = f"S{source_counter}"
        source_counter += 1
        url_index_map[src_id] = news["link"]
        combined_raw_text += f"\n--- [{src_id}] SERPER NEWS: {news['title']} ({news['link']}) Date: {news['date']} ---\n"
        combined_raw_text += f"NEWS SUMMARY: {news['snippet']}\n"

    # Add Social Posts
    for post in dummy_social_posts:
        src_id = f"S{source_counter}"
        source_counter += 1
        url_index_map[src_id] = post["url"]
        combined_raw_text += f"\n--- [{src_id}] SOCIAL INTENT POST ({post['url']}) ---\n"
        combined_raw_text += f"POST CONTENT: {post['text']}\n"

    print("\n📄 INDEXED EVIDENCE TEXT SENT TO GEMINI:")
    print(combined_raw_text)

    # 5. GEMINI 2.5 FLASH COMPACT SCHEMA EXTRACTION
    gemini_system_prompt = """You are a Senior B2B Sales Intelligence Analyst for Tech Recruitment.

CONTEXT:
Analyze the provided multi-source evidence and extract high-value recruitment intent signals.

SIGNAL EXTRACTION CATEGORIES:
1. 'SOCIAL_INTENT': Explicit buyer asks.
2. 'HIRING_SPIKE': Active hiring surges or open hard-to-fill tech roles.
3. 'FUNDING_RAISE': Recent venture funding or debt financing.
4. 'REVENUE_MILESTONE': ARR milestones ($10M+, $50M+, $100M+ ARR).
5. 'EXECUTIVE_EXPANSION': C-suite or VP hires.
6. 'PRODUCT_LAUNCH': Major platform, AI model, or enterprise product launches.

STRICT COMPACT SCHEMA RULES:
- Use compact keys for signals: "t" for signal_type, "q" for verbatim_quote, "s" for source ID (e.g. "S1", "S2"), "d" for event_date (YYYY-MM-DD).
- 'q' (verbatim_quote) MUST BE AN EXACT WORD-FOR-WORD SUBSTRING of the evidence text. Zero paraphrasing!
- 's' MUST match the source tag ID (e.g., "S1", "S2").

COMPACT JSON OUTPUT FORMAT:
{
  "company_name": "Exact Brand Name",
  "intent_score": 85,
  "tier": "HOT",
  "ai_verdict": "Executive summary pitch hook...",
  "adjacent_hiring_gap": boolean,
  "signal_tags": [{"category": "FUNDING_RAISE"}, {"category": "HIRING_SPIKE"}],
  "signals": [
    {
      "t": "FUNDING_RAISE",
      "q": "exact word for word quote",
      "s": "S2",
      "d": "YYYY-MM-DD"
    }
  ]
}"""

    gemini_user_prompt = f"""Target Company: {company_name}
Target Domain: {domain}

MULTI-SOURCE INDEXED EVIDENCE:
{combined_raw_text}

Analyze the evidence and output strictly valid compact JSON matching the required schema."""

    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    config = types.GenerateContentConfig(
        system_instruction=gemini_system_prompt,
        temperature=0.1,
        response_mime_type="application/json"
    )

    print("\n🧠 Sending evidence to Gemini 2.5 Flash...")
    gemini_res = await asyncio.to_thread(
        lambda: gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=gemini_user_prompt,
            config=config
        )
    )

    gemini_raw_json = json.loads(gemini_res.text)

    token_str = "Unknown"
    if hasattr(gemini_res, "usage_metadata") and gemini_res.usage_metadata:
        p_tok = getattr(gemini_res.usage_metadata, "prompt_token_count", 0)
        c_tok = getattr(gemini_res.usage_metadata, "candidates_token_count", 0)
        t_tok = getattr(gemini_res.usage_metadata, "total_token_count", 0)
        token_str = f"Prompt: {p_tok} | Output: {c_tok} | Total: {t_tok}"

    print(f"📊 Gemini Token Usage: [{token_str}]")
    print(f"📥 Gemini Raw Compact Response:\n{json.dumps(gemini_raw_json, indent=2)}")

    # 6. UNPACK COMPACT KEYS & EXPAND SOURCE URLS
    unpacked_signals = []
    for sig in gemini_raw_json.get("signals", []):
        quote = sig.get("q") or sig.get("verbatim_quote") or ""
        sig_type = sig.get("t") or sig.get("signal_type") or "HIRING_SPIKE"
        event_date = sig.get("d") or sig.get("event_date") or datetime.now(timezone.utc).isoformat()
        src_tag = sig.get("s") or sig.get("source_url") or "S1"
        full_url = url_index_map.get(src_tag, src_tag if src_tag.startswith("http") else "")

        unpacked_signals.append({
            "signal_type": sig_type,
            "verbatim_quote": quote,
            "source_url": full_url,
            "event_date": event_date
        })

    gemini_raw_json["signals"] = unpacked_signals

    # 7. CODEBASE MATH SCORER
    math_result = process_hybrid_lead_scoring(
        raw_source_text=combined_raw_text,
        raw_extracted_payload=gemini_raw_json,
        firmographics={"employee_count": 143, "total_funding": 252000000},
        icp_fit_label="Strong"
    )

    math_result["gemini_token_usage"] = token_str

    out_file = os.path.join(os.path.dirname(__file__), "test_dummy_multisource_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(math_result, f, indent=2)

    print("\n=================================================================")
    print(f"✅ FINAL MATH SCORE: {math_result.get('intent_score')} ({math_result.get('tier')} / {math_result.get('intent_classification')})")
    print(f"📁 Results saved to: {out_file}")
    print("=================================================================")

if __name__ == "__main__":
    asyncio.run(run_dummy_multisource_test())

import os
import sys
import json
import asyncio

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.config_manager import load_intent_config
from backend.pipeline.social_discovery import fetch_social_micro_intent
from backend.pipeline.social_classifier import batch_classify_social_intent

# Master Queries per Sub-Type Matrix (Senior Spec)
SUBTYPE_QUERIES_MATRIX = {
    "startup_tech": {
        "linkedin": ["excited to announce our seed round", "growing our founding team", "hiring our first engineers"],
        "twitter": '("seed round" OR "pre-seed" OR "series a") (hiring OR "we\'re hiring" OR "join our team") -"venture capital firm" -"our accelerator program" -"our incubator cohort"',
        "reddit": ["just raised our seed round hiring", "startup hiring after funding"],
        "google": '("raised our seed round" OR "closed our pre-seed" OR "growing our founding team") hiring -"venture capital firm" -"accelerator program" -"incubator cohort"',
        "threads": ["raised seed round hiring engineers", "growing founding team startup hiring"]
    },
    "tech_recruitment": {
        "linkedin": ["hiring DevOps engineers", "growing our ML engineering team", "SOC2 compliance hiring"],
        "twitter": '("hiring DevOps" OR "hiring ML engineers" OR "SOC2 compliance" OR "scaling our engineering team") -"our staffing firm" -"our RPO services" -"leading headhunter firm"',
        "reddit": ["engineering hiring spike SOC2", "scaling DevOps team hiring"],
        "google": '("hiring DevOps engineers" OR "growing our ML team" OR "SOC2 compliance hiring") -"our staffing firm" -"leading RPO provider"',
        "threads": ["hiring DevOps engineers", "scaling engineering SOC2 compliance"]
    },
    "executive_search": {
        "linkedin": ["hiring our next VP of Engineering", "board announces leadership transition", "searching for our next CEO"],
        "twitter": '("VP of Engineering search" OR "VP of Sales search" OR "searching for our next CEO" OR "leadership transition") -"executive coaching" -"leadership training program" -"our HR consultancy"',
        "reddit": ["company searching for new CEO", "VP level hiring announcement"],
        "google": '("searching for our next CEO" OR "VP Engineering search" OR "board announces leadership transition") -"executive coaching" -"leadership training program"',
        "threads": ["hiring VP Engineering", "searching for new CEO"]
    },
    "volume_rpo": {
        "linkedin": ["opening our new warehouse hiring", "seasonal hiring announcement", "hiring 100 new positions"],
        "twitter": '("new warehouse" OR "new distribution center" OR "seasonal hiring event") ("100 positions" OR "mass hiring") -"our staffing agency" -"our temp agency" -"PEO services"',
        "reddit": ["new warehouse opening jobs", "seasonal hiring event retail"],
        "google": '("opening a new warehouse" OR "new distribution center" OR "seasonal hiring event") hiring -"our staffing agency" -"PEO services"',
        "threads": ["opening new warehouse hiring", "seasonal hiring event"]
    },
    "healthcare_recruitment": {
        "linkedin": ["opening our new clinic hiring", "clinical staff shortage", "expanding our hospital network"],
        "twitter": '("new clinic" OR "new healthcare facility" OR "clinical staff shortage" OR "hospital expansion") hiring -"our staffing agency" -"locum tenens firm" -"medical device sales agency"',
        "reddit": ["clinical staff shortage hiring", "new hospital facility opening"],
        "google": '("clinical staff shortage" OR "new healthcare facility" OR "hospital expansion") hiring -"our staffing agency" -"locum tenens firm"',
        "threads": ["opening new clinic hiring", "clinical staff shortage"]
    },
    "sales_recruitment": {
        "linkedin": ["hiring SDRs and AEs", "welcomes our new VP of Sales", "building our GTM team from scratch"],
        "twitter": '("hiring SDRs" OR "hiring AEs" OR "new VP of Sales" OR "building our GTM team") -"sales training company" -"sales enablement agency" -"outbound agency services"',
        "reddit": ["hiring SDR AE cluster", "new VP sales building team"],
        "google": '("hiring SDRs and AEs" OR "new VP of Sales" OR "building our GTM team") -"sales training company" -"sales enablement agency"',
        "threads": ["hiring SDRs AEs", "new VP of Sales"]
    }
}

async def run_subtype_test(target_subtype: str = "startup_tech"):
    print("=" * 80)
    print(f"🚀 HEIMDALL MASTER SUB-TYPE PIPELINE TEST: [{target_subtype.upper()}]")
    print("=" * 80)

    # 1. Update config for active sub-type & recruitment_agencies niche
    config = load_intent_config()
    config["active_niche"] = "recruitment_agencies"
    config["active_subtype"] = target_subtype
    
    with open(os.path.join(PROJECT_ROOT, "backend", "intent_config.json"), "w", encoding="utf-8") as cf:
        json.dump(config, cf, indent=2)

    queries_info = SUBTYPE_QUERIES_MATRIX.get(target_subtype, SUBTYPE_QUERIES_MATRIX["startup_tech"])
    
    print(f"Active Niche      : recruitment_agencies")
    print(f"Active Sub-Type   : {target_subtype}")
    print(f"Master Queries    : {json.dumps(queries_info, indent=2)}")
    print("-" * 80)

    # PHASE 1: Fetch Raw Posts directly using platform queries
    print(f"\n⏳ PHASE 1: Fetching raw social posts for '{target_subtype}' across all platforms...")
    
    from backend.pipeline.social_discovery import (
        fetch_apify_linkedin,
        fetch_scrapebadger_twitter,
        fetch_scrapebadger_reddit,
        fetch_scrapecreators_google,
        fetch_scrapecreators_threads,
        reconstruct_platform_url
    )
    import httpx

    raw_posts = []
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        # 1. LinkedIn (Apify)
        li_queries = queries_info.get("linkedin", [])
        if li_queries:
            li_items = await fetch_apify_linkedin(client, li_queries[0])
            for item in li_items:
                raw_posts.append({
                    "company_name": item.get("authorName") or item.get("companyName") or "Startup Founder",
                    "author_handle": item.get("authorUsername") or item.get("authorProfileId") or "linkedin_user",
                    "author_name": item.get("authorName") or "LinkedIn User",
                    "platform": "linkedin",
                    "content": str(item.get("text") or item.get("commentary") or "")[:500],
                    "post_url": reconstruct_platform_url("linkedin", item, keyword=li_queries[0]),
                    "keyword_matched": li_queries[0],
                    "published_at": item.get("postedAt") or item.get("publishedAt") or "2026-07-30T00:00:00Z"
                })

        # 2. Twitter / X (ScrapeBadger)
        tw_query = queries_info.get("twitter", "")
        if tw_query:
            tw_items = await fetch_scrapebadger_twitter(client, tw_query)
            for item in tw_items:
                raw_posts.append({
                    "company_name": item.get("user", {}).get("name") or "Founder",
                    "author_handle": item.get("user", {}).get("screen_name") or "x_user",
                    "author_name": item.get("user", {}).get("name") or "X User",
                    "platform": "x",
                    "content": str(item.get("text") or item.get("full_text") or "")[:500],
                    "post_url": reconstruct_platform_url("x", item, keyword="startup"),
                    "keyword_matched": tw_query,
                    "published_at": item.get("created_at") or "2026-07-30T00:00:00Z"
                })

        # 3. Reddit (ScrapeBadger)
        rd_queries = queries_info.get("reddit", [])
        if rd_queries:
            rd_items = await fetch_scrapebadger_reddit(client, rd_queries[0])
            for item in rd_items:
                raw_posts.append({
                    "company_name": item.get("author") or "Reddit User",
                    "author_handle": item.get("author") or "reddit_user",
                    "author_name": item.get("author") or "Reddit User",
                    "platform": "reddit",
                    "content": f"{item.get('title', '')}\n{item.get('selftext', '')}"[:500],
                    "post_url": item.get("url") or f"https://reddit.com{item.get('permalink', '')}",
                    "keyword_matched": rd_queries[0],
                    "published_at": item.get("created_utc") or "2026-07-30T00:00:00Z"
                })

        # 4. Google (ScrapeCreators)
        g_query = queries_info.get("google", "")
        if g_query:
            g_items = await fetch_scrapecreators_google(client, g_query)
            for item in g_items:
                raw_posts.append({
                    "company_name": item.get("title", "").split(" - ")[0][:40] or "Target Lead",
                    "author_handle": item.get("domain") or "google_search",
                    "author_name": item.get("displayed_link") or "Google Result",
                    "platform": "google",
                    "content": f"{item.get('title', '')}\n{item.get('snippet', '')}"[:500],
                    "post_url": item.get("link") or item.get("url") or "",
                    "keyword_matched": g_query,
                    "published_at": "2026-07-30T00:00:00Z"
                })

        # 5. Threads (ScrapeCreators)
        th_queries = queries_info.get("threads", [])
        for th_q in th_queries:
            th_items = await fetch_scrapecreators_threads(client, th_q)
            print(f"   [Threads API] Query '{th_q}' -> {len(th_items)} items returned.")
            for item in th_items:
                user_obj = item.get("user", {}) if isinstance(item.get("user"), dict) else {}
                raw_posts.append({
                    "company_name": user_obj.get("username") or item.get("username") or "Threads User",
                    "author_handle": user_obj.get("username") or item.get("username") or "threads_user",
                    "author_name": user_obj.get("full_name") or user_obj.get("username") or "Threads User",
                    "platform": "threads",
                    "content": str(item.get("caption") or item.get("text") or item.get("content") or "")[:500],
                    "post_url": item.get("url") or f"https://www.threads.net/@{user_obj.get('username', 'user')}",
                    "keyword_matched": th_q,
                    "published_at": item.get("published_at") or item.get("created_at") or "2026-07-30T00:00:00Z"
                })

    print(f"✅ Total Raw Social Posts Fetched: {len(raw_posts)}")

    platform_counts = {}
    for p in raw_posts:
        plat = p.get("platform", "unknown")
        platform_counts[plat] = platform_counts.get(plat, 0) + 1

    print("📊 Platform Breakdown:")
    for plat, count in platform_counts.items():
        print(f"   - {plat.upper()}: {count} posts")

    # OBJECT 1: Raw Fetched Posts Object
    object_1_raw_posts = {
        "subtype_tested": target_subtype,
        "total_raw_count": len(raw_posts),
        "platform_breakdown": platform_counts,
        "raw_posts": raw_posts
    }

    # PHASE 2: Mistral AI LLM Classification (ministral-3b-2512)
    print(f"\n⏳ PHASE 2: Running Mistral AI (ministral-3b-2512) Classification under '{target_subtype}' ICP rules...")
    qualified_leads, token_usage = await batch_classify_social_intent(raw_posts, return_usage=True)
    print(f"✅ LLM Classification Complete: {len(qualified_leads)} Qualified HOT/WARM Leads!")
    
    print("-" * 80)
    print("📊 MISTRAL AI TOKEN USAGE LOG:")
    print(f"   - Prompt Tokens    : {token_usage.get('prompt_tokens', 0):,}")
    print(f"   - Completion Tokens: {token_usage.get('completion_tokens', 0):,}")
    print(f"   - Total Tokens     : {token_usage.get('total_tokens', 0):,}")
    print(f"   - Est. Batch Cost  : ${ (token_usage.get('total_tokens', 0) / 1000000.0) * 0.10 :.6f}")
    print("-" * 80)

    for idx, lead in enumerate(qualified_leads[:5], start=1):
        print(f"\n{idx}. [{lead.get('platform', '').upper()}] @{lead.get('author_handle')}: {lead.get('classification')} (Confidence: {int(lead.get('confidence', 0)*100)}%)")
        print(f"   Reason: {lead.get('reason')}")
        print(f"   Quote : {lead.get('summary')}")

    # OBJECT 2: LLM Output Qualified Leads Object
    object_2_llm_qualified_leads = {
        "active_niche": "recruitment_agencies",
        "active_subtype": target_subtype,
        "mistral_token_usage": token_usage,
        "qualified_count": len(qualified_leads),
        "qualified_leads": qualified_leads
    }

    # COMBINED OUTPUT JSON
    final_output = {
        "object_1_fetched_raw_posts": object_1_raw_posts,
        "object_2_llm_qualified_leads": object_2_llm_qualified_leads
    }

    output_path = os.path.join(PROJECT_ROOT, "backend", "test_master_subtype_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2)

    print("\n" + "=" * 80)
    print(f"💾 Full test results saved to: backend/test_master_subtype_results.json")
    print(f"   - Object 1 (Raw Fetched Posts): {len(raw_posts)} posts")
    print(f"   - Object 2 (LLM Qualified Leads): {len(qualified_leads)} leads")
    print("=" * 80)

if __name__ == "__main__":
    # Test starting from the first sub-type: 'startup_tech'
    subtype_to_test = sys.argv[1] if len(sys.argv) > 1 else "startup_tech"
    asyncio.run(run_subtype_test(subtype_to_test))

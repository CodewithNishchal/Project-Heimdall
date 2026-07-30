import asyncio
import os
import sys
import json
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.pipeline.social_classifier import batch_classify_social_intent

# 40 Realistic Dummy Social Posts (Mixing Buyers, Agencies/Providers, Job Listings & Unrelated Chatter)
DUPLICATE_40_POSTS = [
    # --- BUYERS SEEKING PROVIDERS / AGENCIES / FRACTIONAL LEADERS ---
    {"platform": "x", "author_name": "Sarah Chen", "author_handle": "schen_tech", "content": "Can anyone recommend a great Fractional CMO for a B2B SaaS startup scaling to $5M ARR? Need someone with proven PLG experience.", "post_url": "https://x.com/schen_tech/status/101", "company_name": "SaaSFlow", "published_at": "2026-07-28T10:00:00Z"},
    {"platform": "linkedin", "author_name": "David Miller", "author_handle": "david-miller-founder", "content": "We are issuing an RFP for a full-service Growth Marketing Agency to handle our Q4 paid acquisition and SEO. Inbox me or drop recommendations below.", "post_url": "https://linkedin.com/posts/david-miller-102", "company_name": "FinTech Vault", "published_at": "2026-07-28T11:00:00Z"},
    {"platform": "reddit", "author_name": "dev_founder_99", "author_handle": "dev_founder_99", "content": "Looking for a performance marketing agency specializing in Shopify e-commerce. Current ad spend is $50k/mo. Recommendations?", "post_url": "https://reddit.com/r/marketing/comments/103", "company_name": "RetailScale", "published_at": "2026-07-27T15:30:00Z"},
    {"platform": "threads", "author_name": "Elena Rostova", "author_handle": "elena_designs", "content": "Our B2B startup needs an emergency Fractional CMO to help align sales & marketing before our Series A pitch. DM if interested!", "post_url": "https://threads.net/@elena_designs/post/104", "company_name": "Nexus AI", "published_at": "2026-07-28T09:15:00Z"},
    {"platform": "google", "author_name": "TechCrunch RFP", "author_handle": "google_search", "content": "RFP Announcement: FinTech scale-up seeking growth marketing agency for international expansion.", "post_url": "https://techcrunch.com/rfp-fintech-105", "company_name": "PayDirect", "published_at": "2026-07-26T14:00:00Z"},
    {"platform": "x", "author_name": "Marcus Vance", "author_handle": "mvance_vc", "content": "One of my portfolio companies is looking for a fractional CMO with deep experience in HealthTech and HIPAA compliance. Recommendations welcomed!", "post_url": "https://x.com/mvance_vc/status/106", "company_name": "Vance Ventures", "published_at": "2026-07-28T16:20:00Z"},
    {"platform": "linkedin", "author_name": "Jessica Taylor", "author_handle": "jessica-taylor-vp", "content": "We need an external agency recommendation for website redesign and B2B positioning sprint. Must have SaaS case studies.", "post_url": "https://linkedin.com/posts/jessica-taylor-107", "company_name": "CloudSync", "published_at": "2026-07-28T12:45:00Z"},
    {"platform": "reddit", "author_name": "startup_ceo_austin", "author_handle": "startup_ceo_austin", "content": "Has anyone hired a Fractional CMO from a specialized growth agency? What was your experience and who did you use?", "post_url": "https://reddit.com/r/startups/comments/108", "company_name": "Austin BioTech", "published_at": "2026-07-25T18:00:00Z"},

    # --- AGENCIES & FREELANCERS PROMOTING SERVICES (IS_PROVIDER) ---
    {"platform": "linkedin", "author_name": "Apex Marketing Studio", "author_handle": "apex-marketing", "content": "We help B2B SaaS companies scale from $1M to $10M ARR using data-driven Fractional CMO and growth sprint frameworks. Book a call today!", "post_url": "https://linkedin.com/posts/apex-marketing-109", "company_name": "Apex Marketing", "published_at": "2026-07-28T08:00:00Z"},
    {"platform": "x", "author_name": "Jason Growth", "author_handle": "jasongrowth_cmo", "content": "As a Fractional CMO for 12+ startups, here are 5 reasons why hiring a full-time CMO too early will burn your seed capital. #FractionalCMO", "post_url": "https://x.com/jasongrowth_cmo/status/110", "company_name": "Jason CMO Consulting", "published_at": "2026-07-27T10:00:00Z"},
    {"platform": "threads", "author_name": "HyperGrowth Agency", "author_handle": "hypergrowth_agency", "content": "Looking to boost your conversions? Our agency specializes in SEO, Meta Ads, and Fractional CMO leadership for DTC brands. DM for a free audit!", "post_url": "https://threads.net/@hypergrowth_agency/post/111", "company_name": "HyperGrowth", "published_at": "2026-07-28T07:30:00Z"},
    {"platform": "linkedin", "author_name": "Rachel Sterling", "author_handle": "rachel-sterling-cmo", "content": "I am opening 2 slots for my Fractional CMO practice starting next month. If your B2B company is struggling with GTM alignment, let's talk.", "post_url": "https://linkedin.com/posts/rachel-sterling-112", "company_name": "Sterling Strategy", "published_at": "2026-07-26T11:20:00Z"},
    {"platform": "reddit", "author_name": "agency_owner_mike", "author_handle": "agency_owner_mike", "content": "I run a digital agency that offers fractional CMO services. Here is how we helped a client achieve 300% YoY growth.", "post_url": "https://reddit.com/r/entrepreneur/comments/113", "company_name": "Mike Agency", "published_at": "2026-07-24T19:00:00Z"},
    {"platform": "x", "author_name": "ScaleFast Media", "author_handle": "scalefast_media", "content": "Stop burning cash on agencies that don't deliver. ScaleFast provides embedded Fractional CMOs and performance growth teams.", "post_url": "https://x.com/scalefast_media/status/114", "company_name": "ScaleFast Media", "published_at": "2026-07-28T14:10:00Z"},
    {"platform": "linkedin", "author_name": "Tom Bradley", "author_handle": "tom-bradley-advisors", "content": "Unlocking enterprise growth: How our fractional marketing leadership model transforms B2B sales pipelines.", "post_url": "https://linkedin.com/posts/tom-bradley-115", "company_name": "Bradley Advisors", "published_at": "2026-07-27T09:00:00Z"},
    {"platform": "threads", "author_name": "Elevate Marketing", "author_handle": "elevate_mktg", "content": "Need an agency that actually understands Fractional CMO leadership? Check out our case studies at elevate.io", "post_url": "https://threads.net/@elevate_mktg/post/116", "company_name": "Elevate Marketing", "published_at": "2026-07-25T13:40:00Z"},

    # --- UNRELATED CHATTER, JOB LISTINGS & COMMENTARY ---
    {"platform": "x", "author_name": "Tech Jobs Daily", "author_handle": "techjobsdaily", "content": "Hiring: Senior Backend Engineer (Go / Kubernetes) at FinTech company. Fully remote, $180k-$220k + equity.", "post_url": "https://x.com/techjobsdaily/status/117", "company_name": "Tech Jobs Daily", "published_at": "2026-07-28T13:00:00Z"},
    {"platform": "reddit", "author_name": "dev_rant_user", "author_handle": "dev_rant_user", "content": "Why is everyone on LinkedIn calling themselves a Fractional CMO or Fractional CTO now? It feels like buzzword inflation.", "post_url": "https://reddit.com/r/consulting/comments/118", "company_name": "Reddit User", "published_at": "2026-07-27T21:00:00Z"},
    {"platform": "linkedin", "author_name": "Global News Digest", "author_handle": "global-news-digest", "content": "Federal Reserve announces latest interest rate decision amid cooling inflation data.", "post_url": "https://linkedin.com/posts/global-news-119", "company_name": "Global News", "published_at": "2026-07-28T15:00:00Z"},
    {"platform": "google", "author_name": "Marketing Law Blog", "author_handle": "google_search", "content": "Legal differences between hiring an independent contractor vs full-time executive.", "post_url": "https://lawblog.com/contracts-120", "company_name": "Law Blog", "published_at": "2026-07-20T10:00:00Z"},
    {"platform": "x", "author_name": "AI Daily News", "author_handle": "aidailynews", "content": "OpenAI releases new open weights model architecture for high-speed agentic reasoning.", "post_url": "https://x.com/aidailynews/status/121", "company_name": "AI Daily", "published_at": "2026-07-28T17:00:00Z"},
    {"platform": "threads", "author_name": "Coffee & Code", "author_handle": "coffee_and_code", "content": "What is your favorite IDE setup for TypeScript in 2026? VS Code or Zed?", "post_url": "https://threads.net/@coffee_and_code/post/122", "company_name": "Coffee & Code", "published_at": "2026-07-27T08:00:00Z"},
    {"platform": "linkedin", "author_name": "HR Executive Hub", "author_handle": "hr-exec-hub", "content": "We are hiring a full-time Senior Recruiting Manager for our Austin headquarters.", "post_url": "https://linkedin.com/posts/hr-exec-123", "company_name": "HR Executive Hub", "published_at": "2026-07-28T11:15:00Z"},
    {"platform": "reddit", "author_name": "crypto_watcher", "author_handle": "crypto_watcher", "content": "Bitcoin breaks key resistance level following institutional ETF inflows.", "post_url": "https://reddit.com/r/crypto/comments/124", "company_name": "Crypto Watcher", "published_at": "2026-07-26T16:00:00Z"},

    # --- MORE MIXED BUYERS & PROVIDERS TO REACH EXACTLY 40 ---
    {"platform": "x", "author_name": "Brian K.", "author_handle": "briank_founder", "content": "We need a Fractional CMO who has scaled a B2B SaaS company from $2M to $10M ARR. Drop portfolio or send DM.", "post_url": "https://x.com/briank_founder/status/125", "company_name": "DataVault", "published_at": "2026-07-28T18:00:00Z"},
    {"platform": "linkedin", "author_name": "Laura Hayes", "author_handle": "laura-hayes-marketing", "content": "Our agency specializes in helping healthtech startups with fractional CMO leadership and omnichannel growth.", "post_url": "https://linkedin.com/posts/laura-hayes-126", "company_name": "Hayes Growth", "published_at": "2026-07-27T14:30:00Z"},
    {"platform": "threads", "author_name": "Chris B.", "author_handle": "chris_b_builds", "content": "Looking for recommendations for a Fractional CMO with deep experience in developer tooling & PLG marketing.", "post_url": "https://threads.net/@chris_b_builds/post/127", "company_name": "DevStack", "published_at": "2026-07-28T19:10:00Z"},
    {"platform": "reddit", "author_name": "saas_guy_sf", "author_handle": "saas_guy_sf", "content": "What is the average monthly retainer for a quality Fractional CMO in the US? Looking to hire one next month.", "post_url": "https://reddit.com/r/SaaS/comments/128", "company_name": "SF SaaS Co", "published_at": "2026-07-28T09:40:00Z"},
    {"platform": "google", "author_name": "VentureBeat RFP", "author_handle": "google_search", "content": "FinTech Startup Issues RFP for Fractional Marketing Leadership and Brand Refresh.", "post_url": "https://venturebeat.com/rfp-129", "company_name": "FinTech One", "published_at": "2026-07-25T11:00:00Z"},
    {"platform": "x", "author_name": "Growth Catalyst", "author_handle": "growth_cat", "content": "We offer Fractional CMO and CRO services for high-growth tech companies. Reach out for a consultation.", "post_url": "https://x.com/growth_cat/status/130", "company_name": "Growth Catalyst", "published_at": "2026-07-28T10:15:00Z"},
    {"platform": "linkedin", "author_name": "Samantha Wu", "author_handle": "samantha-wu-ceo", "content": "Seeking a fractional CMO or specialized growth marketing agency for our series B e-commerce platform.", "post_url": "https://linkedin.com/posts/samantha-wu-131", "company_name": "CartCraft", "published_at": "2026-07-28T15:20:00Z"},
    {"platform": "reddit", "author_name": "marketer_john", "author_handle": "marketer_john", "content": "I am a Fractional CMO offering 10 hours a week for early-stage B2B SaaS startups. DM me if you need strategy.", "post_url": "https://reddit.com/r/freelance/comments/132", "company_name": "John Marketing", "published_at": "2026-07-27T12:00:00Z"},
    {"platform": "x", "author_name": "Tech Events Bot", "author_handle": "techeventsbot", "content": "Upcoming Web Summit 2026 conference schedule announced for November.", "post_url": "https://x.com/techeventsbot/status/133", "company_name": "Tech Events", "published_at": "2026-07-28T06:00:00Z"},
    {"platform": "threads", "author_name": "Sophia Vance", "author_handle": "sophia_vance", "content": "Recommend me your favorite Fractional CMO for B2B cybersecurity brands!", "post_url": "https://threads.net/@sophia_vance/post/134", "company_name": "CyberShield", "published_at": "2026-07-28T16:00:00Z"},
    {"platform": "linkedin", "author_name": "Venture Capital Daily", "author_handle": "vc-daily", "content": "Top 10 B2B SaaS trends to watch in the second half of 2026.", "post_url": "https://linkedin.com/posts/vc-daily-135", "company_name": "VC Daily", "published_at": "2026-07-27T17:00:00Z"},
    {"platform": "google", "author_name": "Forbes Business", "author_handle": "google_search", "content": "Why companies are turning to Fractional CMOs instead of traditional marketing agencies.", "post_url": "https://forbes.com/article-136", "company_name": "Forbes", "published_at": "2026-07-22T08:00:00Z"},
    {"platform": "x", "author_name": "Daniel Kim", "author_handle": "dkim_fintech", "content": "Our FinTech startup is looking for an agency partner or Fractional CMO to revamp our acquisition pipeline.", "post_url": "https://x.com/dkim_fintech/status/137", "company_name": "WealthPulse", "published_at": "2026-07-28T20:00:00Z"},
    {"platform": "linkedin", "author_name": "Growth Agency Inc", "author_handle": "growth-agency-inc", "content": "We scale SaaS companies with full-stack fractional marketing teams. Contact us for a proposal.", "post_url": "https://linkedin.com/posts/growth-agency-138", "company_name": "Growth Agency Inc", "published_at": "2026-07-28T09:30:00Z"},
    {"platform": "reddit", "author_name": "bootstrapper_dev", "author_handle": "bootstrapper_dev", "content": "Should I hire a Fractional CMO or a growth marketing agency first for a bootstrapped B2B SaaS?", "post_url": "https://reddit.com/r/SaaS/comments/139", "company_name": "Bootstrapped SaaS", "published_at": "2026-07-27T18:45:00Z"},
    {"platform": "threads", "author_name": "Agency Finder AI", "author_handle": "agency_finder", "content": "Find top rated marketing agencies and fractional CMOs on our platform. Free for founders.", "post_url": "https://threads.net/@agency_finder/post/140", "company_name": "Agency Finder", "published_at": "2026-07-28T05:00:00Z"}
]

async def run_40_posts_test():
    print("=" * 80)
    print("🧪 LEAN INDEXED INPUT (ID + CONTENT ONLY) LLM EVALUATION TEST")
    print(f"Total Raw API Posts: {len(DUPLICATE_40_POSTS)}")
    print("=" * 80)

    start_time = time.time()
    
    # Process in batches of 20 as done in production social_posts router
    batch_size = 20
    all_matched_posts = []

    for i in range(0, len(DUPLICATE_40_POSTS), batch_size):
        batch = DUPLICATE_40_POSTS[i:i+batch_size]
        print(f"\n🚀 Processing Batch [{i//batch_size + 1}] (Posts {i} to {i+len(batch)-1})...")
        print(f"   -> Stripped metadata. Sending ONLY lean 'id' + 'content' to OpenRouter...")
        matched_results = await batch_classify_social_intent(batch)
        all_matched_posts.extend(matched_results)

    elapsed_time = time.time() - start_time

    print("\n" + "=" * 80)
    print("📊 MATCHED BUYER POSTS RETRIEVED FROM OLD JSON & ENRICHED WITH SUMMARY")
    print("=" * 80)
    print(f"{'PLATFORM':<9} | {'AUTHOR':<18} | {'COMPANY':<16} | {'CATEGORY':<22} | {'AI ONE-LINE SUMMARY'}")
    print("-" * 115)

    for p in all_matched_posts:
        platform = p.get("platform", "unknown")
        author = p.get("author_name", "Unknown")
        company = p.get("company_name", "Unknown")
        category = p.get("service_category", "intent signal")
        summary = p.get("summary", "")
        print(f"{platform:<9} | {author:<18} | {company:<16} | {category[:21]:<22} | {summary[:45]}")

    filtered_out_count = len(DUPLICATE_40_POSTS) - len(all_matched_posts)

    print("\n" + "=" * 80)
    print("📈 FINAL SUMMARY STATS")
    print("=" * 80)
    print(f"⏱️  Total Processing Time : {elapsed_time:.2f} seconds")
    print(f"🟢 Matched ICP Buyer Posts (SAVED TO DB) : {len(all_matched_posts)} / 40 ({len(all_matched_posts)/40*100:.1f}%)")
    print(f"⚪ Unmatched / Seller Ads (FILTERED OUT)   : {filtered_out_count} / 40 ({filtered_out_count/40*100:.1f}%)")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_40_posts_test())

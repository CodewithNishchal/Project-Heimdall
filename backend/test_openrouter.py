import asyncio
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.pipeline.social_classifier import batch_classify_social_intent

async def test_openrouter():
    print("=" * 70)
    print("Testing OpenRouter Batch Classification")
    print("=" * 70)

    # 20 mock posts: mixed intents to stress-test the batch classification
    test_posts = [
        {"content": "Desperately need a performance marketing agency to help us scale our Facebook ads.", "author_name": "User1", "platform": "reddit", "post_url": "url1"},
        {"content": "My facebook ads got banned again. I hate this platform.", "author_name": "User2", "platform": "x", "post_url": "url2"},
        {"content": "Looking for a top-tier SEO expert to audit our e-commerce site.", "author_name": "User3", "platform": "threads", "post_url": "url3"},
        {"content": "We are a digital marketing agency specialized in B2B SaaS growth. Hire us today!", "author_name": "User4", "platform": "linkedin", "post_url": "url4"},
        {"content": "Can anyone recommend a good B2B marketing agency? Our current one isn't driving leads.", "author_name": "User5", "platform": "reddit", "post_url": "url5"},
        {"content": "Just got a new puppy! He's so cute.", "author_name": "User6", "platform": "x", "post_url": "url6"},
        {"content": "I need help with my Google Ads campaign. It's bleeding money. Any freelancers here?", "author_name": "User7", "platform": "reddit", "post_url": "url7"},
        {"content": "What's the best way to cook a steak? Reverse sear or sous vide?", "author_name": "User8", "platform": "threads", "post_url": "url8"},
        {"content": "RFP for digital marketing and PR services for the City of Springfield.", "author_name": "User9", "platform": "google", "post_url": "url9"},
        {"content": "I run a lead gen agency and we just crossed $10k MRR!", "author_name": "User10", "platform": "linkedin", "post_url": "url10"},
        {"content": "Anyone know a good growth marketing agency for a mobile app launch?", "author_name": "User11", "platform": "x", "post_url": "url11"},
        {"content": "Here are 5 tips for improving your SEO ranking in 2026...", "author_name": "User12", "platform": "linkedin", "post_url": "url12"},
        {"content": "Seeking a fractional CMO to guide our marketing team.", "author_name": "User13", "platform": "reddit", "post_url": "url13"},
        {"content": "Does anyone want to buy my used car? DM me.", "author_name": "User14", "platform": "x", "post_url": "url14"},
        {"content": "Our non-profit is looking for a local marketing agency for a rebrand.", "author_name": "User15", "platform": "threads", "post_url": "url15"},
        {"content": "I'm offering free SEO audits for the first 5 people who comment.", "author_name": "User16", "platform": "reddit", "post_url": "url16"},
        {"content": "We need a new web design and marketing agency, our current site is from 1999.", "author_name": "User17", "platform": "linkedin", "post_url": "url17"},
        {"content": "I can't believe the game last night! What a comeback.", "author_name": "User18", "platform": "x", "post_url": "url18"},
        {"content": "Looking to hire a franchise marketing agency to manage 50 locations.", "author_name": "User19", "platform": "reddit", "post_url": "url19"},
        {"content": "We are looking for PPC experts to join our growing agency team.", "author_name": "User20", "platform": "linkedin", "post_url": "url20"}
    ]

    print(f"Sending {len(test_posts)} posts to batch_classify_social_intent()...")
    
    try:
        results = await batch_classify_social_intent(test_posts)
        print("\n--- RESULTS ---")
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"\n--- ERROR ---")
        print(str(e))

if __name__ == "__main__":
    asyncio.run(test_openrouter())

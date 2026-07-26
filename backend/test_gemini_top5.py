import asyncio
import json
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from google.genai import types
from dotenv import load_dotenv
from backend.config import settings

# Enable concise logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
load_dotenv("backend/.env")

PROMPT = """You are a Lead Scoring AI and Senior B2B Sales Intelligence Analyst.

TASK:
Analyze the attached list of 100 company names. 
Use live search to evaluate recent developments (2025-2026) and identify the TOP 5 companies displaying the highest, most actionable sales intent triggers.

EVALUATION & RANKING CRITERIA (Prioritize in order):
1. 💰 Funding & Investment: Recent venture rounds (Series A/B/C+), debt financing, or strategic funding announcements.
2. 📈 Revenue & Scale Milestones: Publicly announced ARR milestones ($10M+, $50M+, $1B+ processing volume, etc.).
3. 👥 Rapid Hiring Spikes: Leadership announcements for hiring 10+ new roles or critical executive expands.
4. 🚀 Major Product / Expansion Launches: Rollouts of new AI tools/platforms, enterprise integrations, or major market expansions.

STRICT EXCLUSIONS (Do NOT pick):
- Companies going through mass layoffs, bankruptcy, or legal trouble.
- Inactive/dormant companies or companies with no verifiable 2025/2026 news.

OUTPUT FORMAT:
Return ONLY a valid JSON array containing exactly the TOP 5 ranked companies formatted as follows:

[
  {
    "rank": 1,
    "company_name": "Exact Brand Name",
    "estimated_domain": "companydomain.com",
    "intent_score": 92,
    "primary_category": "FUNDING | HIRING_SPIKE | PRODUCT_LAUNCH | STRATEGIC_REVIEW",
    "employee_count": "Estimated employee tier (e.g., 50-200, 20-300, etc.)",
    "top_intent_trigger": "1-2 sentence summary of the exact verified trigger event with metrics/dates",
    "suggested_outreach_angle": "1-sentence pitch hook for B2B vendors"
  }
]

CRITICAL RULES:
- Ensure 'estimated_domain' uses the official root website domain (e.g., 'nitra.com', 'readai.com', 'stepful.com').
- Do not include markdown commentary, intro text, or conversational explanations outside the JSON array.

COMPANY LIST TO SCREEN (100 Companies):
1. Read AI
2. Nitra
3. Stepful
4. ProfileTree
5. DigiMark Agency
6. Cognition AI
7. Harvey AI
8. HeyGen
9. ElevenLabs
10. Perplexity AI
11. Cursor
12. Lovable AI
13. Bolt.new
14. Resend
15. Supabase
16. Pinecone
17. Weaviate
18. Qdrant
19. Chroma
20. LangChain
21. LlamaIndex
22. Together AI
23. Fireworks AI
24. Baseten
25. Replicate
26. RunPod
27. OctoAI
28. Anyscale
29. Modal Labs
30. Groq
31. Cerebras
32. Lambda Labs
33. CoreWeave
34. Tensordock
35. Vast.ai
36. DeepL
37. Synthesia
38. Descript
39. Otter.ai
40. Fathom AI
41. Fireflies.ai
42. Granola
43. Superhuman
44. Shortwave
45. Notion
46. Coda
47. Craft
48. Slite
49. GitBook
50. Reader.ai
51. Gamma App
52. Pitch
53. Tome
54. Beautiful.ai
55. Decktopus
56. Typeform
57. Tally
58. Fillout
59. Jotform
60. Reform
61. Clay
62. Apollo.io
63. Lusha
64. ZoomInfo
65. Cognism
66. Kaspr
67. LeadIQ
68. PhantomBuster
69. Captain Data
70. ScrapeBadger
71. Serper
72. Proxycurl
73. Bright Data
74. Oxylabs
75. Smartproxy
76. Zyte
77. ScrapingBee
78. ScraperAPI
79. WebScraper
80. Apify
81. Vercel
82. Netlify
83. Render
84. Railway
85. Fly.io
86. Koyeb
87. Zeabur
88. Northflank
89. Porter
90. SST
91. PostHog
92. June.so
93. Mixpanel
94. Amplitude
95. Heap
96. LogRocket
97. Highlight.io
98. Sentry
99. BetterStack
100. Datadog
"""

async def test_raw_gemini():
    print("\n" + "="*60)
    print("🚀 GEMINI 2.5 FLASH + WEB SEARCH ISOLATED TESTER")
    print("="*60 + "\n")
    
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        print("❌ Missing GEMINI_API_KEY in .env")
        return

    print("Initializing Gemini Client with timeout=60s...")
    client = genai.Client(api_key=api_key, http_options={'timeout': 60.0})
    
    config = types.GenerateContentConfig(
        temperature=0.2,
        tools=[{"googleSearch": {}}]
    )
    
    print("\n[1/2] Sending exactly 100 companies to Gemini 2.5 Flash for Live Web Sweep Grounding...")
    print("Please wait up to 30 seconds for live search resolution...\n")
    
    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-2.5-flash",
                contents=PROMPT,
                config=config
            )
        )
        
        print("\n[2/2] GEMINI TOP 5 SELECTION (JSON OUTPUT)")
        print("-" * 60)
        
        raw_json = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw_json)
        print(json.dumps(data, indent=2))
        
    except Exception as e:
        print(f"\n❌ Error during Gemini execution: {e}")

if __name__ == "__main__":
    asyncio.run(test_raw_gemini())

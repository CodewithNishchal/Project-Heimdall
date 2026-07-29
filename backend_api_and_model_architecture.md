# Heimdall B2B Lead Intelligence Platform — API, AI Model & Infrastructure Audit

This document provides a comprehensive, non-technical overview of the software components, Artificial Intelligence (AI) models, data pipelines, current limitations, and recommended production API upgrades for the Heimdall Lead Intelligence Platform.

---

## 1. Executive Summary

Heimdall operates a multi-stage data engine that scans the web, social media platforms, and business registries to discover high-intent prospective clients (ICPs). 

To deliver real-time buyer intelligence without relying on manual research, the platform uses a hybrid network of **Specialized Data APIs** (for web scraping and company search) and **AI Models** (for intent scoring, quote validation, and automated pitch summaries).

---

## 2. Active AI Models & Large Language Models (LLMs)

| AI Engine / Provider | Specific Model Used | Primary Role in Platform | Cost / Billing Tier |
|---|---|---|---|
| **Google AI (Gemini)** | `gemini-2.5-flash` | **Candidate Screening (Phase 2)**: Scans 100 raw candidate companies from web search and filters out irrelevant dev shops / agencies to select the Top 5 target leads. | Free Tier |
| **Groq LPU Engine** | `llama-3.1-8b-instant`<br/>`llama-3.3-70b-versatile` | **Intent Scoring & Evidence Extraction**: Analyzes raw text from news, job boards, and social posts. Extracts verbatim evidence quotes, scores buying intent (0–100), and validates source links. | Free Tier (High Speed / 500+ tokens/sec) |
| **OpenRouter** | `meta-llama/llama-3.3-70b-instruct`<br/>`openai/gpt-oss-20b:free` | **Pitcher AI & Social Post Classification**: Generates structured 1-sentence summaries for social media intent posts and builds point-wise executive briefs (Hiring, Funding, Leadership) for sales outreach. | Free / Ultra Low-Cost |

---

## 3. Data Collection & Web Scraping APIs

| Platform / Service | Scraper / Actor Name | Data Collected | API Endpoints Used |
|---|---|---|---|
| **Exa AI Search** | Exa Neural Web Search | Discovers 100 target companies matching ICP criteria across the US. | `https://api.exa.ai/search` |
| **Google Serper API** | Serper Search & Google News | Resolves official company website domains, extracts Google News, and Knowledge Graphs. | `https://google.serper.dev/search`<br/>`https://google.serper.dev/news` |
| **ScrapeBadger** | ScrapeBadger Twitter Tweet Advanced Search | Crawls real-time buyer intent tweets on X (Twitter). | `https://scrapebadger.com/v1/twitter/tweets/advanced_search` |
| **ScrapeBadger** | ScrapeBadger Reddit Post Search | Crawls buyer intent threads and discussions on Reddit. | `https://scrapebadger.com/v1/reddit/search/posts` |
| **Apify** | `harvestapi~linkedin-company` | Fetches verified company headcount, industry, description, and headquarters. | `https://api.apify.com/v2/acts/harvestapi~linkedin-company/runs` |
| **Apify** | `harvestapi~linkedin-company-posts` | Retrieves official company updates and corporate LinkedIn posts. | `https://api.apify.com/v2/acts/harvestapi~linkedin-company-posts/runs` |
| **Apify** | `harvestapi~linkedin-post-search` | Scans public LinkedIn posts for buyer intent keywords and RFPs. | `https://api.apify.com/v2/acts/harvestapi~linkedin-post-search/run-sync-get-dataset-items` |
| **Apify** | `apidojo~tweet-scraper` | Fallback real-time Twitter tweet search scraper. | `https://api.apify.com/v2/acts/apidojo~tweet-scraper/run-sync-get-dataset-items` |
| **ScrapeCreators** | ScrapeCreators Threads Search | Crawls micro-intent posts on Instagram Threads. | `https://api.scrapecreators.com/v1/threads/search` |
| **ScrapeCreators** | ScrapeCreators Google Search | Extracts specialized RFP and vendor search results from Google. | `https://api.scrapecreators.com/v1/google/search` |

---

## 4. Key Gaps & Recommended Production Upgrades

While the platform is fully operational, replacing basic scraping fallbacks with **enterprise-grade data APIs** will significantly increase contact accuracy, deliverability, and outreach conversion rates for sales teams.

---

### A. Executive Contact & Verified Email Extraction
- **Current Gap**: Heimdall currently uses Google Search (Serper API) to find executive names on LinkedIn (`site:linkedin.com/in`), and infers email addresses using domain MX records and standard patterns (`first.last@company.com`).
- **Business Risk**: Higher email bounce rates (20–30%), which can damage cold email domain sender reputation and land outreach emails in spam folders. Lacks verified direct-dial phone numbers.
- **Recommended API Upgrades**:
  - **Apollo.io API**: Provides 275M+ verified decision-maker profiles, direct work emails, verified mobile phone numbers, and title filtering.
  - **Prospeo.io API** / **Hunter.io API**: Delivers real-time SMTP deliverability verification with a 98%+ deliverability guarantee to protect cold email domains.

---

### B. LinkedIn Company Firmographics & Growth Trends
- **Current Gap**: Heimdall uses third-party web scraping actors on Apify (`harvestapi~linkedin-company`) to fetch headcount and industry details.
- **Business Risk**: Web scraping actors are subject to LinkedIn rate limits, anti-bot blocks, and longer response latencies (10–25 seconds per company).
- **Recommended API Upgrades**:
  - **Proxycurl API** or **CoreSignal API**: Enterprise B2B data providers offering clean REST endpoints for real-time company headcount growth trends, employee retention, and official executive rosters.

---

### C. Background Pipeline Execution Architecture
- **Current Gap**: Manual pipeline execution (`POST /api/pipeline/run`) currently processes sweeps on the main web server thread.
- **Business Risk**: A full 4-minute discovery sweep can cause HTTP request timeouts on single-worker server deployments.
- **Recommended Infrastructure Upgrades**:
  - **Celery + Redis Task Queue**: Offloads background data sweeps to dedicated worker processes.
  - **WebSockets / Server-Sent Events (SSE)**: Pushes real-time progress updates directly to the frontend UI without blocking server HTTP threads.

---

### D. CRM & Automated Outreach Integrations
- **Current Gap**: High-intent leads and pitch briefs are stored locally in the Heimdall PostgreSQL/SQLite database.
- **Business Risk**: Sales representatives must manually copy and paste lead details into outreach tools.
- **Recommended Integration Upgrades**:
  - **Instantly.ai / Smartlead.ai API**: Automatically syncs high-intent leads into active cold email campaigns.
  - **HubSpot / Salesforce Webhooks**: Enables 1-click lead push directly into your CRM.

---

## 5. Summary of Architecture Benefits

1. **Multi-Provider Redundancy**: If any single API provider (e.g. ScrapeBadger or Serper) undergoes maintenance, the system automatically falls back to secondary sources (Apify, OpenRouter, or Gemini) without interrupting pipeline execution.
2. **Cost-Efficient Hybrid Model**: Uses free-tier LLM engines (Groq LPUs & Gemini Flash) for heavy data processing, keeping operational costs under $0.01 per scanned company lead.
3. **Auditability**: Every extracted intent signal includes a 100% verified quote and direct permalink back to the source post/article for human verification.

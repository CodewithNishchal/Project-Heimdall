# Heimdall: AI-Powered Target Acquisition System

## The Core Problem
Sales organizations currently rely on slow, manual research to find companies that need outbound infrastructure and sales support. Identifying high-intent signals (funding rounds, sales hiring, pivot news) is a fragmented and inconsistent process.

## Our Solution (POC)
Heimdall is an autonomous, full-stack lead intelligence platform. It automatically discovers targets, scrapes public intent signals, runs strict ICP filtering, and leverages LLMs (Gemini/Claude) to score leads and generate contextual outreach blueprints.

---

### 1. Autonomous Company Discovery
Instead of relying on a hardcoded list, Heimdall runs multi-threaded discovery sweeps using `python-jobspy` (LinkedIn/Indeed for SDR hiring) and `NewsAPI` (startup funding and expansion news). It uses a local NLP model (`spaCy`) to extract organizational entities directly from raw articles.

### 2. The Hybrid AI Scoring Engine
To balance token cost and accuracy, we implemented a senior-level hybrid scoring architecture:
*   **The ICP Gatekeeper (Rules):** Instantly filters out poorly sized companies (e.g., >500 employees) or incompatible industries using firmographic data before they ever hit the LLM.
*   **The Gemini Engine (LLM):** Surviving companies have their scraped signals passed into Gemini 2.5 Flash using strict JSON schemas. Gemini evaluates the signals and returns a 0-100 Intent Score, a Priority Tier, and a detailed written AI Verdict.

### 3. Contact Extraction & Enrichment
Using the Serper API, Heimdall dynamically searches LinkedIn for Vice Presidents of Sales, Revenue Leaders, and Founders at the target company, giving sales reps the exact names to target. Zero-cost firmographics are gathered via Clearbit Autocomplete and Wikipedia.

### 4. "Pitcher Mode" (Actionable AI)
Heimdall goes beyond just scoring. By clicking a button in the UI, the platform feeds the scraped intent signals and company context into Claude Haiku or Gemini to automatically generate a highly contextual, 3-line cold email opener ready to be copied and sent.

### 5. Automated Pipelines
The backend uses `APScheduler` to run autonomous web sweeps and background data ingestion on a scheduled cron job without any human intervention.

---

## V1 vs V2 Roadmap

**What we built for V1 (Scope):** 
A working proof-of-concept that demonstrates the entire end-to-end pipeline (Discovery → Enrichment → AI Scoring → Contact Extraction → Email Generation). We prioritized speed, rapid API integration, and hybrid scoring architecture over perfection to prove the value quickly.

**What we would add in V2:**
*   **More signals:** Adding G2/Capterra buyer intent data and X (Twitter) "dark social" listening.
*   **Better enrichment:** Integrating Apollo.io or Hunter.io for verified email deliverability (SMTP handshakes) instead of scraped/generated emails.
*   **Stronger scoring:** Implementing a Machine Learning regression model that continuously trains its weights based on actual "Closed-Won" CRM feedback.
*   **Automation pipelines:** Native two-way sync with Salesforce/HubSpot to automatically push the generated Pitcher Mode emails directly into Outreach.io sequences.

---

## Tech Stack
*   **Backend:** Python, FastAPI, SQLite, APScheduler, spaCy
*   **Frontend:** React, Vite, Tailwind CSS, Framer Motion
*   **AI / APIs:** Google Gemini 2.5 Flash, Claude Haiku, Serper API, NewsAPI, JobSpy

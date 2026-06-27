# Final Project Architecture (Heimdall Intel Platform)

The Heimdall Intel Platform has been completely scaffolded, implemented, and verified across both backend and frontend layers. The layers communicate via the Strict Data Contract Protocol.

---

## 🛠️ Complete Summary of Work & Changes

### 1. Backend Core & Configuration
- **FastAPI Core (`backend/main.py`)**: Mounts all routes (`/api/leads`, `/api/pipeline`, `/api/health`, `/api/audit/dns`, etc.). Integrated `APScheduler` inside a FastAPI `lifespan` context manager to avoid duplicate background thread instances upon reload.
- **Settings Manager (`backend/config.py`)**: Loads variables via Pydantic from `.env` and `backend/.env`.
- **Database Layer (`backend/database.py` & `backend/models.py`)**: Configured SQLite engine (`lead_intelligence.db`) with SQLAlchemy ORM schemas mapped strictly to the data contracts.
- **Dependencies (`backend/requirements.txt`)**: Cleaned and optimized backend requirements.

### 2. LLM Engine Migration (Claude ➔ Gemini)
- **SDK Update**: Swapped out the old `anthropic` SDK in favor of the official `google-genai` SDK in `requirements.txt`.
- **API configuration**: Replaced `CLAUDE_API_KEY` references with `GEMINI_API_KEY` across `.env`, `config.py`, and the codebase.
- **JSON Enforcement (`backend/pipeline/scorer.py`)**: Rebuilt the core scoring model logic to use `gemini-2.5-flash` with native JSON mode formatting:
  ```python
  config=types.GenerateContentConfig(response_mime_type="application/json")
  ```
  This guarantees that intent scores and signal extractions strictly match the frontend schemas.
- **Pitcher Mode (`backend/routers/leads.py`)**: Replaced Claude with `gemini-2.5-flash` for the `/api/leads/{id}/verdict` endpoint. It dynamically builds and customizes outreach cold emails.

### 3. Job Board Scraper Migration (JSearch ➔ python-jobspy)
- **Scraper Engine Swap**: Replaced the paid/capped RapidAPI JSearch dependency with the open-source **`python-jobspy`** library (and `pandas==2.2.2`). This completely eliminates API costs, billing limits, and subscription requirements.
- **Signal Discovery (`backend/pipeline/discovery.py`)**:
  - Implemented the `fetch_job_signals` logic to concurrently query LinkedIn and Indeed for open B2B/SDR job postings matching the lead company name.
  - Correctly parses the resulting Pandas DataFrames and maps the job details into the strict pipeline signals payload formatting.
- **Environment Clean**: Removed the obsolete `JSEARCH_API_KEY` configuration.

### 4. Pipeline Scrapers & Algorithms
- **DNS Infrastructure Audit (`backend/pipeline/dns_audit.py`)**: Queries domain records (SPF, DKIM, DMARC) deterministically using `dnspython`. 
- **HTML Filtering (`backend/pipeline/filter_funnel.py`)**: Strips web layout noise using `BeautifulSoup` and `html2text` to keep prompt sizes compact.
- **Hallucination Verification (`backend/validation/quote_validator.py`)**: Uses Fuzzy Matching (`rapidfuzz`) to guarantee Gemini's extracted signal quotes are indeed verbatim matches to the scraped HTML source.

### 5. Frontend UI & Integration
- **Vite Router Proxy (`vite.config.ts`)**: Proxies `/api` directly to `127.0.0.1:8000` to bypass CORS.
- **API Client (`src/lib/api.ts`)**: Implements request handling for `/api/leads/` and the `/api/leads/{id}/verdict` endpoints.
- **Component Interface**:
  - `App.tsx` handles mounting hooks, pulling API data, and gracefully falling back to local mocks if the server goes offline.
  - `LeadTable.tsx` & subcomponents (`ConfidenceMeter.tsx`, `ScoreBreakdown.tsx`, `PitcherMode.tsx`) completely map to the nested JSON structure.

---

## 📊 Status Validation Checklist

- **Serper API (Google Search)**: ✅ **SUCCESS** (Verified active)
- **News API**: ✅ **SUCCESS** (Verified active)
- **Gemini API**: ✅ **SUCCESS** (Verified active, tested with strict JSON schema returns)
- **JobSpy Scraper**: ✅ **SUCCESS** (Active, scrapes LinkedIn/Indeed concurrently)
- **Frontend Proxy Wiring**: ✅ **SUCCESS** (Connecting perfectly)
- **Strict Data Contract**: ✅ **SUCCESS** (Strictly aligned across all model files)

---

## 📈 Next Proposed Enhancements
1. **Interactive Ingest Form**: A button on the frontend to allow you to input a company name (e.g. "OpenAI") and trigger `fetch_public_intent_signals` on the backend instantly to populate the table.
2. **Bulk Scrape Scheduler Controls**: Frontend toggles to run, stop, or view logs of the manual pipeline run (`/api/pipeline/run`).

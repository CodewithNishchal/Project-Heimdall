# Project Heimdall: Final Modifications Left

This document maps out the remaining implementation tasks, structural gaps, runtime bugs, logic flaws, and the prioritized roadmap to transition Project Heimdall from a proof-of-concept into a fully persistent, automated enterprise platform.

---

## 📋 Core Architectural Plan

### 1. Automated Batch Pipeline Ingestion (APScheduler Implementation)
*   **Current State:** 
    The scheduler is configured in [pipeline_scheduler.py](file:///c:/IIITN/Semester%207/Z-Intern/Crework/Project%20Heimdial/backend/scheduler/pipeline_scheduler.py), but its execution loop (`run_pipeline_job`) is currently a stub that registers a mock telemetry completion log rather than performing actual scans.
*   **Remaining Work:**
    *   **Refactor Ingestion:** Extract the core ingestion sequence (fetching JobSpy/NewsAPI signals, running Gemini evaluations, conducting DNS audits) out of [leads.py](file:///c:/IIITN/Semester%207/Z-Intern/Crework/Project%20Heimdial/backend/routers/leads.py) and into a reusable orchestrator service (`backend/pipeline/orchestrator.py`).
    *   **Wire to Scheduler:** Update `run_pipeline_job` to loop through a targeted list of companies (e.g., `["Vercel", "Stripe", "Supabase"]`) and trigger the orchestrator.
    *   **Rate Limit Delays:** Introduce a pause (e.g., `time.sleep(10)`) between each scan iteration to avoid Gemini API `429 RESOURCE_EXHAUSTED` rate limits.

### 2. Full Lead Persistence (Database Integration)
*   **Current State:** 
    The frontend reads all active lead profiles from `MOCK_DETAILED_LEADS` (an in-memory dictionary). Although manual lead ingestion (`POST /api/leads/ingest`) writes a partial snapshot to the SQLite `lead_snapshots` table, the API itself still relies on memory. If the backend server restarts, all manual sweeps and deletions are lost.
*   **Remaining Work:**
    *   **Database Schema Expansion:** Modify the database schema in [models.py](file:///c:/IIITN/Semester%207/Z-Intern/Crework/Project%20Heimdial/backend/models.py) to store full lead details, including nested relational tables/fields for `signals` and `dns_audit`.
    *   **CRUD Refactoring:** Refactor [leads.py](file:///c:/IIITN/Semester%207/Z-Intern/Crework/Project%20Heimdial/backend/routers/leads.py) endpoints (`GET /`, `GET /{id}`, `DELETE /{id}`) to read from and write directly to the database.

### 3. V2 Roadmap: Contact Enrichment (The "Contact Bonus")
*   **Current State:** 
    As noted in the [README.md](file:///c:/IIITN/Semester%207/Z-Intern/Crework/Project%20Heimdial/README.md), contact details are currently out of scope.
*   **Remaining Work:**
    *   **API Integrations:** Register and integrate a bulk enrichment provider (e.g., Hunter.io or Apollo).
    *   **Contact Matching:** Automatically enrich the lead object with decision-maker emails, titles, and names (e.g. Sales Directors or VP of Sales) matching the company domain during ingestion.

---

## 🔍 Detailed Diagnosis of Gaps & Logic Flaws

The project tracking widget flags several key issues:

### 🧩 Missing Components & Gaps
*   **LeadSnapshot Schema is too thin:** The current schema in [models.py](file:///c:/IIITN/Semester%207/Z-Intern/Crework/Project%20Heimdial/backend/models.py) only has basic columns and lacks columns or relations to store the full `signals` list, `dns_audit` JSON/tables, `icp_fit`, `badge`, and `why_now` text. This blocks persisting/retrieving the full `LeadDetailResponse`.
*   **Orchestrator file does not exist:** There is no `orchestrator.py` module to serve as the connective tissue between the scheduler and the extraction/scoring modules.
*   **API reads from Memory:** `GET /api/leads/` reads from `MOCK_DETAILED_LEADS` instead of the database.
*   **Pitcher Mode uses Mock Delay:** [PitcherMode.tsx](file:///c:/IIITN/Semester%207/Z-Intern/Crework/Project%20Heimdial/frontend/src/components/PitcherMode.tsx) still relies on a `setTimeout` mock to simulate loading the email body instead of making a call to `POST /api/leads/{id}/verdict`.
*   **KPI Ribbon is Hardcoded:** [KPIRibbon.tsx](file:///c:/IIITN/Semester%207/Z-Intern/Crework/Project%20Heimdial/frontend/src/components/KPIRibbon.tsx) shows static numbers rather than retrieving telemetry from `/api/pipeline/status`.
*   **Pipeline Status Telemetry:** `/api/pipeline/status` returns a hardcoded count.

![Gaps and Missing Components](file:///C:/Users/Nischal%20Verma/.gemini/antigravity-ide/brain/2dc56de3-562f-4513-8224-0906ee969a59/media__1782581829317.png)

### ⚠️ Runtime Crashes & Silent Issues
*   **Scheduler Lifespan Order Error:** In [main.py](file:///c:/IIITN/Semester%207/Z-Intern/Crework/Project%20Heimdial/backend/main.py), calling `scheduler.add_job()` runs before the FastAPI lifespan configuration is fully defined.
*   **Async/Sync Mismatch:** The scheduler job `run_pipeline_job()` runs synchronously, but `fetch_public_intent_signals()` inside [discovery.py](file:///c:/IIITN/Semester%207/Z-Intern/Crework/Project%20Heimdial/backend/pipeline/discovery.py) is an `async def`. Calling this from a synchronous context without `asyncio.run()` will trigger runtime errors.
*   **Unapplied ICP Penalties:** In [icp_filter.py](file:///c:/IIITN/Semester%207/Z-Intern/Crework/Project%20Heimdial/backend/pipeline/icp_filter.py), certain penalties are calculated or declared but never properly factored into the final score.
*   **Bypassed Cache Check:** The cache evaluation function `check_recent_cache()` in [filter_funnel.py](file:///c:/IIITN/Semester%207/Z-Intern/Crework/Project%20Heimdial/backend/pipeline/filter_funnel.py#L38-L70) returns a boolean indicating whether a domain has been scanned recently, but the caller never evaluates it, rendering the cache check bypassed.

![Runtime Crashes and Silent Behavior](file:///C:/Users/Nischal%20Verma/.gemini/antigravity-ide/brain/2dc56de3-562f-4513-8224-0906ee969a59/media__1782581838384.png)

---

## 🗺️ Step-by-Step Priority Execution Roadmap

To address the gaps systematically, the following execution order is recommended:

| Step | Task | Duration | Priority |
|---|---|---|---|
| **1** | **Expand LeadSnapshot Model**<br>Add `full_payload` JSON column or related tables to support full lead data persistence in [models.py](file:///c:/IIITN/Semester%207/Z-Intern/Crework/Project%20Heimdial/backend/models.py). | 30 min | Do first |
| **2** | **Create Orchestrator Service**<br>Write `orchestrator.py` containing the 7-step pipeline execution flow (Discovery → Filter → Scoring → DNS Audit → Cache → DB Write). | 2-3 hrs | Do second |
| **3** | **Wire Background Scheduler**<br>Update `run_pipeline_job()` in [pipeline_scheduler.py](file:///c:/IIITN/Semester%207/Z-Intern/Crework/Project%20Heimdial/backend/scheduler/pipeline_scheduler.py) with the `TARGET_COMPANIES` loop and a `time.sleep(10)` rate-limit delay. | 20 min | Do third |
| **4** | **Refactor API Lead Retrieval**<br>Rewrite `GET /api/leads/` and `GET /api/leads/{id}` in [leads.py](file:///c:/IIITN/Semester%207/Z-Intern/Crework/Project%20Heimdial/backend/routers/leads.py) to read directly from the SQLite database. | 45 min | Do fourth |
| **5** | **Fix Pitcher Mode UI**<br>Update [PitcherMode.tsx](file:///c:/IIITN/Semester%207/Z-Intern/Crework/Project%20Heimdial/frontend/src/components/PitcherMode.tsx) to perform real API POST requests to `/api/leads/{id}/verdict` rather than relying on `setTimeout` mocks. | 15 min | Do fifth |
| **6** | **Resolve Async/Sync Mismatch**<br>Fix execution contexts between asynchronous scraping calls and the synchronous scheduler threads. | 20 min | Do sixth |
| **7** | **Standardize LLM Engines**<br>Align on Gemini (or Claude) consistently across [scorer.py](file:///c:/IIITN/Semester%207/Z-Intern/Crework/Project%20Heimdial/backend/pipeline/scorer.py) and [leads.py](file:///c:/IIITN/Semester%207/Z-Intern/Crework/Project%20Heimdial/backend/routers/leads.py). | 20 min | Do seventh |
| **8** | **Connect KPI Ribbon UI**<br>Wire [KPIRibbon.tsx](file:///c:/IIITN/Semester%207/Z-Intern/Crework/Project%20Heimdial/frontend/src/components/KPIRibbon.tsx) to fetch real telemetry from `/api/pipeline/status`. | 45 min | Do eighth |
| **9** | **Fix Lead Processed Counts**<br>Expose the accurate count of processed leads from the database inside `/api/pipeline/status`. | 10 min | Do ninth |
| **10** | **Fix Lifespan Initialization**<br>Reorder `scheduler.add_job()` startup logic inside [main.py](file:///c:/IIITN/Semester%207/Z-Intern/Crework/Project%20Heimdial/backend/main.py) to ensure correct lifecycle startup. | 10 min | Do tenth |
| **11** | **V2: Hunter.io Contact Enrichment**<br>Integrate decision-maker email/role discovery in the pipeline orchestrator. | V2 Bonus | After 1-10 |

![Implementation Priority Roadmap](file:///C:/Users/Nischal%20Verma/.gemini/antigravity-ide/brain/2dc56de3-562f-4513-8224-0906ee969a59/media__1782581862112.png)

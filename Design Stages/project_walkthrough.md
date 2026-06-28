# Implementation Walkthrough: Stage by Stage Guide

Building the Heimdall Lead Intelligence Platform follows a systematic, five-stage pipeline. This approach allows us to progressively add complexity, starting with data extraction and moving all the way up to automated background processing and AI-driven sales interfaces.

Here is the step-by-step walkthrough of how we execute the platform build.

---

## Stage 1: Data Sourcing & Core Infrastructure
**Goal:** Establish the foundation and configure the environment.

* **Database & ORM:** We set up the SQLite database and SQLAlchemy Object-Relational Mapper (`database.py` and `models.py`). This gives us persistent storage for tracking lead intent scores and pipeline run statuses.
* **DNS Auditing:** We build the `dns_audit.py` engine using `dnspython` to query public DNS records. This checks a target domain's SPF, DKIM, and DMARC configurations to give us an immediate security posture assessment before doing expensive LLM operations.
* **API Shell:** We construct the primary FastAPI entrypoint (`main.py`) with standard CORS middleware and our first `/api/audit/dns` route.

## Stage 2: The Filter Funnel & Guardrails
**Goal:** Drastically reduce LLM computing costs and drop bad leads before processing.

* **HTML Trimming:** We introduce `BeautifulSoup` and `html2text` in `filter_funnel.py`. By stripping out CSS, navigation bars, and scripts, we reduce the payload size by up to 90%, saving massive amounts of Claude API tokens.
* **Zero-Cost Keyword Gating:** A fast algorithmic gate checks for anchor keywords (like "funding", "hiring SDR"). If a company has none of these keywords, we drop them instantly at zero cost.
* **Smart Caching:** We implement a 7-day SQLite cache check. If we've already parsed a domain recently, we return the cached result instead of hitting the AI endpoint again.

## Stage 3: The Scoring Engine & ICP Constraints
**Goal:** Apply business logic and deterministic math to the AI's semantic evaluation.

* **Claude API Integration:** We wire in the Anthropic SDK (`scorer.py`) to generate the initial unstructured AI assessment of the lead's intent.
* **Time Decay:** We apply a mathematical degradation curve (`time_decay.py`). A signal from 3 months ago is worth much less than a signal from yesterday, ensuring sales reps focus on fresh intent.
* **ICP Penalties:** We layer on hard caps and point deductions based on firmographics (`icp_filter.py`). For instance, if a company is an Enterprise giant (500+ employees) or out-of-sector, we aggressively throttle their intent score.
* **Hallucination Checking:** Using `rapidfuzz`, we cross-reference the exact quote the AI provides against the raw source text. If the AI hallucinates, it's penalized and marked as unverified.

## Stage 4: Automation & Background Scheduling
**Goal:** Convert the platform from a manual tool into a self-updating, autonomous engine.

* **In-Process Scheduler:** Instead of setting up complex external systems like Celery or Redis, we use `APScheduler` inside FastAPI's `@asynccontextmanager lifespan`. This allows the server to run a completely automated background lead ingestion sweep every 24 hours.
* **Freshness Tracking:** During the background job, the system compares the new intent score against the historical score stored in SQLite (`pipeline_scheduler.py`). This computes "score up" or "score down" deltas that map to freshness UI badges.

## Stage 5: The Trust Layer & Conversion Tools
**Goal:** Expose the data to the frontend UI and build trust with the sales representatives.

* **List and Detail Endpoints:** We build out the actual endpoints in `leads.py` (like `GET /api/leads`) that the React frontend will poll to render the Lead Table and Score Breakdown matrices.
* **Lazy-Loaded "Pitcher Mode":** We expose a `POST /api/leads/{id}/verdict` endpoint. This is specifically designed to only call Claude to generate a personalized cold email template *when the user actually clicks the button*. This avoids generating emails for hundreds of leads that the sales rep never opens.
* **Trust UI Metrics:** We wire the backend data directly into the React components (`ConfidenceMeter.tsx` and `ScoreBreakdown.tsx`), allowing reps to instantly see which quotes were mathematically verified and how the score was calculated.

---

> [!TIP]
> **What's Next?**
> Since the Markdown guides are now fully patched and aligned with the architecture, our next step is to begin the actual code creation. We can start creating the physical `backend/` and `frontend/` folders and placing these Python/TypeScript files on your local drive.

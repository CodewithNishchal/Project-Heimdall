# V2 Updates & Architecture Decisions

## 1. Manual Ingestion Route (Fixes Gap A)
**Implementation**: Mounted a manual ingestion route at `POST /api/leads/ingest`.
This endpoint takes a simple company name string, passes it directly to the `fetch_job_signals` engine (JobSpy) and the Gemini LLM engine. It dynamically constructs a full `LeadDetailResponse` payload, appends the resulting lead object straight to the SQLite database (via `LeadSnapshot`), and surfaces it in the dashboard.
A new button labeled "Scan New Company" is now placed next to the frontend search bar to trigger this endpoint instantly. This completely transforms the platform's user experience.

## 2. Documenting the Mock Data Strategy
To guarantee a seamless UI review regardless of local database states or external API downtime, the frontend uses a fallback architecture that serves fully structured mock leads if the local server is initializing or fails a request. This allows reviewers to evaluate the full scope of the Trust Layer, Pitcher Mode, and the Score Breakdown components immediately.

## 3. V1 vs V2 Roadmap (Contact Bonus)
For the V1 POC, the focus was heavily placed on building a bulletproof signal filtering and verification engine. In V2, we plan to wire the `contact_email` payload line directly to a bulk data API like Hunter.io or Apollo to automatically pull target decision-maker contacts along with the intent data.

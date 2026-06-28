# Heimdall Pipeline & UI Update

This document summarizes the key backend and frontend improvements implemented in today's session.

## 1. Frontend UI Enhancements
- **Contacts Data Grid:** Updated the frontend typings (`LeadDetailResponse`) and enhanced `LeadTable.tsx` to gracefully render extracted contact information. Contacts now appear in a sleek, responsive grid inside the expanded company row, displaying their Name, Title, a clickable Email Address, and dynamically colored confidence/source badges.
- **Empty States:** Added a clean empty-state fallback message (`"No public contacts found on [domain] during this sweep."`) for when highly secure domains block contact extraction, preventing the section from rendering blank.
- **Clickable Company Links:** Added a direct, clickable URL link (e.g., `company.com ↗`) in the expanded row, allowing users to jump straight to the target's website with one click.
- **Header Refinement:** Optimized the vertical screen real estate by reducing the massive `p-10` padding on the main Heimdall header in `App.tsx` down to a sleeker `p-4`, creating a more compact and premium dashboard feel.

## 2. Backend Extraction & Formatting Fixes
- **Domain Resolution (`.com` bug):** Fixed a critical string manipulation bug in `discovery.py` (`resolve_domain`) where `.com` was being redundantly appended to already valid domains (e.g., resulting in `stripe.com.com`). This ensures the downstream NLP and contact scrapers successfully hit real domains without encountering DNS errors.
- **Recency & Source Parsing:** Fixed the `UNKNOWN` recency bug and broken `Source` links in the UI. Enforced strict extraction parameters to ensure dates are properly parsed into standard ISO 8601 format and URLs are explicitly isolated from the raw scraped HTML.

## 3. Database Duplication Fix
- **SQLite Upsert Logic:** Fixed a database inflation issue where `orchestrator.py` (`_persist_lead`) was generating new UUIDs and blindly inserting duplicate rows for the same company across different pipeline runs. 
- The persistence layer now executes a proper SQLAlchemy **Upsert**: it actively queries `lead_intelligence.db` by `company_name` and updates the existing record's score and metadata rather than cloning it.
- Ran an automated SQL cleanup to prune all pre-existing duplicates from the local database.

## 4. Pipeline Testing Controls
- **Controlled Discovery:** Temporarily adjusted `discovery.py` to allow rate-limited testing sweeps (1 to 2 companies at a time) to ensure the end-to-end extraction pipeline behaves correctly before unleashing full batch volumes.

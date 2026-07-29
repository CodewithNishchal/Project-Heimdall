# Heimdall Backend Data Requirements & Pipeline Integration Specification

## 1. Executive Summary & Engine Verification

### Verified LLM Engine Mapping
After cross-checking `backend/pipeline/scorer.py`, `backend/pipeline/orchestrator.py`, and `backend/routers/leads.py`:
- **Phase 1 Autonomous Discovery**: Exa AI Neural Search (`https://api.exa.ai/search`).
- **Phase 2 Candidate Selection**: Gemini 2.5 Flash Grounded Model (`gemini-2.5-flash`).
- **Phase 3 Entity Resolution**: Apify HarvestAPI (`harvestapi~linkedin-company` & `harvestapi~linkedin-company-posts`) with **Serper Knowledge Graph Fallback**.
- **Phase 4 & 5 Multi-Platform Sweeps**: ScrapeBadger X/Twitter + Reddit APIs & Serper Executive Contact Extraction.
- **Phase 6 Intent Synthesis & Scoring**: **Groq API (`llama-3.1-8b-instant`)** in `scorer.py` (`analyze_lead_intent_with_llm`).
- **Pitcher Mode**: **Groq API (`llama-3.3-70b-versatile`)** in `leads.py` (`_generate_pitch_with_groq`).

---

## 2. API Data Availability vs. LLM Extraction Audit

### Analysis of Raw Harvested Data:
The APIs already return abundant raw data:
- **Apify HarvestAPI**: Official employee count, industry name, company description, logo, website URL, and 5 recent LinkedIn posts.
- **ScrapeBadger Twitter & Reddit**: Recent tweets and subreddits mentioning funding, agency hiring, or expansion.
- **Exa AI**: High-intent job descriptions detailing $10M–$20M revenue goals, fractional CMO requirements, and ad spend budgets.

### The Missing Gap (`why_now`, `company_segment`, `signal_tags`):
Currently, `scorer.py` calls Groq for intent score and verbatim signals, but because Groq's JSON schema did not request `why_now` or `signal_tags`, `scorer.py` defaults `why_now` to `"Intent signals detected"`.

### Recommended Groq Prompt Schema Update:
By adding **3 lightweight fields** (`why_now`, `company_segment`, `signal_tags`) to Groq's prompt schema in `backend/pipeline/scorer.py`, Groq will automatically generate them during Phase 6 with zero extra API latency.

---

## 3. Groq Extraction Prompt Standard (`backend/pipeline/scorer.py`)

Below is the exact updated prompt schema to be passed to **Groq API (`llama-3.1-8b-instant`)**:

```python
prompt = f"""
Analyze {company_name} using the provided harvested signals below.

=== INPUT HARVESTED SIGNALS ===
{cleaned_html}
===============================

TARGET KEYWORDS: [{keywords_str}]

TASK:
Extract intent signals matching TARGET KEYWORDS, generate a 2-sentence 'why_now' trigger statement, assign intent category tags, and calculate a composite intent score.

OUTPUT JSON SCHEMA:
{{
  "company_name": "{company_name}",
  "industry": "Specific Industry Name (e.g., FinTech, B2B SaaS, EdTech, Healthcare, E-Commerce, Retail)",
  "company_segment": "High-level market segment (e.g., FinTech Scale-up, DTC Consumer Brand, AI Infra)",
  "intent_score": 85,
  "why_now": "Sentence 1 (Catalyst): State the exact recent funding, hiring spree, or metric found in the text. Sentence 2 (Opportunity): State the immediate strategic hook or problem your services solve for them right now.",
  "signal_tags": [
    {{
      "tag": "Series C Funding",
      "category": "funding",
      "color_theme": "indigo"
    }},
    {{
      "tag": "Fractional CMO Request",
      "category": "agency_intent",
      "color_theme": "rose"
    }}
  ],
  "signals": [
    {{
      "signal_type": "Exact keyword or topic matched",
      "verbatim_quote": "Exact word-for-word string copied directly from text",
      "source_url": "https://example.com/source-link",
      "event_date": "YYYY-MM-DD"
    }}
  ],
  "ai_verdict": "A concise 2-3 sentence summary detailing verified intent triggers and proposed outreach strategy."
}}
"""
```

---

## 4. Signal Tag Category Library & Theme Matrix (SVG Icon Specs)

The backend outputs `signal_tags` adhering to this color theme matrix for rendering frontend intent chips:

| Category Code | Category Name | Description / Triggers | UI Color Theme | Tailwind Class | Recommended Lucide SVG Icon |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `funding` | Financial & Funding | Venture rounds (Seed, Series A-C), debt, ARR milestones | **Indigo** | `bg-indigo-500/10 text-indigo-300 border-indigo-500/30` | `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>` (`DollarSign`) |
| `hiring` | Growth & Expansion | Leadership hiring, 10+ open job roles, new offices | **Emerald** | `bg-emerald-500/10 text-emerald-300 border-emerald-500/30` | `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="16" y1="11" x2="22" y2="11"/></svg>` (`UserPlus`) |
| `tech_stack` | Tooling & Infrastructure | Migration to Shopify, Klaviyo, HubSpot, GCP, Keap | **Amber** | `bg-amber-500/10 text-amber-300 border-amber-500/30` | `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>` (`Server`) |
| `leadership` | Executive Changes | New CMO, VP of Marketing, Head of Growth, CEO transition | **Purple** | `bg-purple-500/10 text-purple-300 border-purple-500/30` | `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>` (`Crown`) |
| `product_launch` | Product & Market Launch | Launch of new AI platforms, international expansion, PR | **Teal** | `bg-teal-500/10 text-teal-300 border-teal-500/30` | `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-3.05 11a22.35 22.35 0 0 1-3.95 2z"/></svg>` (`Rocket`) |
| `agency_intent` | Agency & RFP Intent | Actively searching for Fractional CMO, PPC agency, lead gen | **Rose** | `bg-rose-500/10 text-rose-300 border-rose-500/30` | `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>` (`Target`) |

---

## 5. Backend Pydantic & Supabase Database Migration Specs

To ensure that neither the React frontend nor **Supabase / PostgreSQL** throw missing field errors when querying or inserting `why_now`, `company_segment`, and `signal_tags`, strict fallbacks and SQL DDL migrations are defined below:

### Expanded Pydantic Model (`LeadDetailResponse` in `backend/schemas.py` & `backend/routers/leads.py`):

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class SignalTagModel(BaseModel):
    """Visual Intent Chip Object"""
    tag: str            # e.g., "Series C Funding", "Hiring Spike", "PPC Agency Intent"
    category: str       # "funding", "hiring", "tech_stack", "leadership", "product_launch", "agency_intent"
    color_theme: str    # "indigo", "emerald", "amber", "purple", "teal", "rose"

class LeadDetailResponse(BaseModel):
    id: str
    company_name: str
    domain: str
    industry: str = "B2B Software & Services"
    company_segment: Optional[str] = "Growth Scale-up"
    employee_count: Optional[int] = None
    funding_stage: Optional[str] = None
    intent_score: int = 50
    signal_freshness: int = 100
    tier: Literal["High", "Medium", "Low"] = "Medium"
    icp_fit: Literal["Strong", "Partial", "Poor"] = "Strong"
    confidence: ConfidenceModel
    
    # --- NON-BREAKING WHY NOW SUMMARY FALLBACK ---
    why_now: str = Field(
        default="Verified public buying intent triggers detected. Recommend targeted outreach.",
        description="2-sentence catalyst and strategic opportunity statement."
    )
    signal_tags: List[SignalTagModel] = Field(default_factory=list)
    
    badge: Optional[Literal["new_today", "score_up", "score_down", "signal_added", "filtered"]] = None
    social_segment: Optional[str] = None
    meta_ads_active: Optional[bool] = False
    meta_ads_count: Optional[int] = 0
    bio_url: Optional[str] = None
    signals: List[SignalModel] = Field(default_factory=list)
    ai_verdict: str = "Review signals for outreach context."
    dns_audit: DNSAuditModel
    contacts: List[ContactModel] = Field(default_factory=list)
    last_updated: str
```

### SQLAlchemy Model Extension (`backend/models.py`):
```python
class LeadSnapshot(Base):
    __tablename__ = "lead_snapshots"

    id = Column(String, primary_key=True, index=True)
    domain = Column(String, index=True, nullable=False)
    company_name = Column(String, nullable=True)
    company_segment = Column(String, nullable=True, default="Growth Scale-up")
    industry = Column(String, nullable=True)
    employee_count = Column(Integer, nullable=True)
    funding_stage = Column(String, nullable=True)
    intent_score = Column(Integer, nullable=False, default=0)
    signal_freshness = Column(Integer, nullable=True, default=100)
    tier = Column(String, nullable=True)
    icp_fit = Column(String, nullable=True)
    badge = Column(String, nullable=True)
    social_segment = Column(String, nullable=True)
    meta_ads_active = Column(Boolean, default=False)
    meta_ads_count = Column(Integer, default=0)
    bio_url = Column(String, nullable=True)
    why_now = Column(Text, nullable=True, default="Verified public buying intent triggers detected.")
    signal_tags = Column(JSON, nullable=True, default=list)
    ai_verdict = Column(Text, nullable=True)
    full_payload = Column(JSON, nullable=True)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

### Supabase / PostgreSQL DDL Migration SQL:
To update existing Supabase or PostgreSQL databases without dropping existing lead records:

```sql
-- Migration Script for Supabase / PostgreSQL
ALTER TABLE lead_snapshots 
ADD COLUMN IF NOT EXISTS why_now TEXT DEFAULT 'Verified public buying intent triggers detected.';

ALTER TABLE lead_snapshots 
ADD COLUMN IF NOT EXISTS company_segment VARCHAR(255) DEFAULT 'Growth Scale-up';

ALTER TABLE lead_snapshots 
ADD COLUMN IF NOT EXISTS signal_tags JSONB DEFAULT '[]'::jsonb;
```

---

## 6. Phase 7 Pipeline Architecture: DB Storage + Live Frontend Streaming

In **Phase 7 (Persistence & Delivery)**, the pipeline MUST accomplish dual objectives:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                   PHASE 7: PERSISTENCE & DELIVERABILITY                  │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                 ┌───────────────────┴───────────────────┐
                 │                                       │
  [1. Persistent DB Storage]              [2. Live Frontend Delivery]
  Saves `LeadSnapshot` record             Returns / broadcasts full lead payload
  to SQLite / Supabase DB                 to frontend's pipeline state.
  (`db.add(lead_snapshot)`)               - Direct HTTP Response on Ingest
  (`db.commit()`)                         - SSE / WebSockets on Batch Runs
```

### 1. Persistent DB Storage:
```python
db = SessionLocal()
try:
    lead_snap = LeadSnapshot(
        id=lead_id,
        domain=domain,
        company_name=company_name,
        company_segment=company_segment or "Growth Scale-up",
        industry=industry,
        employee_count=employee_count,
        intent_score=intent_score,
        tier=tier,
        icp_fit=icp_fit,
        why_now=why_now or "Verified public buying intent triggers detected.",
        signal_tags=signal_tags or [],
        ai_verdict=ai_verdict,
        full_payload=lead_payload,
        last_updated=datetime.now(timezone.utc)
    )
    db.merge(lead_snap)
    db.commit()
finally:
    db.close()
```

### 2. Live Frontend Pipeline Integration:
* **For `/api/leads/ingest` & `/api/pipeline/run`**:
  * Return the constructed `LeadDetailResponse` in the API endpoint response body:
    ```json
    {
      "status": "success",
      "lead": { ...full LeadDetailResponse... }
    }
    ```
* **Frontend State Ingestion**:
  * In the React frontend, append the returned lead directly to the pipeline state array (`setPipelineLeads(prev => [newLead, ...prev])`) so it renders immediately without requiring a full page refresh.

---

## 7. Summary of Current Frontend Adaptations

1. **Dedicated Pipeline State**:
   * Frontend maintains `pipelineLeads` for active pipeline runs alongside `allLeads` for historical database views.

2. **High-Density Card Components**:
   * Uses `why_now` for top-level lead summary cards.
   * Maps `signal_tags` into themed SVG intent chips (Indigo, Emerald, Amber, Purple, Teal, Rose).

3. **Contact & DNS Audit Widgets**:
   * Displays verified decision-maker contacts (`name`, `title`, `email`) and infrastructure health checks (SPF, DKIM, DMARC).

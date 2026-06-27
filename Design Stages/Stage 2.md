# Stage 2: The Filter Funnel & Guardrails (Implementation Guide)

[cite_start]This document details the configuration and deployment of Stage 2 of the platform, focusing on active cost management and data accuracy guardrails as specified in `Lead_Intelligence_Platform_Architecture.docx`[cite: 32, 33]. [cite_start]This stage implements the HTML token trimmer [cite: 35][cite_start], the programmatic keyword gating array [cite: 46][cite_start], and the fuzzy string validation module (Fix 1) [cite: 65] [cite_start]to systematically eliminate AI hallucinations and minimize API usage[cite: 33, 68].

---

## 📂 Targeted File Architecture (Stage 2 Extensions)

Your active workspace layout will expand to include the following modules:
```text
lead-gen-platform/
├── backend/
│   ├── requirements.txt           # Updated with parser & alignment utilities
│   ├── main.py                    # Routes updated to support filter simulation
│   ├── pipeline/
│   │   └── filter_funnel.py       # HTML reduction and keyword verification rules
│   └── validation/
│       └── quote_validator.py     # Levenshtein partial ratio alignment engine (Fix 1)
└── frontend/
    ├── app/
    │   └── page.tsx               # Updated to nest the active lead grid layout
    └── components/
        └── LeadTable.tsx          # Real-time state-driven data grid UI wrapper

```

---

## 🛠️ Backend Implementation

### 1. Dependency Extensions

Append these tracking libraries to your existing `backend/requirements.txt` file:

```text
beautifulsoup4==4.12.3
html2text==2024.2.26
rapidfuzz==3.9.3

```

### 2. `backend/pipeline/filter_funnel.py`

This module handles token minimization and high-speed string inspection. It reduces raw web payload size by 70–90% to protect the system from excessive LLM pricing fees.

```python
from bs4 import BeautifulSoup
import html2text

ANCHOR_KEYWORDS = [
    'funding', 'raised', 'series a', 'series b',
    'sdr', 'bdr', 'sales development', 'business development',
    'hiring', 'expand', 'growth', 'outbound', 'pipeline'
[cite_start]] [cite: 50, 51, 52]

def trim_html_for_llm(raw_html: str) -> str:
    """
    Strips raw code strings, stylesheets, script markers, and layout menus
    [cite_start]to optimize context structure before calling AI engines. (Stage 2) [cite: 35, 36, 37]
    """
    [cite_start]soup = BeautifulSoup(raw_html, 'html.parser') [cite: 41]
    
    # [cite_start]Prune non-content structural tags [cite: 42]
    [cite_start]for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']): [cite: 42]
        [cite_start]tag.decompose() [cite: 43]
        
    # [cite_start]Convert standard DOM syntax to clean markdown text format [cite: 44]
    [cite_start]text = html2text.html2text(str(soup)) [cite: 44]
    
    # [cite_start]Enforce strict ceiling limit to cap upstream context sizes [cite: 45]
    [cite_start]return text[:8000] [cite: 45]

def passes_keyword_gate(text: str) -> bool:
    """
    Executes a microsecond-level plain string match check. 
    [cite_start]Drops non-matching leads immediately at zero compute cost. [cite: 47, 48, 49]
    """
    [cite_start]lower = text.lower() [cite: 54]
    [cite_start]return any(kw in lower for kw in ANCHOR_KEYWORDS) [cite: 55]

def check_recent_cache(domain: str) -> bool:
    """
    Checks if the domain was enriched within the last 7 days.
    If cached, bypasses LLM parsing to save compute costs.
    """
    from backend.database import SessionLocal
    from sqlalchemy import text
    from datetime import datetime, timedelta, timezone

    db = SessionLocal()
    try:
        row = db.execute(
            text("SELECT last_updated FROM lead_snapshots WHERE domain=:d ORDER BY last_updated DESC LIMIT 1"),
            {"d": domain}
        ).fetchone()
        
        if row and row[0]:
            last_updated = datetime.fromisoformat(row[0].replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - last_updated < timedelta(days=7):
                return True
    except Exception:
        pass
    finally:
        db.close()
    return False

```

### 3. `backend/validation/quote_validator.py` (Fix 1)

Implements an algorithmic verification step to screen out AI hallucinations. It relies on partial Levenshtein ratio matching instead of rigid exact evaluations to prevent false negatives caused by minor punctuation or phrasing shifts.

```python
[cite_start]from rapidfuzz import fuzz [cite: 69]

def validate_quote(quote: str, source: str, threshold: float = 85.0) -> tuple[bool, float]:
    """
    Validates whether an extracted verbatim AI quote matches 
    [cite_start]the original raw source material. (Fix 1) [cite: 66, 67]
    
    Returns:
        [cite_start]tuple: (passes_validation_bool, calculated_similarity_score_float) [cite: 70]
    """
    if not quote or not source:
        return False, 0.0

    # [cite_start]Execute partial ratio similarity check across variant segments [cite: 67, 71]
    [cite_start]score = fuzz.partial_ratio(quote.lower(), source.lower()) [cite: 71]
    [cite_start]passes = score >= threshold [cite: 72]
    
    [cite_start]return passes, float(score) [cite: 72]

```

### 4. `backend/main.py` (Extended Tracking Routes)

Update your entrypoint file to provide functional inspection endpoints for testing the filter engines.

```python
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import engine, Base, get_db
from backend import models
from backend.pipeline.dns_audit import audit_domain_email_infrastructure
from backend.pipeline.filter_funnel import trim_html_for_llm, passes_keyword_gate
from backend.validation.quote_validator import validate_quote

# Retain DB initialization from Stage 1
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Heimdall Intel Platform API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class FilterRequest(BaseModel):
    raw_html: str

class ValidationPayload(BaseModel):
    quote: str
    source_text: str

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "stage": 2, "scheduler_status": "initialized_idle"}

# Retain route from Stage 1
@app.get("/api/audit/dns")
def execute_dns_audit(domain: str):
    """Direct programmatic debugging route for infrastructure audits."""
    return audit_domain_email_infrastructure(domain)

@app.post("/api/filter/simulate")
def simulate_filter_funnel(payload: FilterRequest):
    """Programmatic staging endpoint evaluating structural data reduction."""
    cleaned_text = trim_html_for_llm(payload.raw_html)
    matches_gate = passes_keyword_gate(cleaned_text)
    
    return {
        "character_count_before": len(payload.raw_html),
        "character_count_after": len(cleaned_text),
        "passes_keyword_gate": matches_gate,
        "sample_preview": cleaned_text[:300]
    }

@app.post("/api/validation/verify-quote")
def verify_extracted_quote(payload: ValidationPayload):
    """Validates the alignment of an extracted quote against the source material."""
    success, score = validate_quote(payload.quote, payload.source_text)
    return {
        "is_valid": success,
        "similarity_score": score,
        [cite_start]"action_taken": "Proceed" if success else "Discard Signal" [cite: 68]
    }

```

---

## 🎨 Frontend Implementation (Data Grid Layout)

### 1. `frontend/components/LeadTable.tsx`

This layout provides a clean, searchable interface grid for sales teams, prioritizing instant scannability over abstract layouts.

```tsx
'use client';

import React, { useState } from 'react';

[cite_start]// Hardcoded Stage 2 mock dataset matching systemic data contracts [cite: 13, 115]
const INITIAL_MOCK_LEADS = [
  { id: '1', name: 'Crework Labs', domain: 'creworklabs.com', industry: 'Software Development', score: 78, tier: 'High', why_now: 'Expanding global footprint; searching for immediate high-velocity SDR leadership.' },
  { id: '2', name: 'Acme Systems', domain: 'acmesystems.io', industry: 'SaaS', score: 92, tier: 'High', why_now: 'Closed $12M Series A funding round inside previous 14 days.' },
  { id: '3', name: 'Delta Cyber', domain: 'deltacyber.net', industry: 'Cybersecurity', score: 54, tier: 'Medium', why_now: 'Stale open sales postings detected across international job boards.' },
  { id: '4', name: 'Beta Logistics', domain: 'betalogistics.org', industry: 'Logistics Software', score: 28, tier: 'Low', why_now: 'Active technical tools footprint but missing fundamental root domain SPF configurations.' }
];

export default function LeadTable() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTier, setSelectedTier] = useState('ALL');

  [cite_start]// Interactive filtering rules [cite: 3]
  const filteredLeads = INITIAL_MOCK_LEADS.filter((lead) => {
    const matchesSearch = lead.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          lead.industry.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesTier = selectedTier === 'ALL' || lead.tier === selectedTier;
    return matchesSearch && matchesTier;
  });

  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden shadow-xl">
      [cite_start]{/* Search and Filtering Controls Section [cite: 3] */}
      <div className="p-5 border-b border-zinc-800 flex flex-col sm:flex-row justify-between items-center gap-4 bg-zinc-950">
        <input
          type="text"
          placeholder="Search target company or industry vertically..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full sm:w-80 px-4 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition-colors"
        />
        <div className="flex gap-2 w-full sm:w-auto justify-end">
          {['ALL', 'High', 'Medium', 'Low'].map((tier) => (
            <button
              key={tier}
              onClick={() => setSelectedTier(tier)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-all ${
                selectedTier === tier
                  ? 'bg-zinc-100 text-zinc-900 border-zinc-100'
                  : 'bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-zinc-200'
              }`}
            >
              {tier}
            </button>
          ))}
        </div>
      </div>

      [cite_start]{/* Main Core Data Table Frame [cite: 3] */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900/40 text-zinc-400 text-xs font-semibold tracking-wider uppercase">
              <th className="p-4">Company Name</th>
              <th className="p-4">Industry Sector</th>
              <th className="p-4 text-center">Intent Score</th>
              <th className="p-4">Intent Tier</th>
              <th className="p-4">Primary Trigger (Why Now)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800 text-sm text-zinc-300">
            {filteredLeads.length > 0 ? (
              filteredLeads.map((lead) => (
                <tr key={lead.id} className="hover:bg-zinc-900/30 transition-colors">
                  <td className="p-4 font-medium text-white">
                    <div className="flex flex-col">
                      <span>{lead.name}</span>
                      <span className="text-xs text-zinc-500 font-mono mt-0.5">{lead.domain}</span>
                    </div>
                  </td>
                  <td className="p-4 text-zinc-400">{lead.industry}</td>
                  <td className="p-4 text-center">
                    <span className="font-semibold px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 text-zinc-100 font-mono">
                      {lead.score}
                    </span>
                  </td>
                  <td className="p-4">
                    <span className={`px-2 py-0.5 rounded text-xs font-semibold uppercase tracking-wider ${
                      lead.tier === 'High' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                      lead.tier === 'Medium' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                      'bg-zinc-800 text-zinc-400 border border-zinc-700'
                    }`}>
                      {lead.tier}
                    </span>
                  </td>
                  <td className="p-4 text-zinc-400 max-w-sm truncate sm:max-w-md" title={lead.why_now}>
                    [cite_start]{lead.why_now} [cite: 177]
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5} className="p-12 text-center text-zinc-500 font-medium">
                  No tracking records found matching the active filter settings.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

```

### 2. `frontend/app/page.tsx`

Update your root viewport file to render the newly created table component underneath your executive performance layout metrics.

```tsx
import KPIRibbon from '@/components/KPIRibbon';
import LeadTable from '@/components/LeadTable';

export default function DashboardHome() {
  return (
    <main className="min-h-screen bg-zinc-900 text-zinc-100 p-8 space-y-8">
      {/* Top Header Layout Configuration */}
      <div className="flex flex-col gap-1 border-b border-zinc-800 pb-6">
        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          Heimdall Lead Intelligence Platform
          <span className="text-xs px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-zinc-400 font-mono">V1 POC (Stage 2)</span>
        </h1>
        <p className="text-sm text-zinc-400">
          Automated intent tracking and outbound threat scanning.
        </p>
      </div>

      {/* KPI Metric Summary Blocks */}
      <KPIRibbon />

      {/* Interactive Core Data Table */}
      <LeadTable />
    </main>
  );
}

```

---

## 🚦 System Verification Guidelines

Run these sanity checks to verify Stage 2 functionality:

1. **Test Token Trimming & Keyword Gating Engine:**
```bash
curl -X POST "[http://127.0.0.1:8000/api/filter/simulate](http://127.0.0.1:8000/api/filter/simulate)" \
     -H "Content-Type: application/json" \
     -d '{"raw_html": "<html><body><nav>Menu</nav><main>Our startup just raised a seed funding round to scale up outbound operations!</main></body></html>"}'

```


Confirm that the response shows the HTML tags have been stripped, the token count has dropped, and `passes_keyword_gate` returns `true`.


2. **Test Fuzzy Verification Mechanics (Fix 1):**
```bash
curl -X POST "[http://127.0.0.1:8000/api/validation/verify-quote](http://127.0.0.1:8000/api/validation/verify-quote)" \
     -H "Content-Type: application/json" \
     -d '{"quote": "raised $4 million", "source_text": "Company records show we raised $4M this quarter"}'

```


Verify that the similarity score clears the target threshold (85%), indicating a valid extraction.


3. **Verify UI Filtering Framework:**
Confirm that clicking the `High`, `Medium`, or `Low` filter buttons accurately shifts row visibility states without layout issues.

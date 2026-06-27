# Stage 3: Scoring Engine & ICP Constraints (Implementation Guide)

This document details the architecture and deployment of Stage 3 of the platform, tracking the specifications outlined in `Lead_Intelligence_Platform_Architecture.docx`. [cite_start]This stage orchestrates the hybrid intelligence layer, combining LLM semantic parsing with deterministic constraints: the Time-Decay Recency Formula (Fix 2) [cite: 82] [cite_start]and the ICP Score Caps filter engine (Fix 3)[cite: 92].

---

## 📂 Targeted File Architecture (Stage 3 Extensions)

Your active workspace layout will expand to include the following core decision modules:
```text
lead-gen-platform/
├── backend/
│   ├── requirements.txt           # Verified anthropic client bindings
│   ├── main.py                    # Multi-stage routing extensions
│   └── pipeline/
│       ├── scorer.py              # Core semantic scoring & Pydantic mapping
│       ├── time_decay.py          # Recency multi-tier formula implementation (Fix 2)
│       └── icp_filter.py          # Growth stage & scale constraint engine (Fix 3)
└── frontend/
    └── components/
        └── LeadTable.tsx          # Enhanced with visualization bars and chip indicators

```

---

## 🛠️ Backend Implementation

### 1. Dependency Extensions

Ensure your `backend/requirements.txt` environment contains the official Anthropic SDK client wrapper if making live external calls:

```text
anthropic==0.28.0

```

### 2. `backend/pipeline/time_decay.py` (Fix 2)

Implements mathematical degradation curves based on the chronological age of detected intent events. This ensures that dated historic actions do not artificially bloat real-time outbound queues.

```python
from datetime import datetime, timezone

RECENCY_TIERS = [
    (30,  1.00)[cite_start],   # < 30 days  -> Full weight contribution (100%) [cite: 86]
    (90,  0.70)[cite_start],   # 30-90 days -> 70% retention multiplier [cite: 87]
    (180, 0.40)[cite_start],   # 90-180 days -> 40% retention multiplier [cite: 88]
    (365, 0.20)[cite_start],   # 180-365 days -> 20% retention multiplier [cite: 89]
]
[cite_start]FALLBACK_MULTIPLIER = 0.10  # > 1 year -> 10% anchor floor [cite: 91]

def calculate_time_decay(event_date_str: str) -> tuple[float, str]:
    """
    [cite_start]Computes a recency factor and a string tracking indicator based on data age. (Fix 2) [cite: 82, 83]
    """
    if not event_date_str:
        return 0.50, "unknown"
    try:
        event_date = datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
    except ValueError:
        return 1.00, "current"
        
    delta_days = (datetime.now(timezone.utc) - event_date).days
    
    for max_days, multiplier in RECENCY_TIERS:
        if delta_days <= max_days:
            label = "current" if max_days <= 30 else f"{delta_days}d_stale"
            return multiplier, label
            
    return FALLBACK_MULTIPLIER, "historical"

```

### 3. `backend/pipeline/icp_filter.py` (Fix 3)

Applies non-linear target parameter checks to penalize or hard-cap leads that diverge from the service agency's sweet spot market profiles.

```python
from typing import Optional
from backend.config import settings

def apply_icp_filters(
    base_score: float, 
    employee_count: Optional[int], 
    funding_stage: Optional[str], 
    industry: str
) -> tuple[int, str]:
    """
    Evaluates firmographic vectors to calculate hard ceiling caps and 
    [cite_start]deduction scoring modifications. (Fix 3) [cite: 93]
    """
    score = base_score
    penalties = 0
    fit_label = "Strong"
    
    # [cite_start]1. Scale Constraints: Capacity Check [cite: 95]
    if employee_count is not None:
        if employee_count > 500:
            [cite_start]score = min(score, 35)  # Enterprise internal sales block cap [cite: 95]
            fit_label = "Poor"
        elif employee_count < 5:
            [cite_start]score = min(score, 35)  # Under-resourced/pre-revenue cash block cap [cite: 95]
            fit_label = "Poor"
            
    # [cite_start]2. Maturity Level Analysis [cite: 95]
    if funding_stage:
        stagnant_stages = ["Series D", "Series E", "Public", "M&A"]
        if any(funding_stage.lower() == stage.lower() for stage in stagnant_stages):
            [cite_start]score = min(score, 30)  # Locked internal operations block cap [cite: 95]
            fit_label = "Poor"

    # [cite_start]3. Industry Vertical Alignment [cite: 95]
    target_list = settings.ICP.TARGET_INDUSTRIES
    if not any(tgt.lower() in industry.lower() for tgt in target_list):
        [cite_start]score -= 10  # Out of sector mismatch deduction [cite: 95]
        if fit_label != "Poor":
            fit_label = "Partial"
            
    # Enforce standard scoring boundaries
    final_score = max(0, min(int(score), 100))
    return final_score, fit_label

```

### 4. `backend/pipeline/scorer.py`

Connects rule-based parameters with structured Claude prompt outputs to form the unified business logic block.

```python
import json
import anthropic
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from backend.pipeline.time_decay import calculate_time_decay
from backend.pipeline.icp_filter import apply_icp_filters
from backend.validation.quote_validator import validate_quote
from backend.config import settings

# [cite_start]Define unified Pydantic data interface structures [cite: 102]
class ExtractedSignal(BaseModel):
    [cite_start]signal_type: str [cite: 108]
    [cite_start]verbatim_quote: str [cite: 109]
    event_date: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ClaudeScoringPayload(BaseModel):
    [cite_start]company_name: str [cite: 104]
    [cite_start]intent_score: int [cite: 105]
    [cite_start]tier: str [cite: 106]
    [cite_start]signals: list[ExtractedSignal] [cite: 107]
    [cite_start]ai_verdict: str [cite: 111]

def process_hybrid_lead_scoring(raw_extracted_payload: dict, firmographics: dict, raw_source_text: str = "") -> dict:
    """
    Combines LLM data extractions with mathematical operational 
    [cite_start]adjustments and structural filter rules. [cite: 78, 79]
    """
    base_ai_score = raw_extracted_payload.get("intent_score", 50)
    running_score = 0.0
    signals_processed = []
    total_multipliers = 0.0

    # [cite_start]Calculate signal weights combined with individual time decays [cite: 79]
    for sig in raw_extracted_payload.get("signals", []):
        sig_type = sig.get("signal_type")
        
        # [cite_start]Mapping base architectural lookup evaluations [cite: 13, 81]
        base_weight = 20.0
        [cite_start]if sig_type == "funding_round": base_weight = 30.0 [cite: 81]
        [cite_start]elif sig_type == "sdr_hiring": base_weight = 25.0 [cite: 81]
        [cite_start]elif sig_type == "growth_news": base_weight = 15.0 [cite: 81]
        
        decay_mult, recency_label = calculate_time_decay(sig.get("event_date", ""))
        total_multipliers += decay_mult
        
        contribution = base_weight * decay_mult
        running_score += contribution
        
        sig["score_contribution"] = round(contribution, 1)
        sig["recency_label"] = recency_label
        
        is_valid, sim_score = validate_quote(sig.get("verbatim_quote", ""), raw_source_text)
        sig["quote_validated"] = is_valid
        if not is_valid:
            running_score -= 10
            
        signals_processed.append(sig)

    # Compute systemic baseline score
    aggregated_base = (base_ai_score * 0.4) + (running_score * 0.6)
    
    # [cite_start]Apply transactional structural filter modifiers (Fix 3) [cite: 79, 93]
    final_intent_score, icp_fit_label = apply_icp_filters(
        base_score=aggregated_base,
        employee_count=firmographics.get("employee_count"),
        funding_stage=firmographics.get("funding_stage"),
        industry=firmographics.get("industry", "Unknown")
    )
    
    # [cite_start]Enforce algorithmic score categorization bands [cite: 114, 115]
    [cite_start]if final_intent_score >= 70: assigned_tier = "High" [cite: 115]
    [cite_start]elif final_intent_score >= 40: assigned_tier = "Medium" [cite: 115]
    [cite_start]else: assigned_tier = "Low" [cite: 115]
    
    [cite_start]avg_freshness = int((total_multipliers / len(signals_processed) * 100)) if signals_processed else 100 [cite: 138]

    return {
        "company_name": raw_extracted_payload.get("company_name"),
        [cite_start]"intent_score": final_intent_score, [cite: 137]
        [cite_start]"signal_freshness": min(avg_freshness, 100), [cite: 138]
        [cite_start]"tier": assigned_tier, [cite: 139]
        [cite_start]"icp_fit": icp_fit_label, [cite: 140]
        [cite_start]"signals": signals_processed, [cite: 145]
        [cite_start]"ai_verdict": raw_extracted_payload.get("ai_verdict", "") [cite: 153]
    }

def analyze_lead_with_claude(company_name: str, cleaned_html: str, firmographics: dict) -> dict:
    """Calls Claude API to extract signals and then applies hybrid scoring."""
    client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)
    
    prompt = f"Analyze {company_name} from the following text:\n{cleaned_html}\nExtract intent signals as JSON with intent_score, signals list, and ai_verdict."
    
    try:
        message = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            temperature=0,
            system="You are an expert SDR extraction engine. Output raw JSON.",
            messages=[{"role": "user", "content": prompt}]
        )
        raw_payload = json.loads(message.content[0].text)
    except Exception:
        raw_payload = {"company_name": company_name, "intent_score": 50, "signals": [], "ai_verdict": "Error processing"}
        
    return process_hybrid_lead_scoring(raw_payload, firmographics, cleaned_html)

```

### 5. `backend/main.py` (Unified Integration Pipeline Endpoint)

```python
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from backend.database import engine, Base, get_db
from backend import models
from backend.pipeline.dns_audit import audit_domain_email_infrastructure
from backend.pipeline.filter_funnel import trim_html_for_llm, passes_keyword_gate
from backend.validation.quote_validator import validate_quote
from backend.pipeline.scorer import process_hybrid_lead_scoring

# Inherit existing configuration (Additive Stage)
Base.metadata.create_all(bind=engine)
app = FastAPI(title="Heimdall Intel Platform API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ... (Previous routes omitted for brevity in guide)

@app.get("/api/score/simulate")
def simulate_scoring_pipeline():
    """Simulates the lifecycle processing sequence from ingestion to score caps."""
    mock_llm_json = {
        "company_name": "Crework Labs",
        "intent_score": 85,
        "signals": [
            {"signal_type": "sdr_hiring", "verbatim_quote": "Looking for high-velocity SDR leadership", "event_date": "2026-06-15T12:00:00Z"},
            {"signal_type": "growth_news", "verbatim_quote": "expanding its global B2B footprint", "event_date": "2026-02-10T12:00:00Z"}
        ],
        "ai_verdict": "High conversion potential for outbound agency services."
    }
    
    mock_firmographics = {
        "employee_count": 45,
        "funding_stage": "Seed",
        "industry": "Software Development"
    }
    
    scored_payload = process_hybrid_lead_scoring(mock_llm_json, mock_firmographics)
    return scored_payload

```

---

## 🎨 Frontend Implementation (Enhanced Grid Layout)

### 1. `frontend/components/LeadTable.tsx`

Update the table component to cleanly render dual visual performance tracking indicators and specific ideal profile chips.

```tsx
'use client';

import React, { useState } from 'react';

const ENHANCED_MOCK_LEADS = [
  { id: '1', name: 'Crework Labs', domain: 'creworklabs.com', industry: 'Software Development', score: 78, freshness: 85, tier: 'High', icp_fit: 'Strong', why_now: 'Expanding global footprint; tracking high-velocity SDR leadership targets.' },
  { id: '2', name: 'Acme Systems', domain: 'acmesystems.io', industry: 'SaaS', score: 92, freshness: 100, tier: 'High', icp_fit: 'Strong', why_now: 'Closed $12M Series A funding round inside previous 14 days.' },
  { id: '3', name: 'MacroEnterprise', domain: 'macrocorp.com', industry: 'Logistics', score: 35, freshness: 70, tier: 'Low', icp_fit: 'Poor', why_now: 'Scale footprint > 500 employees. Internally managed operational loops active.' },
  { id: '4', name: 'Beta Logistics', domain: 'betalogistics.org', industry: 'Retail Tech', score: 48, freshness: 40, tier: 'Medium', icp_fit: 'Partial', why_now: 'Industry horizontal mismatch identified outside priority target vectors.' }
];

export default function LeadTable() {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTier, setSelectedTier] = useState('ALL');

  const filteredLeads = ENHANCED_MOCK_LEADS.filter((lead) => {
    const matchesSearch = lead.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          lead.industry.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesTier = selectedTier === 'ALL' || lead.tier === selectedTier;
    return matchesSearch && matchesTier;
  });

  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden shadow-xl">
      {/* Table Headers and Control Toggles */}
      <div className="p-5 border-b border-zinc-800 flex flex-col sm:flex-row justify-between items-center gap-4">
        <input
          type="text"
          placeholder="Filter down active targets via company or sector search..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full sm:w-80 px-4 py-2 bg-zinc-900 border border-zinc-800 rounded-lg text-sm text-zinc-100 focus:outline-none focus:border-indigo-500"
        />
        <div className="flex gap-2">
          {['ALL', 'High', 'Medium', 'Low'].map((tier) => (
            <button
              key={tier}
              onClick={() => setSelectedTier(tier)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg border ${
                selectedTier === tier ? 'bg-zinc-100 text-zinc-900' : 'bg-zinc-900 text-zinc-400 border-zinc-800'
              }`}
            >
              {tier}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900/40 text-zinc-400 text-xs font-semibold uppercase tracking-wider">
              <th className="p-4">Target Identity</th>
              <th className="p-4">ICP Status</th>
              <th className="p-4">Scoring Status (Intent vs Recency)</th>
              <th className="p-4">Tier Status</th>
              <th className="p-4">Core Context Trigger</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800 text-sm text-zinc-300">
            {filteredLeads.map((lead) => (
              <tr key={lead.id} className="hover:bg-zinc-900/30 transition-colors">
                <td className="p-4 font-medium text-white">
                  <div className="flex flex-col">
                    <span>{lead.name}</span>
                    <span className="text-xs text-zinc-500 font-mono mt-0.5">{lead.domain}</span>
                  </div>
                </td>
                <td className="p-4">
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    lead.icp_fit === 'Strong' ? 'bg-emerald-500/10 text-emerald-400' :
                    lead.icp_fit === 'Partial' ? 'bg-amber-500/10 text-amber-400' :
                    'bg-rose-500/10 text-rose-400'
                  }`}>
                    {lead.icp_fit} Fit
                  </span>
                </td>
                <td className="p-4 min-w-[180px]">
                  <div className="space-y-1.5">
                    {/* Intent Score Bar Tracking Visual */}
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-zinc-400 w-8">INT:</span>
                      <div className="w-24 bg-zinc-800 h-2 rounded-full overflow-hidden">
                        <div className="bg-indigo-500 h-full" style={{ width: `${lead.score}%` }}></div>
                      </div>
                      <span className="text-xs font-mono text-zinc-200 font-semibold">{lead.score}</span>
                    </div>
                    {/* Signal Freshness Retention Visual (Fix 2) */}
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-zinc-500 w-8">REC:</span>
                      <div className="w-24 bg-zinc-800 h-1.5 rounded-full overflow-hidden">
                        <div className="bg-teal-500 h-full" style={{ width: `${lead.freshness}%` }}></div>
                      </div>
                      <span className="text-xs font-mono text-zinc-400">{lead.freshness}%</span>
                    </div>
                  </div>
                </td>
                <td className="p-4">
                  <span className={`px-2 py-0.5 rounded text-xs font-semibold uppercase ${
                    lead.tier === 'High' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                    lead.tier === 'Medium' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                    'bg-zinc-800 text-zinc-400'
                  }`}>
                    {lead.tier}
                  </span>
                </td>
                <td className="p-4 text-zinc-400 max-w-xs truncate" title={lead.why_now}>
                  {lead.why_now}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

```

---

## 🚦 System Verification Guidelines

Run these diagnostic tests to verify Stage 3 accuracy:

1. **Test Multi-Layer Scoring Calculations & Scale Constraints:**
```bash
curl -X GET "[http://127.0.0.1:8000/api/score/simulate](http://127.0.0.1:8000/api/score/simulate)"

```


Confirm that the calculated response returns proper modifications: ensuring variables scale properly, decay factor labels compute without issues, and `icp_fit` states map accurately.
2. **Verify Dual Data Display Controls:**
Confirm that the frontend displays distinct tracking bars for Intent Strength (`INT`) and Recency Retention (`REC`), allowing sales teams to separate hot, timely leads from stale, historic events.

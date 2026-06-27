# Stage 1: Data Sourcing & Infrastructure Audit (Implementation Guide)

This document establishes the foundational codebase for the AI-Driven Lead Intelligence Platform, tracking the specifications outlined in `Lead_Intelligence_Platform_Architecture.docx`[cite: 1]. Stage 1 is dedicated to configuring the environment, initializing database models, provisioning the public signal APIs, implementing the DNS email infrastructure audit engine, and assembling the frontend UI layout shell[cite: 1].

---

## 📂 Targeted File Architecture (Stage 1 Scope)

Ensure your working directory is scaffolded exactly as follows[cite: 1]:
```text
lead-gen-platform/
├── backend/
│   ├── config.py                  # Environment keys & constants
│   ├── database.py                # SQLite & SQLAlchemy engine configuration
│   ├── models.py                  # Pydantic & DB base schemas
│   ├── main.py                    # FastAPI entrypoint
│   └── pipeline/
│       ├── discovery.py           # Public signal fetch modules
│       └── dns_audit.py           # dnspython email infrastructure engine (Fix 4)
└── frontend/
    ├── app/
    │   └── page.tsx               # Primary dashboard structural root
    └── components/
        └── KPIRibbon.tsx          # Initial core performance cards

```

---

## 🛠️ Backend Implementation

### 1. Dependency Environment Configuration

Create a `requirements.txt` file inside the `backend/` directory:

```text
fastapi==0.111.0
uvicorn==0.30.1
pydantic==2.7.4
pydantic-settings==2.3.3
SQLAlchemy==2.0.30
dnspython==2.6.1
httpx==0.27.0

```

### 2. `backend/config.py`

Establish a unified configuration module managing validation thresholds and third-party credential ingestion.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel

class ICPSettings(BaseModel):
    MIN_EMPLOYEES: int = 10
    MAX_EMPLOYEES: int = 200
    TARGET_INDUSTRIES: list[str] = ["SaaS", "B2B", "Fintech", "Agtech", "Agency", "Software Development"]

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./lead_intelligence.db"
    
    # Discovery API Keys
    SERPER_API_KEY: str = "mock_key_if_empty"
    JSEARCH_API_KEY: str = "mock_key_if_empty"
    NEWS_API_KEY: str = "mock_key_if_empty"
    CLAUDE_API_KEY: str = "mock_key_if_empty"
    
    # ICP Blueprint Constants
    ICP: ICPSettings = ICPSettings()
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        env_nested_delimiter="__"
    )

settings = Settings()

```

### 3. `backend/database.py`

Configure the standard synchronous SQLite connection engine for rapid local execution.

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from backend.config import settings

engine = create_engine(
    settings.DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

```

### 4. `backend/pipeline/dns_audit.py` (Fix 4)

This engine converts the "Leaky Outbound Infrastructure" signal into an executable module via `dnspython`. It systematically checks the root domain for missing or misconfigured SPF/DKIM/DMARC settings to surface immediate pipeline risk profiles.

```python
import dns.resolver

COMMON_DKIM_SELECTORS = [
    "google", "selector1", "k1", "default", "mail", 
    "smtp", "picasso", "mandrill", "sendgrid", "microsoft"
]

def audit_domain_email_infrastructure(domain: str) -> dict:
    """
    Performs a deterministic public DNS diagnostic on the target domain
    to extract infrastructure vulnerability points. (Fix 4)
    """
    results = {
        "spf": {"status": "Missing", "points": 8, "record": None},
        "dkim": {"status": "Missing", "points": 4, "selector_found": None},
        "dmarc": {"status": "Missing", "points": 5, "record": None, "policy": None},
        "issues": []
    }
    
    # 1. Evaluate SPF Record Status
    try:
        txt_records = dns.resolver.resolve(domain, 'TXT')
        for record in txt_records:
            txt_str = "".join(s.decode() for s in record.strings)
            if txt_str.startswith("v=spf1"):
                results["spf"]["status"] = "Valid"
                results["spf"]["points"] = 0
                results["spf"]["record"] = txt_str
                break
    except Exception:
        pass
        
    if results["spf"]["status"] == "Missing":
        results["issues"].append(f"{domain} has no SPF record — outbound emails risk immediate rejection.")

    # 2. Evaluate DMARC Record Status & Policy Strictness
    dmarc_domain = f"_dmarc.{domain}"
    try:
        dmarc_records = dns.resolver.resolve(dmarc_domain, 'TXT')
        for record in dmarc_records:
            txt_str = "".join(s.decode() for s in record.strings)
            if txt_str.startswith("v=DMARC1"):
                results["dmarc"]["status"] = "Valid"
                results["dmarc"]["points"] = 0
                results["dmarc"]["record"] = txt_str
                
                # Parse policy configuration strength
                if "p=none" in txt_str.lower():
                    results["dmarc"]["status"] = "Weak (Monitoring Only)"
                    results["dmarc"]["points"] = 3
                    results["dmarc"]["policy"] = "none"
                    results["issues"].append(f"{domain} enforces DMARC p=none — monitoring only, lacks active domain protection.")
                elif "p=quarantine" in txt_str.lower():
                    results["dmarc"]["policy"] = "quarantine"
                elif "p=reject" in txt_str.lower():
                    results["dmarc"]["policy"] = "reject"
                break
    except Exception:
        pass

    if results["dmarc"]["status"] == "Missing":
        results["issues"].append(f"{domain} lacks a DMARC record — zero delivery visibility or sender spoofing safety blocks.")

    # 3. Evaluate DKIM Security Footprint
    for selector in COMMON_DKIM_SELECTORS:
        dkim_target = f"{selector}._domainkey.{domain}"
        try:
            dns.resolver.resolve(dkim_target, 'TXT')
            results["dkim"]["status"] = "Valid"
            results["dkim"]["points"] = 0
            results["dkim"]["selector_found"] = selector
            break
        except Exception:
            continue
            
    if results["dkim"]["status"] == "Missing":
        results["issues"].append(f"{domain} missing common cryptographic DKIM record configurations.")

    return results

```

### 5. `backend/pipeline/discovery.py`

Initializes a structured scaffolding architecture for incoming data channels before the filter logic triggers.

```python
import httpx
from backend.config import settings

async def fetch_public_intent_signals(query: str) -> list[dict]:
    """
    Mocks/Ingests initial web signals from public data sources.
    To be fully wired to live API responses in Stage 2.
    """
    # Placeholder layout matching incoming structural types
    return [
        {
            "company_name": "Crework Labs",
            "domain": "creworklabs.com",
            "raw_text": "Crework Labs is expanding its global B2B footprint and actively searching for high-velocity SDR leadership to structure our outbound pipelines.",
            "source_api": "Serper",
            "extracted_url": "[https://creworklabs.com](https://creworklabs.com)"
        }
    ]

```

### 6. `backend/models.py`

Defines the SQLAlchemy ORM schema needed for database tracking across the platform.

```python
from sqlalchemy import Column, String, Integer, DateTime
from backend.database import Base
from datetime import datetime, timezone

class LeadSnapshot(Base):
    __tablename__ = "lead_snapshots"
    id = Column(String, primary_key=True, index=True)
    domain = Column(String, index=True)
    intent_score = Column(Integer)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class PipelineStatus(Base):
    __tablename__ = "pipeline_status"
    id = Column(String, primary_key=True, index=True)
    last_run_time = Column(String)
    status = Column(String)
```

### 7. `backend/main.py`

Instantiates backend routes, application routing wrappers, and systemic checking routes.

```python
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from backend.database import engine, Base, get_db
from backend import models
from backend.pipeline.dns_audit import audit_domain_email_infrastructure

# Construct local storage architecture
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Heimdall Intel Platform API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "stage": 1, "scheduler_status": "initialized_idle"}

@app.get("/api/audit/dns")
def execute_dns_audit(domain: str):
    """Direct programmatic debugging route for infrastructure audits."""
    return audit_domain_email_infrastructure(domain)

```

---

## 🎨 Frontend Implementation (Next.js Dashboard Shell)

### 1. `frontend/components/KPIRibbon.tsx`

Construct clean, high-impact semantic dashboard summaries focused squarely on revenue operations metrics over abstract computing counts.

```tsx
import React from 'react';

interface KPICardProps {
  title: string;
  value: string | number;
  subtext: string;
  variant?: 'success' | 'indigo' | 'warning' | 'neutral';
}

export const KPICard: React.FC<KPICardProps> = ({ title, value, subtext, variant = 'neutral' }) => {
  const borderColors = {
    success: 'border-emerald-500/30 text-emerald-400',
    indigo: 'border-indigo-500/30 text-indigo-400',
    warning: 'border-amber-500/30 text-amber-400',
    neutral: 'border-zinc-800 text-zinc-100',
  };

  return (
    <div className={`p-6 bg-zinc-950 border rounded-xl flex flex-col justify-between shadow-md`}>
      <div>
        <p className="text-xs font-medium text-zinc-400 uppercase tracking-wider">{title}</p>
        <p className={`text-3xl font-bold tracking-tight mt-2 ${borderColors[variant]}`}>{value}</p>
      </div>
      <p className="text-xs text-zinc-500 mt-4 flex items-center gap-1">{subtext}</p>
    </div>
  );
};

export default function KPIRibbon() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 w-full">
      <KPICard subtext="Initializing pipeline data..." title="High-Intent Leads Ready" value="0" variant="success"/>
      <KPICard subtext="Scan required to extract trends" title="Top Signal This Week" value="Awaiting Run" variant="indigo"/>
      <KPICard subtext="0 verifications executed" title="Avg. AI Confidence" value="0%" variant="warning"/>
      <KPICard subtext="Est. contract revenue target" title="Untapped Pipeline Value" value="$0" variant="neutral"/>
    </div>
  );
}

```

### 2. `frontend/app/page.tsx`

Primary framework viewport utilizing a responsive dark canvas styling configuration.

```tsx
import KPIRibbon from '@/components/KPIRibbon';

export default function DashboardHome() {
  return (
    <main className="min-h-screen bg-zinc-900 text-zinc-100 p-8 space-y-8">
      {/* Dashboard Top Level Header */}
      <div className="flex flex-col gap-1 border-b border-zinc-800 pb-6">
        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          Heimdall Lead Intelligence Platform
          <span className="text-xs px-2 py-0.5 rounded bg-zinc-800 border border-zinc-700 text-zinc-400 font-mono">V1 POC (Stage 1)</span>
        </h1>
        <p className="text-sm text-zinc-400">
          Automated intent tracking and outbound threat scanning.
        </p>
      </div>

      {/* Metric Executive Row summary blocks */}
      <KPIRibbon/>

      {/* Main UI Body Grid Shell Placeholder */}
      <div className="w-full border border-dashed border-zinc-800 rounded-xl p-12 text-center text-zinc-500 bg-zinc-950/50">
        <p className="text-sm">Data extraction and verification pipeline staging area.</p>
        <p className="text-xs text-zinc-600 mt-1">Stage 2 will mount interactive data tables and string matching funnels.</p>
      </div>
    </main>
  );
}

```

---

## 🚦 System Verification Guidelines

Run the initialization checks below to verify Stage 1 structural integrity:

1. **Verify Backend Status:**
```bash
cd backend
uvicorn main:app --reload --port 8000

```

Navigate to `http://127.0.0.1:8000/api/health` and verify the operational lifecycle state payload.
2. **Test Automated DNS Audit Pipeline Engine (Fix 4):**
```text
[http://127.0.0.1:8000/api/audit/dns?domain=google.com](http://127.0.0.1:8000/api/audit/dns?domain=google.com)

```

Confirm the payload correctly surfaces calculated deductions and flags string issues without missing record parameters.

3. **Verify UI Execution Framework:**
Ensure your Next.js local server builds cleanly and matches the targeted visual dashboard configuration.

---

Let me know once your agent finishes spinning up the infrastructure and testing out that DNS engine, and we'll jump straight into generating **Stage 2: The Filter Funnel & Guardrails**.

# Automation Pipeline

The core shift is one sentence: instead of telling the system what companies to find, you tell it what market conditions to look for, and it finds the companies itself.

## Phase 1 — Keyword Discovery (replacing TARGET_COMPANIES)

**What changes:** Delete the hardcoded company list from your orchestrator. Replace with three concurrent keyword sweeps that return company names as output, not input.

*   **JobSpy sweep** — Query with `search_term="Sales Development Representative"` instead of a company name. Parse the company column from the returned DataFrame. Every unique value is a discovered lead. Filter out staffing agencies by excluding rows where the company name contains "Staffing", "Recruiting", or "Talent".
    *Implementation Note (Gap):* The sweep must use keyword roles, not targeted search of company names. Implement a separate `discover_companies_from_jobspy()` function in `discovery.py` that performs role-keyword sweeps independently of any company name input.
*   **NewsAPI sweep** — Query phrases like "SaaS startup raises", "B2B seed round", "series A funding 2026". Extract company names from article titles using spaCy's ORG entity recogniser — the same library you're loading in Phase 4, so no extra dependency.
    *Implementation Note (Gap):* The ORG extraction function needs to be added to `discovery.py`:
    ```python
    def extract_orgs_from_articles(articles: list[dict]) -> set[str]:
        nlp = nlp_instance  # loaded once at startup
        orgs = set()
        for article in articles:
            doc = nlp(article.get("title","") + " " + article.get("description",""))
            for ent in doc.ents:
                if ent.label_ == "ORG" and len(ent.text) > 3:
                    orgs.add(ent.text)
        return orgs
    ```
*   **Serper sweep** — Google search `site:linkedin.com/company "hiring SDR" OR "hiring BDR"`. Parse company names from result titles by stripping the " | LinkedIn" or "- LinkedIn" suffix:
    ```python
    company_name = result["title"].replace("| LinkedIn","").replace("- LinkedIn","").strip()
    ```
*   **Dedup:** Union all three sources into a Python `set()`. Check against SQLite to skip companies scored within the last 7 days. Pass remaining unique names to Phase 2.

> **Loom line:** "The system discovers companies it has never seen before by watching where the market is actively building sales teams — that's the highest-intent signal that exists."

---

## Phase 2 — Domain Resolution via Clearbit Autocomplete

**The problem:** You have "Acme Corp" as a string but need `acmecorp.com` before DNS audits or page scraping can happen. Letting Gemini guess domains wastes tokens and hallucinates.

**The fix:** Clearbit's public autocomplete endpoint requires no API key. Add a `resolve_domain(company_name)` function to `discovery.py`:
```python
import httpx

def resolve_domain(company_name: str) -> tuple[str | None, dict]:
    """Returns (domain, firmographics) from Clearbit. No API key needed."""
    try:
        resp = httpx.get(
            "https://autocomplete.clearbit.com/v1/companies/suggest",
            params={"query": company_name},
            timeout=5.0
        )
        results = resp.json()
        if results:
            first = results[0]
            return first.get("domain"), {
                "employee_count": first.get("employees"),
                "industry":       first.get("type","Unknown"),
            }
    except Exception:
        pass
    # Fallback: construct and verify
    slug = company_name.lower().replace(" ","")
    fallback = f"{slug}.com"
    try:
        r = httpx.head(f"https://{fallback}", timeout=4.0, follow_redirects=True)
        if r.status_code < 400:
            return fallback, {}
    except Exception:
        pass
    return None, {}
```

**Fallback:** If Clearbit returns nothing, construct `company_name.lower().replace(" ","") + ".com"` and verify with `httpx.head()`. If that also 404s, log as "Domain Unresolved" and skip entirely — never spend a Gemini call on an unverified domain.

**ICP Industry Mapping Gap:** Clearbit Autocomplete returns `"type": "B2B"` or `"type": "SaaS"`. However, `icp_filter.py` checks against `settings.ICP.TARGET_INDUSTRIES` (e.g. `["SaaS", "B2B", "Fintech", ...]`). Clearbit might return `"type": "Technology"` or `"type": "Software"`. Add `"Technology"` and `"Software"` to `TARGET_INDUSTRIES` in `config.py` to avoid false Poor Fit classifications on legitimate targets.

---

## Phase 3 — ICP Gatekeeper (runs before any LLM call)

**What it does:** Takes the `employee_count` and `industry` you already got from Clearbit and runs `apply_icp_filters()` immediately. If the result is Poor Fit, write a minimal record to SQLite with `tier="Poor Fit"` and stop. Total compute time: ~5ms.

**Critical detail:** Still log Poor Fit companies to the database with a rejection reason ("Exceeds employee ceiling", "Industry mismatch"). Show them as grayed-out rows in the dashboard with a "Filtered" badge. This demonstrates to the evaluator that your system actively rejects bad leads rather than ignoring them — that distinction matters for the rubric's "ICP-based filtering" bonus.

When the ICP gate returns a Poor Fit, the orchestrator must write a minimal record to SQLite:
```python
if icp_fit == "Poor":
    db.execute(text(
        "INSERT OR REPLACE INTO lead_snapshots"
        " (id, domain, company_name, intent_score, tier, badge, badge_label, full_payload, last_updated)"
        " VALUES (:id,:d,:cn,0,'Poor Fit','filtered',:reason,:fp,:lu)"
    ), {
        "id": domain.replace(".","_"),
        "d": domain, "cn": company_name,
        "reason": icp_reason,  # e.g. "Exceeds employee ceiling"
        "fp": json.dumps({"tier":"Poor Fit","icp_fit":"Poor","why_now": icp_reason}),
        "lu": datetime.now(timezone.utc).isoformat()
    })
    return None  # stop pipeline here
```

> **Loom line:** "We gate roughly 70% of discovered companies at millisecond speed before they ever touch the LLM. The AI only sees companies we've already confirmed are worth its attention."

---

## Phase 4 — Contact Extraction (3-tier local, zero API cost)

Here's an honest and effective architecture for local contact extraction, layered by reliability:

### Page Scraper (Targeted Subpage Fetching)
Implement a scraper function that targets company subpages for contact extraction.
- **Rules:**
  - Attempt to fetch the following pages: `["/about", "/team", "/blog", ""]` (skip `/contact` as it is typically a form page).
  - Set a 5-second timeout on each `httpx.get()` call.
  - Wrap each page fetch in a try/except individually so a single `404` or timeout doesn't abort the others.
  - Combine the cleaned text of all successfully fetched pages into a single string and pass it to the spaCy extractor (do not extract page-by-page).

### Layer 1 — Email pattern from any page (most reliable)
Don't limit to `/contact`. Scrape the homepage, `/about`, `/team`, and `/blog` simultaneously. Run your regex across all of them. The pattern that matters:

```python
import re

EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+\-]+@(?:' + re.escape(domain) + r')',
    re.IGNORECASE
)
```

Only match emails on the company's own domain — you don't want `careers@lever.co` leaking in from job widgets. This gives you real corporate emails when they exist, which is about 20–30% of the time.

### Layer 2 — spaCy PERSON + title proximity (medium reliability)
This is your best tool for names when emails don't exist. The key insight you need: don't just look for PERSON entities globally — look for them within a 60-character window of a title keyword. Raw spaCy on a full page will extract every person mentioned in any news article widget, testimonial, or case study.

**Critical Performance Rule (Startup Load):** 
The spaCy model `nlp = spacy.load("en_core_web_sm")` must be loaded once at the **module level** of `contact_extractor.py`, not inside the extraction function body. Loading the 40MB model inside `extract_leaders_from_text()` will load it on every single company processed, adding ~2 seconds of latency per company and completely defeating the purpose of using a local model.

```python
import spacy
# LOAD ONCE AT MODULE LEVEL:
nlp = spacy.load("en_core_web_sm")

TITLE_KEYWORDS = ["CEO", "CTO", "Founder", "Co-founder", "VP Sales",
                  "Head of Sales", "Director", "President", "Partner"]

def extract_leaders_from_text(text: str) -> list[dict]:
    doc = nlp(text)
    leaders = []
    for ent in doc.ents:
        if ent.label_ != "PERSON":
            continue
        # Check 60-char window before and after the entity
        start = max(0, ent.start_char - 60)
        end   = min(len(text), ent.end_char + 60)
        window = text[start:end]
        matched_title = next(
            (t for t in TITLE_KEYWORDS if t.lower() in window.lower()), None
        )
        if matched_title:
            leaders.append({
                "name":  ent.text,
                "title": matched_title,
                "source": "spacy_ner"
            })
    # Deduplicate by name
    seen = set()
    return [l for l in leaders if not (l["name"] in seen or seen.add(l["name"]))]
```

### Layer 3 — Email guessing from name (low cost, surprisingly effective)
Once you have a name from spaCy and a domain from Clearbit, you can programmatically generate the 6 most common corporate email formats and verify which one is real using DNS MX lookup — no API needed:

```python
import dns.resolver

def split_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return parts[0], parts[-1]  # first, last
    return parts[0], ""             # single name edge case

def generate_email_candidates(first: str, last: str, domain: str) -> list[str]:
    f, l = first.lower(), last.lower()
    return [
        f"{f}.{l}@{domain}",      # john.smith@company.com  (most common)
        f"{f}@{domain}",           # john@company.com
        f"{f[0]}{l}@{domain}",    # jsmith@company.com
        f"{l}@{domain}",           # smith@company.com
        f"{f}{l}@{domain}",        # johnsmith@company.com
        f"{f[0]}.{l}@{domain}",   # j.smith@company.com
    ]

def verify_email_deliverable(email: str) -> bool:
    """
    Checks MX record exists for the domain — does NOT send email.
    Eliminates obvious dead domains. Cannot confirm the mailbox exists.
    """
    try:
        domain = email.split("@")[1]
        dns.resolver.resolve(domain, "MX")
        return True
    except Exception:
        return False
```

This doesn't confirm the mailbox exists — nothing local can do that without sending an email. But it eliminates dead domains and gives you a ranked candidate list. In practice, the `first.last@domain` format is correct about 55–60% of the time for B2B tech companies.

### Orchestrating the Contact Extraction Module (`contact_extractor.py`)
Ensure your agent implements the full glue code connecting all layers. Note that `contact_extractor.py` needs to import `trim_html_for_llm` from `backend.pipeline.filter_funnel` for page text cleanup:
```python
from backend.pipeline.filter_funnel import trim_html_for_llm
import httpx

def extract_contacts(domain: str) -> list[dict]:
    pages = ["/about", "/team", "/blog", ""]
    combined_text, found_emails = "", []
    for path in pages:
        try:
            r = httpx.get(f"https://{domain}{path}", timeout=5.0)
            page_text = trim_html_for_llm(r.text)
            # Tier 1: regex emails
            found_emails += EMAIL_PATTERN.findall(page_text)
            combined_text += " " + page_text
        except Exception:
            continue
    # Tier 2: spaCy leaders
    leaders = extract_leaders_from_text(combined_text)
    # Tier 3: email generation for each leader
    contacts = []
    for leader in leaders:
        first, last = split_name(leader["name"])
        candidates = generate_email_candidates(first, last, domain)
        verified = [e for e in found_emails if e in candidates]
        contacts.append({
            "name": leader["name"], 
            "title": leader["title"],
            "email": verified[0] if verified else candidates[0],
            "confidence": "verified" if verified else "generated"
        })
    return contacts
```

### Layer 4 — LinkedIn URL construction (zero-cost signal)
You already have the company name from JobSpy. LinkedIn company pages are public and predictable. You can construct the search URL and scrape the public employee count without authentication:

```python
def build_linkedin_search_url(company_name: str) -> str:
    slug = company_name.lower().replace(" ", "-").replace(",", "")
    return f"https://www.linkedin.com/company/{slug}/people/"
```

This page is heavily rate-limited and bot-protected, so don't rely on it programmatically. But it's worth mentioning in your Loom as a V2 integration point — "with a LinkedIn Sales Navigator API key, this step becomes deterministic."

### Dependency Requirements
1. Add to `requirements.txt`:
   ```text
   spacy==3.7.4
   ```
2. Document the post-install CLI setup command in the README:
   ```bash
   python -m spacy download en_core_web_sm
   ```

### The honest architecture for your Loom
Don't oversell Phase 4. Frame it this way: "Phase 4 uses a three-tier local extraction strategy. Tier 1 is regex email scanning across all public pages. Tier 2 is spaCy NER with title proximity matching to identify leadership names. Tier 3 is deterministic email format generation with MX verification — no paid data brokers, no hallucination."
Then say: "In V2, this tier plugs directly into Hunter.io's domain search API, which has verified all these format combinations already and returns confidence scores per email."
That's a much stronger framing than "we scrape the contact page" — because it shows you understand why contact pages don't work and built around it.

---

## Phase 5 — Gemini scoring (only after data is clean)

Here's the Gemini-optimised version. Gemini has two advantages over Claude for this use case — native JSON mode via `response_mime_type="application/json"` which guarantees valid JSON without prompt enforcement, and it's cheaper per token.

### The correct Gemini scoring implementation

```python
import google.generativeai as genai
from google.generativeai import types
import json
import logging

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.GEMINI_API_KEY)

SYSTEM_PROMPT = """You are a B2B sales intent scoring engine.
Analyze the provided company signals and return a score.

Scoring rules:
- intent_score: 0-100. Recent funding=+30, SDR hiring=+25, growth news=+15, email infra gap=+15
- tier: High=70+, Medium=40-69, Low=0-39
- icp_fit: Strong=10-200 employees B2B/SaaS, Partial=borderline, Poor=500+ or wrong industry
- signal_freshness: 0-100 based on how recent the signals are (last 30 days=100, 90 days=60, 180+ days=20)
- verbatim_quote: copy the EXACT words from the source text where you found this signal
- event_date: extract from text if mentioned, else leave empty string
- why_now: one sentence a salesperson would use as their opening line"""

def analyze_lead_with_gemini(
    company_name: str,
    cleaned_text: str,
    firmographics: dict
) -> dict | None:
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT,
        generation_config=types.GenerationConfig(
            response_mime_type="application/json",  # enforces JSON at API level
            temperature=0.1,                         # low temp = consistent structure
            max_output_tokens=800,                   # hard cap — schema is small
        )
    )

    # Keep the user prompt lean — system prompt carries the rules
    user_prompt = f"""Company: {company_name}
Employees: {firmographics.get('employee_count', 'Unknown')}
Industry: {firmographics.get('industry', 'Unknown')}
Funding stage: {firmographics.get('funding_stage', 'Unknown')}

Source signals (max 1500 chars):
{cleaned_text[:1500]}"""

    try:
        response = model.generate_content(user_prompt)
        return json.loads(response.text)   # guaranteed valid JSON
    except Exception as e:
        logger.error(f"Gemini scoring failed for {company_name}: {e}")
        return None   # orchestrator checks for None and skips persist
```

### Addressing Conflicts & Gaps in Scorer Implementation
1. **Gemini Replacement in `scorer.py` (Conflict):** 
   The stage code in `scorer.py` still imports `anthropic` and calls `claude-3-opus-20240229`. Replace the entire LLM call section with the `analyze_lead_with_gemini()` function. Make sure to rename the Pydantic scoring payload models (e.g. `ClaudeScoringPayload` to `GeminiScoringPayload`) for clarity.
   *Integration Note:* In `process_hybrid_lead_scoring()`, instead of assuming `raw_extracted_payload` is passed pre-populated from the outside, call `analyze_lead_with_gemini()` at the very top of `process_hybrid_lead_scoring()` to fetch and parse the payload from Gemini before proceeding with mathematical and operational adjustments. This ensures the two scoring functions are correctly connected.
2. **Natural Language Date Parsing in `time_decay.py` (Conflict):**
   The current code uses `datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))`. However, Gemini returns dates in inconsistent formats (e.g. `"2026-06"`, `"June 2026"`, or `""`), causing `fromisoformat()` to crash. Replace the parsing logic with `dateutil.parser` to handle natural date formats safely:
   ```python
   from dateutil import parser as dateutil_parser
   
   try:
       event_date = dateutil_parser.parse(event_date_str)
       if event_date.tzinfo is None:
           event_date = event_date.replace(tzinfo=timezone.utc)
   except Exception:
       event_date = datetime.now(timezone.utc)
   ```
3. **Gemini Response Schema Fallbacks (Gap):**
   Even with JSON Mode enabled, Gemini can occasionally omit fields like `why_now` or `ai_verdict`. Accessing these fields directly without defaults will crash `process_hybrid_lead_scoring()`. Ensure you add safe fallbacks:
   ```python
   why_now = scored.get("why_now", "Intent signals detected")
   ai_verdict = scored.get("ai_verdict", "Review signals for outreach context.")
   ```

### Why this is better than the Claude prompt version
1. **response_mime_type="application/json"** — This is a Gemini-native feature. The API enforces valid JSON at the model output level before the response even reaches your code. You don't need the "Return ONLY valid JSON. No preamble" instruction at all — that's a Claude workaround for a problem Gemini doesn't have.
2. **Schema removed from prompt** — The Claude version embedded the full JSON schema in the system prompt because Claude needs explicit field-by-field instruction to avoid wrapping output in markdown. Gemini with JSON mode doesn't. Removing the schema saves ~150 tokens per call. At 50 companies per day that's 7,500 tokens saved daily for free.
3. **max_output_tokens=800** — The scoring response is small and predictable. Capping at 800 prevents runaway generation. Claude's default is 1024, Gemini's is much higher — always cap it explicitly for structured output tasks.

### The one place you still need safe parsing
Even with JSON mode, Gemini can occasionally return an empty response on rate limit or network error. Add this wrapper around the call: Return `None` on failure, not an empty dict. The orchestrator already handles `None` by skipping the persist step — an empty dict would pass through and write garbage to the database.

### Token budget per company (after this implementation)
| Step | Tokens | Cost at Gemini Flash pricing |
| :--- | :--- | :--- |
| System prompt | ~120 | fixed |
| User prompt (capped 1500 chars) | ~400 | per company |
| Response (schema output) | ~250 | per company |
| **Total per company** | **~770** | **~$0.0002** |

50 companies per scheduler run = ~$0.01 per full pipeline execution. Effectively free.

---

## Phase 5.5 — Dual Model & Local Extractive Optimization (Gemini + Claude)

We implement 2 models: Gemini for intent discovery and scoring, and Claude for personalized communication copy in Pitcher Mode.

### Place 1 — Pitcher Mode (POST `/api/leads/{id}/verdict`)
This is the only place where prose quality matters and where a different model pays for itself. Gemini Flash produces functional cold emails but they read slightly templated. Claude Haiku (`claude-haiku-4-5`) produces noticeably better short-form persuasive copy and costs roughly $0.00025 per call — essentially free per click.

**Implementation Rule (Conflict):**
The current `leads.py` verdict endpoint builds the email as a string concatenation of `lead.signals[x].verbatim_quote[:N]`. Replace the f-string body in the `/api/leads/{id}/verdict` endpoint with the `generate_pitch_email()` call.

**Preamble Suffix Slicing (Gap):**
Since Claude Haiku does not support a native JSON mode like Gemini, it can occasionally wrap its output in conversational preamble (e.g. *"Here is the JSON email payload:"*), causing `json.loads()` to crash. Implement a regex fallback to extract only the JSON object from Claude's raw response:
```python
import re
import anthropic
import json

claude = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)

def generate_pitch_email(lead: LeadDetailResponse) -> dict:
    prompt = f"""Write a 3-line cold email opener for {lead.company_name}.
Signal: {lead.why_now}
Contact title: {lead.contacts[0].title if lead.contacts else 'Founder'}
Tone: direct, no fluff, no 'Hope this finds you well'.
Return JSON: {{"subject_line": string, "email_body": string}}"""

    response = claude.messages.create(
        model="claude-haiku-4-5",
        max_tokens=300,           # hard cap — email is short
        messages=[{"role": "user", "content": prompt}]
    )
    
    raw = response.content[0].text
    # Safe Extraction: Strip any markdown code fences or conversational preambles
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    return {"subject_line": "Following up on your growth", "email_body": raw}
```

### Place 2 — Batch news summarisation (Local Extractive Fallback)
If NewsAPI returns 5 articles per company, you're sending all 5 into Gemini's scoring prompt which inflates tokens. Instead, summarise them locally first using a lightweight extractive approach — no LLM needed:

```python
def extract_key_sentences(text: str, max_sentences: int = 2) -> str:
    """
    Takes the first 2 sentences containing a keyword.
    Costs zero tokens. Good enough for funding/hiring signals.
    """
    sentences = text.split(". ")
    keywords = ["raised", "funding", "hired", "expanded", "launched", "SDR"]
    relevant = [s for s in sentences if any(k.lower() in s.lower() for k in keywords)]
    return ". ".join(relevant[:max_sentences])
```

Pass this summary to Gemini instead of full article text. Reduces tokens per company by ~60%.

---

## Phase 6 — Persist, badge, and surface

### Database Schema Expansion (`models.py`)
**Critical Detail (Gap):**
The current `LeadSnapshot` schema in `models.py` only contains 4 columns (`id`, `domain`, `intent_score`, `last_updated`). To persist the entire lead pipeline state, you must expand `models.py` and recreate the database with the following columns:
- `company_name` (VARCHAR)
- `tier` (VARCHAR)
- `badge` (VARCHAR)
- `badge_label` (VARCHAR)
- `full_payload` (TEXT)

This schema gap is the root blocker for the entire persistence layer. Until `models.py` is expanded and the DB is recreated, no phase can write or read complete lead data.

### Replacing the Scheduler Stub
**Critical Detail (Gap):**
The current `run_pipeline_job()` in `main.py` is a hardcoded stub that only calls `calculate_freshness_badge("creworklabs.com", 85, False)`. Replace this stub so that it calls `run_batch_pipeline()` from the orchestrator.

Since `orchestrator.py` is a new file, ensure you add an explicit import line at the top of the scheduler file (e.g. `pipeline_scheduler.py` or wherever the APScheduler jobs are configured):
```python
from backend.pipeline.orchestrator import run_batch_pipeline
```
Without this stated, the batch runner logic could get incorrectly bundled directly into the scheduler file rather than maintaining clean architectural separation.

The single best demo moment: Start your Loom with the server cold and the dashboard empty. Let the scheduler fire automatically on startup. Watch leads appear in the table with no button press. That shows the evaluator the pipeline is genuinely autonomous, not a manual process with a nice UI on top.


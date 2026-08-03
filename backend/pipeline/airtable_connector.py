import os
import json
import logging
import httpx
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

logger = logging.getLogger("AirtableConnector")

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME", "testing")

STATE_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "pipeline_state.json"))

def load_pipeline_state() -> Dict[str, Any]:
    """Loads the local offset cursor state from pipeline_state.json."""
    default_state = {
        "current_offset": 0,
        "daily_target": 30,
        "daily_processed_count": 0,
        "last_run_timestamp": None,
        "total_records_in_airtable": 0
    }
    if not os.path.exists(STATE_FILE_PATH):
        os.makedirs(os.path.dirname(STATE_FILE_PATH), exist_ok=True)
        save_pipeline_state(default_state)
        return default_state
    
    try:
        with open(STATE_FILE_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
            return {**default_state, **state}
    except Exception as e:
        logger.warning(f"Failed to read {STATE_FILE_PATH}, falling back to defaults: {e}")
        return default_state

def save_pipeline_state(state: Dict[str, Any]) -> None:
    """Saves the local offset cursor state to pipeline_state.json."""
    try:
        os.makedirs(os.path.dirname(STATE_FILE_PATH), exist_ok=True)
        with open(STATE_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write to {STATE_FILE_PATH}: {e}")

_CANDIDATE_CACHE: List[Dict[str, Any]] = []
_CACHE_LAST_FETCHED: Optional[datetime] = None
CACHE_TTL_SECONDS = 300  # 5 minutes

async def fetch_all_airtable_candidates(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    Fetches all candidate records from Airtable to maintain complete master index.
    Caches results in memory for 5 minutes to minimize network latency and rate limits.
    """
    global _CANDIDATE_CACHE, _CACHE_LAST_FETCHED

    now = datetime.now(timezone.utc)
    if not force_refresh and _CANDIDATE_CACHE and _CACHE_LAST_FETCHED:
        elapsed = (now - _CACHE_LAST_FETCHED).total_seconds()
        if elapsed < CACHE_TTL_SECONDS:
            logger.info(f"Using cached Airtable candidates ({len(_CANDIDATE_CACHE)} records, fetched {int(elapsed)}s ago).")
            return _CANDIDATE_CACHE

    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        logger.error("Airtable credentials missing in backend/.env!")
        return []

    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }

    records_accumulated = []
    offset_token = None


    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            params = {}
            if offset_token:
                params["offset"] = offset_token

            try:
                res = await client.get(url, headers=headers, params=params)
                res.raise_for_status()
                data = res.json()

                recs = data.get("records", [])
                for rec in recs:
                    fields = rec.get("fields", {})
                    company_name = fields.get("Company Name") or fields.get("Company") or fields.get("Name") or "Unknown"
                    domain = fields.get("Website") or fields.get("Domain") or fields.get("URL") or ""
                    
                    if company_name and domain:
                        records_accumulated.append({
                            "airtable_id": rec.get("id"),
                            "company_name": company_name.strip(),
                            "domain": domain.replace("https://", "").replace("http://", "").strip("/"),
                            "firmographics": {
                                "industry": fields.get("Industry") or fields.get("Industry Tags") or "B2B SaaS / Tech",
                                "employee_count": fields.get("Headcount") or fields.get("Employee Size") or 150,
                                "total_funding": fields.get("Total Funding") or fields.get("Last Funding Amount"),
                                "linkedin": fields.get("LinkedIn"),
                                "annual_revenue": fields.get("Annual Revenue")
                            },
                            "raw_fields": fields
                        })

                offset_token = data.get("offset")
                if not offset_token:
                    break
            except Exception as e:
                logger.error(f"Error fetching page from Airtable: {e}")
                break

    if records_accumulated:
        _CANDIDATE_CACHE = records_accumulated
        _CACHE_LAST_FETCHED = datetime.now(timezone.utc)

    return records_accumulated


async def get_ui_test_batch(limit: int = 2) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Fetches the next 2 candidate companies for the interactive UI test run.
    Advances `current_offset += 2` and decrements daily remaining quota by 2.
    """

    state = load_pipeline_state()
    all_candidates = await fetch_all_airtable_candidates()
    
    total_count = len(all_candidates)
    state["total_records_in_airtable"] = total_count

    if total_count == 0:
        logger.warning("No candidate records found in Airtable!")
        save_pipeline_state(state)
        return [], state

    current_offset = state.get("current_offset", 0)
    if current_offset >= total_count:
        current_offset = 0  # Rotational reset

    end_offset = min(current_offset + limit, total_count)
    batch = all_candidates[current_offset:end_offset]

    # Advance pointer and track daily count
    new_offset = end_offset if end_offset < total_count else 0
    state["current_offset"] = new_offset
    state["daily_processed_count"] += len(batch)
    state["last_run_timestamp"] = datetime.now(timezone.utc).isoformat()

    save_pipeline_state(state)
    logger.info(f"UI Test Batch: Fetched {len(batch)} candidates. Offset moved from {current_offset} to {new_offset}.")
    return batch, state

async def get_midnight_cron_batch(daily_quota: int = 30) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Fetches the remaining daily batch for midnight cron execution.
    Calculates remaining = max(0, daily_quota - daily_processed_count).
    Advances current_offset and resets daily_processed_count to 0.
    """
    state = load_pipeline_state()
    processed_today = state.get("daily_processed_count", 0)
    remaining_needed = max(0, daily_quota - processed_today)

    if remaining_needed == 0:
        logger.info("Daily target already satisfied by UI test runs today! Resetting daily count.")
        state["daily_processed_count"] = 0
        save_pipeline_state(state)
        return [], state

    all_candidates = await fetch_all_airtable_candidates()
    total_count = len(all_candidates)
    state["total_records_in_airtable"] = total_count

    if total_count == 0:
        save_pipeline_state(state)
        return [], state

    current_offset = state.get("current_offset", 0)
    if current_offset >= total_count:
        current_offset = 0

    end_offset = min(current_offset + remaining_needed, total_count)
    batch = all_candidates[current_offset:end_offset]

    new_offset = end_offset if end_offset < total_count else 0
    state["current_offset"] = new_offset
    state["daily_processed_count"] = 0  # Reset for next day
    state["last_run_timestamp"] = datetime.now(timezone.utc).isoformat()

    save_pipeline_state(state)
    logger.info(f"Midnight Cron Batch: Fetched {len(batch)} candidates (Remaining from {remaining_needed}). Offset: {new_offset}.")
    return batch, state

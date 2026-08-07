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

async def fetch_airtable_candidates_batch(
    limit: int = 5,
    offset_token: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Fetches a single batch of `limit` candidates directly from Airtable using
    native `pageSize=limit` and `maxRecords=limit`.
    Makes exactly ONE HTTP call to Airtable.
    Returns (batch_records, next_offset_token).
    """
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        logger.error("Airtable credentials missing in backend/.env!")
        return [], None

    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }

    params = {
        "pageSize": limit
    }
    if offset_token:
        params["offset"] = offset_token

    records_accumulated = []
    next_offset = None

    async with httpx.AsyncClient(timeout=30.0) as client:
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

            next_offset = data.get("offset")
        except Exception as e:
            logger.error(f"Error fetching batch from Airtable: {e}")

    return records_accumulated, next_offset


async def get_ui_test_batch(limit: int = 5) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Fetches the next `limit` candidate companies for the interactive UI test run.
    Uses native Airtable pagination (1 HTTP call).
    """

    state = load_pipeline_state()
    offset_token = state.get("next_offset_token")

    batch, next_offset = await fetch_airtable_candidates_batch(limit=limit, offset_token=offset_token)

    state["next_offset_token"] = next_offset
    state["daily_processed_count"] = state.get("daily_processed_count", 0) + len(batch)
    state["last_run_timestamp"] = datetime.now(timezone.utc).isoformat()

    save_pipeline_state(state)
    names = [c.get("company_name", "Unknown") for c in batch]
    logger.info(f"\n=========================================================================")
    logger.info(f"📋 AIRTABLE BATCH FETCHED ({len(batch)} companies): {', '.join(names)}")
    logger.info(f"=========================================================================\n")
    return batch, state

async def get_midnight_cron_batch(daily_quota: int = 30) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Fetches the remaining daily batch for midnight cron execution.
    Calculates remaining = max(0, daily_quota - daily_processed_count).
    Advances offset token and resets daily_processed_count to 0.
    """
    state = load_pipeline_state()
    processed_today = state.get("daily_processed_count", 0)
    remaining_needed = max(0, daily_quota - processed_today)

    if remaining_needed == 0:
        logger.info("Daily target already satisfied by UI test runs today! Resetting daily count.")
        state["daily_processed_count"] = 0
        save_pipeline_state(state)
        return [], state

    offset_token = state.get("next_offset_token")
    batch, next_offset = await fetch_airtable_candidates_batch(limit=remaining_needed, offset_token=offset_token)

    state["next_offset_token"] = next_offset
    state["daily_processed_count"] = 0  # Reset for next day
    state["last_run_timestamp"] = datetime.now(timezone.utc).isoformat()

    save_pipeline_state(state)
    logger.info(f"Midnight Cron Batch: Fetched {len(batch)} candidates (Remaining from {remaining_needed}). Next offset: {next_offset}.")
    return batch, state


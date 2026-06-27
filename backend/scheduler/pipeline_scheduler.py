from datetime import datetime, timezone
import logging
from typing import Optional
from sqlalchemy import text
from backend.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PipelineScheduler")


def calculate_freshness_badge(
    domain: str,
    new_score: int,
    is_new_company: bool
) -> tuple[Optional[str], str]:
    """
    Compares the calculated lead metrics against previous historical
    database state logs to determine row delta indicators. (Fix 5)

    Returns:
        tuple: (badge, badge_label)
        badge aligns with Strict Data Contract:
        'new_today' | 'score_up' | 'score_down' | 'signal_added' | None
    """
    if is_new_company:
        return "new_today", "New today"

    db = SessionLocal()
    try:
        # Retrieve the most recent existing historical log for comparison
        row = db.execute(
            text(
                "SELECT intent_score FROM lead_snapshots "
                "WHERE domain=:d ORDER BY last_updated DESC LIMIT 1"
            ),
            {"d": domain}
        ).fetchone()

        if not row:
            return "new_today", "New today"

        previous_score = row[0]
        score_delta = new_score - previous_score

        if score_delta >= 15:
            return "score_up", f"Score up {score_delta} pts"
        elif score_delta <= -15:
            return "score_down", f"Score down {abs(score_delta)} pts"

    except Exception as e:
        logger.error(
            f"Error evaluating delta computations for {domain}: {str(e)}"
        )
    finally:
        db.close()

    return None, ""


TARGET_COMPANIES = ["Vercel", "Stripe", "Supabase"]

def run_pipeline_job():
    """
    Unified background execution runner triggered by the system intervals.
    Generates telemetry updates and state logs inside local database tables.
    """
    logger.info(
        f"Initiating background lead ingestion sweep at "
        f"{datetime.now(timezone.utc).isoformat()}"
    )
    db = SessionLocal()
    success_count = 0
    errors = False
    
    try:
        import asyncio
        import time
        from backend.pipeline.orchestrator import run_pipeline_for_company
        
        for idx, company in enumerate(TARGET_COMPANIES):
            logger.info(f"Processing target: {company}")
            try:
                res = asyncio.run(run_pipeline_for_company(company))
                if res.get("status") == "success":
                    success_count += 1
            except Exception as e:
                logger.error(f"Error orchestrating {company}: {e}")
                errors = True
                
            if idx < len(TARGET_COMPANIES) - 1:
                logger.info(f"Sleeping 10s to respect rate limits...")
                time.sleep(10)  # Rate limit delay

        # Retrieve new total lead count for telemetry
        total_leads = db.execute(text("SELECT COUNT(*) FROM lead_snapshots")).scalar()

        db.execute(
            text(
                "INSERT OR REPLACE INTO pipeline_status "
                "(id, last_run_time, lead_count_processed, status, errors_encountered) "
                "VALUES ('1', :t, :c, :s, :e)"
            ),
            {
                "t": datetime.now(timezone.utc).isoformat(),
                "c": total_leads,
                "s": "Completed Successfully" if not errors else "Completed with Errors",
                "e": errors
            }
        )
        db.commit()
        logger.info("Automated workflow tracking cycles processed successfully.")
    except Exception as e:
        logger.error(
            f"Execution exception inside background engine tracker: {str(e)}"
        )
    finally:
        db.close()

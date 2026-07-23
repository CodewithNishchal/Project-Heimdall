"""
Phase 6 — Autonomous Pipeline Scheduler.

Replaces the hardcoded TARGET_COMPANIES list with a call to
run_batch_pipeline() from the orchestrator, which discovers
companies autonomously via keyword sweeps.
"""
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


def run_pipeline_job():
    """
    Unified background execution runner triggered by the system intervals.
    Now calls run_batch_pipeline() for autonomous company discovery
    instead of iterating a hardcoded company list.
    """
    logger.info(
        f"Initiating autonomous background sweep at "
        f"{datetime.now(timezone.utc).isoformat()}"
    )
    db = SessionLocal()

    try:
        import asyncio
        import json
        import uuid
        from backend.pipeline.orchestrator import run_batch_pipeline
        from backend.pipeline.social_discovery import fetch_social_micro_intent
        from backend.models import SocialPostSnapshot

        # 1. Run the autonomous batch pipeline for companies
        result = asyncio.run(run_batch_pipeline())

        # 2. Also run the social media posts discovery sweep
        try:
            with open("backend/intent_config.json", "r") as f:
                config = json.load(f)
                keywords = config.get("social_keywords", ["looking for marketing agency"])
        except Exception:
            keywords = ["looking for marketing agency"]

        try:
            social_posts = asyncio.run(fetch_social_micro_intent(keywords))
            for p in social_posts:
                existing = db.execute(
                    text("SELECT id FROM social_posts WHERE post_url=:u LIMIT 1"),
                    {"u": p["post_url"]}
                ).fetchone()
                if not existing:
                    db_post = SocialPostSnapshot(
                        id=str(uuid.uuid4()),
                        platform=p["platform"],
                        author_name=p["author_name"],
                        author_handle=p["author_handle"],
                        content=p["content"],
                        post_url=p["post_url"],
                        keyword_matched=p["keyword_matched"],
                        company_name=p["company_name"],
                        published_at=p["published_at"]
                    )
                    db.add(db_post)
            db.commit()
            logger.info(f"Social posts sweep complete: fetched {len(social_posts)} posts.")
        except Exception as s_err:
            logger.error(f"Social posts sweep inside scheduler error: {s_err}")

        success_count = result.get("successes", 0)
        errors = result.get("had_errors", False)

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
                "e": errors,
            },
        )
        db.commit()
        logger.info(
            f"Autonomous sweep complete: {success_count} leads processed, "
            f"{result.get('companies_processed', 0)} companies discovered."
        )
    except Exception as e:
        logger.error(
            f"Execution exception inside background engine tracker: {str(e)}"
        )
    finally:
        db.close()

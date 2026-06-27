from fastapi import APIRouter, Depends
from datetime import datetime, timezone
from pydantic import BaseModel
from sqlalchemy import text
from backend.database import get_db
from backend.scheduler.pipeline_scheduler import run_pipeline_job

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline Operations"])


class PipelineStatusResponse(BaseModel):
    last_run_time: str
    lead_count_processed: int
    status: str
    errors_encountered: bool


@router.get("/status", response_model=PipelineStatusResponse)
def get_pipeline_telemetry(db=Depends(get_db)):
    """Returns background execution metrics to frontend status layouts."""
    try:
        row = db.execute(
            text(
                "SELECT last_run_time, (SELECT COUNT(*) FROM lead_snapshots), status, errors_encountered "
                "FROM pipeline_status WHERE id='1'"
            )
        ).fetchone()
        if row:
            return PipelineStatusResponse(
                last_run_time=row[0],
                lead_count_processed=row[1] if row[1] else 0,
                status=row[2] if row[2] else "Unknown",
                errors_encountered=bool(row[3]) if row[3] is not None else False
            )
    except Exception:
        pass

    return PipelineStatusResponse(
        last_run_time="Never",
        lead_count_processed=0,
        status="Idle (No runs)",
        errors_encountered=False
    )


@router.post("/run")
def trigger_manual_pipeline_run():
    """Exposes an endpoint to bypass schedule parameters and run manual data sweeps."""
    run_pipeline_job()
    return {
        "message": "Pipeline tracking sweep manually forced.",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

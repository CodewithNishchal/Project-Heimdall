from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, JSON
from backend.database import Base
from datetime import datetime, timezone


class LeadSnapshot(Base):
    """Stores scored lead data for historical comparison and freshness badge computation."""
    __tablename__ = "lead_snapshots"

    id = Column(String, primary_key=True, index=True)
    domain = Column(String, index=True, nullable=False)
    company_name = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    employee_count = Column(Integer, nullable=True)
    funding_stage = Column(String, nullable=True)
    intent_score = Column(Integer, nullable=False, default=0)
    signal_freshness = Column(Integer, nullable=True, default=100)
    tier = Column(String, nullable=True)
    icp_fit = Column(String, nullable=True)
    badge = Column(String, nullable=True)
    why_now = Column(Text, nullable=True)
    ai_verdict = Column(Text, nullable=True)
    full_payload = Column(JSON, nullable=True)
    last_updated = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )


class PipelineStatus(Base):
    """Tracks background pipeline execution state for telemetry reporting."""
    __tablename__ = "pipeline_status"

    id = Column(String, primary_key=True, index=True)
    last_run_time = Column(String, nullable=True)
    lead_count_processed = Column(Integer, default=0)
    status = Column(String, nullable=True, default="Idle")
    errors_encountered = Column(Boolean, default=False)

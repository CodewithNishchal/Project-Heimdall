from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, JSON
from backend.database import Base
from datetime import datetime, timezone


class LeadSnapshot(Base):
    """Stores scored lead data for historical comparison and freshness badge computation."""
    __tablename__ = "lead_snapshots"

    id = Column(String, primary_key=True, index=True)
    domain = Column(String, index=True, nullable=False)
    company_name = Column(String, nullable=True)
    company_segment = Column(String, nullable=True, default="Growth Scale-up")
    industry = Column(String, nullable=True)
    employee_count = Column(Integer, nullable=True)
    funding_stage = Column(String, nullable=True)
    intent_score = Column(Integer, nullable=False, default=0)
    signal_freshness = Column(Integer, nullable=True, default=100)
    tier = Column(String, nullable=True)
    icp_fit = Column(String, nullable=True)
    badge = Column(String, nullable=True)
    social_segment = Column(String, nullable=True)  # Segment A, Segment B, Segment C
    meta_ads_active = Column(Boolean, default=False)
    meta_ads_count = Column(Integer, default=0)
    bio_url = Column(String, nullable=True)
    why_now = Column(Text, nullable=True, default="Verified public buying intent triggers detected.")
    signal_tags = Column(JSON, nullable=True, default=list)
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


class ScrapeLedger(Base):
    """Tracks previously scraped founders/companies to enforce cooldowns and protect credit budgets."""
    __tablename__ = "scrape_ledger"

    id = Column(String, primary_key=True, index=True)
    company_name = Column(String, index=True, nullable=False)
    founder_handle = Column(String, nullable=True)
    platform = Column(String, nullable=False)
    last_scraped_date = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

class SocialPostSnapshot(Base):
    """Stores curated social media posts fetched via Scrape Creators API."""
    __tablename__ = "social_posts"

    id = Column(String, primary_key=True, index=True)
    platform = Column(String, nullable=False, index=True)
    author_name = Column(String, nullable=True)
    author_handle = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    post_url = Column(String, nullable=False)
    keyword_matched = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    published_at = Column(String, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

class ScrapeCache(Base):
    """Tracks seen post URLs to prevent duplicate LLM classification in future runs."""
    __tablename__ = "scrape_cache"
    
    id = Column(String, primary_key=True, index=True)
    post_url = Column(String, unique=True, index=True, nullable=False)
    processed_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc)
    )


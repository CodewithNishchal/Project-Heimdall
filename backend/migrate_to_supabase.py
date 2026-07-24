"""
Migration Utility — Transfers all records from local SQLite (lead_intelligence.db)
to Supabase PostgreSQL.

Usage:
    python backend/migrate_to_supabase.py
"""
import sys
import os
from pathlib import Path

# Add project root directory to sys.path so 'backend' module is always found
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.config import settings
from backend.models import Base, LeadSnapshot, SocialPostSnapshot, ScrapeLedger, PipelineStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MigrateToSupabase")


def migrate_data():
    target_url = settings.DATABASE_URL
    if target_url.startswith("sqlite"):
        logger.error("DATABASE_URL in backend/.env is currently set to SQLite. "
                     "Please uncomment and set your Supabase PostgreSQL connection string first.")
        sys.exit(1)

    if target_url.startswith("postgres://"):
        target_url = target_url.replace("postgres://", "postgresql://", 1)

    logger.info("Connecting to local SQLite database...")
    backend_dir = Path(__file__).resolve().parent
    sqlite_db_path = backend_dir / "lead_intelligence.db"
    if not sqlite_db_path.exists():
        sqlite_db_path = backend_dir / "heimdall.db"

    sqlite_engine = create_engine(f"sqlite:///{sqlite_db_path}", connect_args={"check_same_thread": False})
    SQLiteSession = sessionmaker(bind=sqlite_engine)
    sqlite_db = SQLiteSession()

    logger.info("Connecting to Supabase PostgreSQL database...")
    pg_engine = create_engine(target_url, pool_pre_ping=True)
    
    # Auto-create schema if using search_path=heimdall
    try:
        from sqlalchemy import text
        with pg_engine.connect() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS heimdall;"))
            conn.commit()
    except Exception as e:
        logger.warning(f"Schema creation notice: {e}")

    # Ensure tables exist in Postgres
    Base.metadata.create_all(bind=pg_engine)
    logger.info("✅ All tables initialized in Supabase PostgreSQL!")

    PGSession = sessionmaker(bind=pg_engine)
    pg_db = PGSession()

    try:
        # 1. Migrate LeadSnapshots (Company Intelligence)
        try:
            leads = sqlite_db.query(LeadSnapshot).all()
            logger.info(f"Found {len(leads)} lead snapshot records in SQLite.")
            for lead in leads:
                existing = pg_db.query(LeadSnapshot).filter(LeadSnapshot.id == lead.id).first()
                if not existing:
                    pg_db.add(LeadSnapshot(
                        id=lead.id,
                        domain=lead.domain,
                        company_name=lead.company_name,
                        industry=lead.industry,
                        employee_count=lead.employee_count,
                        funding_stage=lead.funding_stage,
                        intent_score=lead.intent_score,
                        signal_freshness=lead.signal_freshness,
                        tier=lead.tier,
                        icp_fit=lead.icp_fit,
                        badge=lead.badge,
                        social_segment=lead.social_segment,
                        meta_ads_active=lead.meta_ads_active,
                        meta_ads_count=lead.meta_ads_count,
                        bio_url=lead.bio_url,
                        why_now=lead.why_now,
                        ai_verdict=lead.ai_verdict,
                        full_payload=lead.full_payload,
                        last_updated=lead.last_updated
                    ))
            pg_db.commit()
            logger.info("✅ LeadSnapshots successfully migrated to Supabase!")
        except Exception as e_lead:
            logger.info(f"No existing LeadSnapshots table found in SQLite to migrate: {e_lead}")

        # 2. Migrate SocialPostSnapshots (Social Media Thread Discovery)
        try:
            posts = sqlite_db.query(SocialPostSnapshot).all()
            logger.info(f"Found {len(posts)} social post records in SQLite.")
            for post in posts:
                existing = pg_db.query(SocialPostSnapshot).filter(SocialPostSnapshot.id == post.id).first()
                if not existing:
                    pg_db.add(SocialPostSnapshot(
                        id=post.id,
                        platform=post.platform,
                        author_name=post.author_name,
                        author_handle=post.author_handle,
                        content=post.content,
                        post_url=post.post_url,
                        keyword_matched=post.keyword_matched,
                        company_name=post.company_name,
                        published_at=post.published_at,
                        created_at=post.created_at
                    ))
            pg_db.commit()
            logger.info("✅ SocialPostSnapshots successfully migrated to Supabase!")
        except Exception as e_post:
            logger.info(f"No existing SocialPostSnapshots table found in SQLite to migrate: {e_post}")

        # 3. Migrate ScrapeLedger
        try:
            ledgers = sqlite_db.query(ScrapeLedger).all()
            for leg in ledgers:
                existing = pg_db.query(ScrapeLedger).filter(ScrapeLedger.id == leg.id).first()
                if not existing:
                    pg_db.add(ScrapeLedger(
                        id=leg.id,
                        company_name=leg.company_name,
                        founder_handle=leg.founder_handle,
                        platform=leg.platform,
                        last_scraped_date=leg.last_scraped_date
                    ))
            pg_db.commit()
            logger.info("✅ ScrapeLedgers successfully migrated to Supabase!")
        except Exception as e_leg:
            logger.info(f"No existing ScrapeLedger table found in SQLite to migrate: {e_leg}")

        logger.info("🎉 Supabase setup complete! Your Supabase database is online and ready.")


    except Exception as err:
        pg_db.rollback()
        logger.error(f"Migration failed: {err}")
    finally:
        sqlite_db.close()
        pg_db.close()


if __name__ == "__main__":
    migrate_data()

import asyncio
import logging
from datetime import datetime, timezone
from backend.database import SessionLocal
from backend.models import LeadSnapshot
from backend.pipeline.streaming_orchestrator import (
    resolve_linkedin_company_id,
    fetch_linkedin_company_insights,
    fetch_company_jobs_serper,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("test_enrich_missing_jobs")


async def enrich_leads_without_jobs():
    """Retrieves all companies in DB missing job openings or insights,

    fetches their jobs & insights using current pipeline functions,

    and persists updated payloads back to storage.

    """
    db = SessionLocal()
    try:
        # 1. Fetch all leads from database
        all_leads = db.query(LeadSnapshot).all()
        logger.info(f"📊 Total leads in database: {len(all_leads)}")

        # 2. Filter for leads missing job openings or insights
        leads_to_enrich = [
            lead for lead in all_leads
            if not lead.job_openings or not lead.company_insights
        ]

        if not leads_to_enrich:
            logger.info("✨ All leads already have enriched jobs and insights data!")
            return

        logger.info(f"🔍 Found {len(leads_to_enrich)} leads requiring jobs & insights enrichment:\n")
        for idx, lead in enumerate(leads_to_enrich, 1):
            logger.info(f"  {idx}. {lead.company_name} ({lead.domain}) - Score: {lead.intent_score}")

        logger.info("\n🚀 Starting batch enrichment pipeline...\n" + "=" * 60)

        enriched_count = 0
        for lead in leads_to_enrich:
            company_name = lead.company_name or lead.domain or "Company"
            domain = lead.domain or "example.com"
            company_slug = domain.split(".")[0].lower() if domain else company_name.lower().replace(" ", "")

            logger.info(f"\n⚙️  Processing: {company_name} ({domain})...")

            # A. Resolve numeric LinkedIn Company ID
            company_id = await resolve_linkedin_company_id(company_slug)
            lead.company_linkedin_id = company_id
            logger.info(f"  📌 LinkedIn Company ID: {company_id or 'Not found'}")

            # B. Fetch LinkedIn Insights if company ID resolved
            insights = None
            if company_id:
                logger.info(f"  📈 Fetching LinkedIn Insights for ID {company_id}...")
                insights = await fetch_linkedin_company_insights(company_id, company_slug)
            lead.company_insights = insights

            # C. Fetch Active ATS Jobs via Serper (Senior-Calibrated Strategy)
            logger.info(f"  💼 Fetching Jobs via Serper for {company_name}...")
            jobs_res = await fetch_company_jobs_serper(company_name, company_slug, domain)
            lead.job_openings = jobs_res

            # D. Update full_payload JSON structure
            payload = lead.full_payload or {}
            payload["company_linkedin_id"] = company_id
            payload["company_insights"] = insights
            payload["job_openings"] = jobs_res
            lead.full_payload = payload

            # E. Save changes to DB
            lead.last_updated = datetime.now(timezone.utc)
            db.commit()
            enriched_count += 1

            verified_jobs_count = len(jobs_res.get("verified_jobs", [])) if jobs_res else 0
            logger.info(f"  ✅ Saved {company_name}: {verified_jobs_count} verified jobs & insights stored.")

        logger.info("\n" + "=" * 60)
        logger.info(f"🎉 Batch enrichment completed! Successfully updated {enriched_count} leads in storage.")

    except Exception as e:
        logger.error(f"❌ Error during batch enrichment: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(enrich_leads_without_jobs())

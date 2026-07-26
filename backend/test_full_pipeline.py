import asyncio
import logging
import sys
import os
import json

# Add the project root to sys.path so we can import 'backend'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.pipeline.orchestrator import run_batch_pipeline
from backend.database import SessionLocal
from backend.models import LeadSnapshot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    print("="*60)
    print("🚀 HEIMDALL FULL BATCH PIPELINE TEST")
    print("="*60)
    print("\nStarting full autonomous pipeline execution...")
    print("This will fetch ~100 companies from JobSpy, Serper, and NewsAPI.")
    print("Gemini will select the Top 5, and run the Deep Sweep on them.")
    
    result = await run_batch_pipeline()
    print("\n" + "="*60)
    print("✅ PIPELINE EXECUTION COMPLETE")
    print("="*60)
    print(json.dumps(result, indent=2))
    
    print("\n[DB Check] Most recent 5 companies inserted into database:")
    db = SessionLocal()
    try:
        leads = db.query(LeadSnapshot).order_by(LeadSnapshot.id.desc()).limit(5).all()
        for lead in leads:
            print(f"- {lead.company_name} (Score: {lead.intent_score}, Tier: {lead.tier})")
            print(f"  AI Verdict: {lead.ai_verdict}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())

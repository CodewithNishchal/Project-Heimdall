import os
import sys
from sqlalchemy import text
from dotenv import load_dotenv

# Add project root to sys.path so we can import 'backend'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join("backend", ".env"))

from backend.database import engine

def run_migration():
    print("🚀 Running DB Migration to add new columns to lead_snapshots...")
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE lead_snapshots ADD COLUMN company_linkedin_id TEXT;"))
            print("✅ Added company_linkedin_id column")
        except Exception as e:
            print(f"⚠️ Could not add company_linkedin_id: {e}")

        try:
            conn.execute(text("ALTER TABLE lead_snapshots ADD COLUMN company_insights JSONB;"))
            print("✅ Added company_insights column")
        except Exception as e:
            print(f"⚠️ Could not add company_insights: {e}")
            
        try:
            conn.execute(text("ALTER TABLE lead_snapshots ADD COLUMN IF NOT EXISTS annual_revenue TEXT;"))
            print("✅ Added annual_revenue column")
        except Exception as e:
            print(f"⚠️ Could not add annual_revenue: {e}")

        try:
            conn.execute(text("ALTER TABLE lead_snapshots ADD COLUMN job_openings JSONB;"))
            print("✅ Added job_openings column")
        except Exception as e:
            print(f"⚠️ Could not add job_openings: {e}")

    print("🎉 Migration complete. You can restart the backend server now.")

if __name__ == "__main__":
    run_migration()

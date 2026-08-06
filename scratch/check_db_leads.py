import os
import sys
import json
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join("backend", ".env"))

db_url = os.environ.get("DATABASE_URL")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
engine = create_engine(db_url)

def check_db():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT company_name, job_openings, company_insights FROM lead_snapshots ORDER BY last_updated DESC LIMIT 5"))
        for row in result:
            print("=========================================")
            print(f"Company: {row[0]}")
            
            jobs = row[1]
            if jobs:
                print(f"Jobs Total Results: {jobs.get('total_results', 'N/A')}")
            else:
                print("Jobs: None")
                
            insights = row[2]
            if insights:
                print(f"Insights Headcount: {insights.get('total_employees', 'N/A')}")
            else:
                print("Insights: None")

if __name__ == "__main__":
    check_db()

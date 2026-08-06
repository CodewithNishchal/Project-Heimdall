import os
import sys
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal
from backend.models import LeadSnapshot
from backend.pipeline.streaming_orchestrator import extract_revenue_from_exa_text

def format_revenue(val_str: str) -> str:
    if not val_str or val_str == "N/A" or not any(c.isdigit() for c in val_str):
        return "N/A"
    s = re.sub(r'(?i)\s*million\b', 'M', val_str)
    s = re.sub(r'(?i)\s*billion\b', 'B', s)
    s = re.sub(r'(?i)\s*thousand\b', 'K', s)

    m = re.search(r'(~?\s*\$?\s*[\d\.]+(?:\s*-\s*\$?\s*[\d\.]+)?)\s*([MKBmkb])?', s)
    if m:
        raw_num = m.group(1).replace("~", "").replace("$", "").strip()
        unit = (m.group(2) or "").toUpperCase()
        if not unit:
            try:
                num_val = float(raw_num.split("-")[0].strip())
                if 0 < num_val < 1000:
                    unit = "M"
            except Exception:
                pass
        prefix = "~$" if "~" in s else "$"
        return f"{prefix}{raw_num}{unit}"
    return "N/A"

def backfill():
    db = SessionLocal()
    try:
        leads = db.query(LeadSnapshot).all()
        for lead in leads:
            if lead.annual_revenue:
                new_val = format_revenue(lead.annual_revenue)
                if new_val != lead.annual_revenue:
                    print(f"Update ARR for {lead.company_name}: '{lead.annual_revenue}' -> '{new_val}'")
                    lead.annual_revenue = new_val
                    if isinstance(lead.full_payload, dict):
                        lead.full_payload["annual_revenue"] = new_val
        db.commit()
        print("Done backfilling revenues!")
    finally:
        db.close()

if __name__ == "__main__":
    backfill()

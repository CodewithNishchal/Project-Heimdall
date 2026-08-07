import os
import sys
import json
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join("backend", ".env"), override=True)

from backend.database import SessionLocal
from backend.models import LeadSnapshot

def audit_db():
    db = SessionLocal()
    try:
        leads = db.query(LeadSnapshot).all()
        lines = []
        lines.append(f"Auditing {len(leads)} companies in DB for the Hiring Trend bug:\n")
        lines.append(f"{'Company Name':<32} | {'Has new_hires?':<15} | {'Status':<40}")
        lines.append("-" * 90)

        affected_count = 0
        unaffected_count = 0

        for l in leads:
            c_name = l.company_name or l.domain or "Unknown"
            insights = l.company_insights if isinstance(l.company_insights, dict) else {}
            new_hires = insights.get("new_hires") if isinstance(insights, dict) else None

            if new_hires and isinstance(new_hires, list) and len(new_hires) > 0:
                years = set()
                for nh in new_hires:
                    d = str(nh.get("date") or "")
                    if "-" in d:
                        years.add(d.split("-")[0])
                sorted_years = sorted(list(years))
                if len(sorted_years) > 1 and "2025" in sorted_years and "2026" in sorted_years:
                    status = f"❌ AFFECTED (Shows 2025 data instead of 2026)"
                    affected_count += 1
                else:
                    status = f"⚠️ Single Year ({sorted_years})"
                    unaffected_count += 1
            else:
                status = "✅ NOT AFFECTED (Uses fallback hiring_trend: 2026)"
                unaffected_count += 1

            has_nh = "YES" if (new_hires and len(new_hires) > 0) else "NO"
            lines.append(f"{c_name:<32} | {has_nh:<15} | {status:<40}")

        lines.append("\n" + "=" * 90)
        lines.append(f"Total Companies Audited : {len(leads)}")
        lines.append(f"Affected Companies     : {affected_count}")
        lines.append(f"Unaffected Companies   : {unaffected_count}")

        out_path = os.path.join("scratch", "audit_results.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"Audit written to {out_path}")

    finally:
        db.close()

if __name__ == "__main__":
    audit_db()

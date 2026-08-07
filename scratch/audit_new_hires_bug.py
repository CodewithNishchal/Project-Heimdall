import json
import os

def audit_companies():
    dump_path = os.path.join("scratch", "all_backend_leads_dump.json")
    if not os.path.exists(dump_path):
        print("Dump file not found")
        return

    with open(dump_path, "r", encoding="utf-8") as f:
        leads = json.load(f)

    print(f"Auditing {len(leads)} companies for new_hires bug:\n")
    print(f"{'Company Name':<30} | {'Has new_hires?':<15} | {'Affected Status':<35}")
    print("-" * 85)

    for l in leads:
        c_name = l.get("company_name") or l.get("domain") or "Unknown"
        insights = l.get("company_insights") or {}
        new_hires = insights.get("new_hires") if isinstance(insights, dict) else None
        
        if new_hires and isinstance(new_hires, list) and len(new_hires) > 0:
            years = set()
            for nh in new_hires:
                d = str(nh.get("date") or "")
                if "-" in d:
                    years.add(d.split("-")[0])
            if len(years) > 1:
                status = f"❌ AFFECTED (Has multi-year: {sorted(list(years))})"
            else:
                status = f"⚠️ Single Year ({list(years)})"
        else:
            status = "✅ NOT AFFECTED (No new_hires, uses hiring_trend)"

        has_nh = "YES" if (new_hires and len(new_hires) > 0) else "NO"
        print(f"{c_name:<30} | {has_nh:<15} | {status:<35}")

if __name__ == "__main__":
    audit_companies()

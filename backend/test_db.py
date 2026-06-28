import sqlite3
import json
db = sqlite3.connect('backend/lead_intelligence.db')
res = db.execute('SELECT company_name, domain, icp_fit, intent_score FROM lead_snapshots ORDER BY last_updated DESC LIMIT 2').fetchall()
print("Top 2 latest records:")
for r in res:
    print(r)

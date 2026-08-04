import json
from backend.pipeline.social_classifier import is_prefiltered

with open("backend/test_social_discovery_all_providers_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

items = data.get("items", [])

passed_prefilter = []
blocked_prefilter = []

for item in items:
    content = item.get("content") or item.get("title") or ""
    author_bio = item.get("company_name") or item.get("author_name") or ""
    
    # Check prefilter
    is_skip, skip_reason = is_prefiltered(content, author_bio)
    
    lead_summary = {
        "platform": item.get("platform"),
        "author": author_bio,
        "content_snippet": content[:120].replace("\n", " "),
        "skip_reason": skip_reason
    }
    
    if is_skip:
        blocked_prefilter.append(lead_summary)
    else:
        passed_prefilter.append(lead_summary)

print(f"======================================================================")
print(f"📊 END-TO-END PIPELINE RELEVANCE EVALUATION")
print(f"======================================================================")
print(f"Total Raw Items Fetched   : {len(items)}")
print(f"Passed Classifier Prefilter: {len(passed_prefilter)} ({round(len(passed_prefilter)/len(items)*100, 1)}%)")
print(f"Filtered Out (Sellers/Noise): {len(blocked_prefilter)} ({round(len(blocked_prefilter)/len(items)*100, 1)}%)\n")

print(f"--- SAMPLE PASSED HIGH-INTENT BUYER LEADS ({len(passed_prefilter)} TOTAL) ---")
for i, lead in enumerate(passed_prefilter[:10], 1):
    print(f"[{i}] Platform: {lead['platform'].upper()} | Author: {lead['author']}")
    print(f"    Content : {lead['content_snippet']}...\n")

print(f"--- SAMPLE FILTERED NOISE / SELLER PITCHES ({len(blocked_prefilter)} TOTAL) ---")
for i, lead in enumerate(blocked_prefilter[:5], 1):
    print(f"[{i}] Platform: {lead['platform'].upper()} | Reason: {lead['skip_reason']}")
    print(f"    Content : {lead['content_snippet']}...\n")

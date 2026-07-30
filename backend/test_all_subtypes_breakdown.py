import json
import logging
from backend.config_manager import load_intent_config
from backend.pipeline.discovery import apply_deterministic_filter

logging.basicConfig(level=logging.INFO)

def run_subtype_categorization_test():
    try:
        with open("backend/exa_test_results.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            candidates = data.get("top_10_candidates", []) + data.get("other_candidates", [])
            if not candidates:
                # If only top 10 stored, load raw results if available
                candidates = data.get("top_10_candidates", [])
    except Exception as e:
        print(f"Error loading exa_test_results.json: {e}")
        return

    config = load_intent_config()
    subtypes = config.get("recruitment_subtypes", {})

    print("=" * 80)
    print("📊 RECRUITMENT SUB-TYPES CATEGORIZATION AUDIT (100 EXA CANDIDATES)")
    print("=" * 80)

    summary = {}

    for subtype_key, info in subtypes.items():
        label = info.get("label")
        min_hc = info.get("min_employees", 5)
        max_hc = info.get("max_employees", 5000)
        exclude_terms = [t.lower() for t in info.get("exclude_terms", [])]
        target_inds = [ind.lower() for ind in info.get("target_industries", [])]

        matched = []
        filtered_out = []

        for c in candidates:
            title = c.get("title") or c.get("company_name") or "Unknown"
            text_snippet = (c.get("text_snippet") or c.get("summary") or c.get("text") or "").lower()
            
            # Simple simulation of headcount and category matching for audit
            # 1. Exclusion check
            is_excluded = any(ex in text_snippet for ex in exclude_terms)
            if is_excluded:
                filtered_out.append((title, "Matched Exclusion Term"))
                continue

            matched.append(title)

        summary[subtype_key] = {
            "label": label,
            "bounds": f"{min_hc}-{max_hc} emp",
            "matched_count": len(matched),
            "filtered_out_count": len(filtered_out),
            "sample_matched": matched[:5],
            "sample_filtered": filtered_out[:3]
        }

        print(f"\n🔹 SUB-TYPE: {label} ({subtype_key})")
        print(f"   Headcount Bounds: {min_hc}-{max_hc} employees")
        print(f"   Target Industries: {', '.join(info.get('target_industries', []))}")
        print(f"   Exclusion Terms: {', '.join(info.get('exclude_terms', []))}")
        print(f"   ✅ Matched Candidates ({len(matched)}): {', '.join(matched[:5])}{'...' if len(matched) > 5 else ''}")
        print(f"   ❌ Filtered Out ({len(filtered_out)}): {', '.join([f'{t} ({r})' for t, r in filtered_out[:3]])}")

    print("\n" + "=" * 80)
    print("💾 Saving detailed breakdown to backend/subtype_breakdown_audit.json")
    with open("backend/subtype_breakdown_audit.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("=" * 80)

if __name__ == "__main__":
    run_subtype_categorization_test()

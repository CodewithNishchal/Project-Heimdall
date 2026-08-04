import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestIndexResolution")

def resolve_index(raw_idx, total_signals: int):
    resolved_idx = None
    if raw_idx is not None:
        parsed_num = None
        if isinstance(raw_idx, int):
            parsed_num = raw_idx
        elif isinstance(raw_idx, str):
            import re
            m = re.search(r'\d+', raw_idx)
            if m:
                try:
                    parsed_num = int(m.group(0))
                except ValueError:
                    pass

        if parsed_num is not None:
            # 1. Try 0-based first
            if 0 <= parsed_num < total_signals:
                resolved_idx = parsed_num
            # 2. Try 1-based fallback
            elif 1 <= parsed_num <= total_signals:
                resolved_idx = parsed_num - 1
    return resolved_idx

def run_tests():
    raw_signals = ["url_0", "url_1", "url_2", "url_3"]
    total = len(raw_signals)

    test_cases = [
        (0, 0, "0-based integer 0 -> url_0"),
        (1, 1, "0-based integer 1 -> url_1"),
        ("0", 0, "0-based string '0' -> url_0"),
        ("1", 1, "0-based string '1' -> url_1"),
        ("S1", 1, "0-based string 'S1' -> url_1"),
        ("[S2]", 2, "0-based bracket '[S2]' -> url_2"),
        ("S4", 3, "1-based fallback 'S4' (out of 0-based 0-3) -> url_3 (last item)"),
        (99, None, "Out-of-bounds integer 99 -> None"),
        ("invalid", None, "Invalid string -> None"),
        (None, None, "None input -> None")
    ]

    passed = 0
    for input_val, expected, desc in test_cases:
        res = resolve_index(input_val, total)
        assert res == expected, f"FAILED: {desc} (Got {res}, Expected {expected})"
        print(f"✅ PASSED: {desc} -> {raw_signals[res] if res is not None else 'None'}")
        passed += 1

    print(f"\n🎉 ALL {passed} INDEX RESOLUTION TEST CASES PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()

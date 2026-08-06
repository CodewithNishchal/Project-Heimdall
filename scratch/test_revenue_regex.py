import re
from typing import Optional

def extract_revenue_from_exa_text(text: str, structured_out: Optional[dict] = None) -> Optional[str]:
    if structured_out and isinstance(structured_out, dict):
        rev_num = structured_out.get("revenueAnnual") or structured_out.get("annual_revenue")
        if isinstance(rev_num, (int, float)) and rev_num > 0:
            if rev_num >= 1_000_000_000:
                return f"${rev_num / 1_000_000_000:.1f}B"
            elif rev_num >= 1_000_000:
                return f"${rev_num / 1_000_000:.1f}M"
            else:
                return f"${rev_num:,.0f}"

    if not text:
        return None

    patterns = [
        r'(?i)(?:annual\s+revenue|revenue|arr)\s*(?:of|is|=|:)?\s*~\s*\$?\s*([\d\.]+\s*[MKB]|\$[\d\.]+\s*[MKB]?)',
        r'(?i)\$\s*([\d\.]+\s*[MKB])\s*(?:annual\s+revenue|arr|revenue)',
        r'(?i)(?:annual\s+revenue|revenue|arr)\s*(?:of|is|=|:)?\s*\$?\s*([\d\.]+\s*-\s*\$?[\d\.]+\s*[MKB]|\$?[\d\.]+\s*[MKB]?)',
        r'(?i)USD\s+([\d,]+)'
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            val = m.group(1).strip()
            if not val.startswith("$") and not val.startswith("USD"):
                return f"~${val}"
            return val
    return None

test_cases = [
    "Dispatch employs 33 people and has an annual revenue of $1.2M, founded in 2021.",
    "Company X reported annual revenue of ~$15.5M in 2025.",
    "SaaS scale-up scaled ARR to $5M-$20M without in-house marketing.",
    "Financials: Annual Revenue: USD 3,500,000,000, Total Funding: USD 180M",
    "No financial information available for this lead."
]

for tc in test_cases:
    res = extract_revenue_from_exa_text(tc)
    print(f"INPUT: {tc}\nOUTPUT: {res}\n")

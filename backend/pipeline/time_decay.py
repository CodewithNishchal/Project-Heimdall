from datetime import datetime, timezone

RECENCY_TIERS = [
    (30,  1.00),   # < 30 days  -> Full weight contribution (100%)
    (90,  0.70),   # 30-90 days -> 70% retention multiplier
    (180, 0.40),   # 90-180 days -> 40% retention multiplier
    (365, 0.20),   # 180-365 days -> 20% retention multiplier
]
FALLBACK_MULTIPLIER = 0.10  # > 1 year -> 10% anchor floor


def calculate_time_decay(event_date_str: str) -> tuple[float, str]:
    """
    Computes a recency factor and a string tracking indicator
    based on data age. (Fix 2)
    """
    if not event_date_str:
        return 0.50, "unknown"

    try:
        from dateutil import parser
        event_date = parser.parse(event_date_str)
        if event_date.tzinfo is None:
            event_date = event_date.replace(tzinfo=timezone.utc)
    except Exception:
        return 0.50, "unknown"

    delta_days = (datetime.now(timezone.utc) - event_date).days

    for max_days, multiplier in RECENCY_TIERS:
        if delta_days <= max_days:
            label = "current" if max_days <= 30 else f"{delta_days}d_stale"
            return multiplier, label

    return FALLBACK_MULTIPLIER, "historical"

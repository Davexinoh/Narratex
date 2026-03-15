"""
extractor.py
Narratex — Narrative Extractor

Takes raw signals from the collector and groups them into
named narratives with token associations and mention counts.
"""

import logging
from collections import defaultdict

from seeds import NARRATIVE_TOKENS

log = logging.getLogger(__name__)

# Minimum signal score for a narrative to be considered active
MIN_SIGNAL_THRESHOLD = 2


def extract_narratives(signals: list[dict]) -> list[dict]:
    """
    Aggregates raw signals into narrative clusters.

    For each narrative, computes:
    - mentions:        number of posts that mentioned this narrative
    - engagement:      sum of engagement across all relevant posts
    - weighted_signal: score weighted by engagement
    - tokens:          associated tokens from seeds.NARRATIVE_TOKENS

    Returns a list of narrative dicts ready for momentum scoring.
    """
    narrative_buckets: dict = defaultdict(lambda: {
        "mentions": 0,
        "engagement": 0,
        "weighted_signal": 0.0,
        "post_ids": [],
    })

    for signal in signals:
        for narrative, score in signal.get("narrative_scores", {}).items():
            if score < MIN_SIGNAL_THRESHOLD:
                continue

            bucket = narrative_buckets[narrative]
            engagement = signal.get("engagement", 0)

            bucket["mentions"] += 1
            bucket["engagement"] += engagement
            bucket["weighted_signal"] += score * (1 + (engagement / 100))
            bucket["post_ids"].append(signal["post_id"])

    narratives = []
    for name, bucket in narrative_buckets.items():
        narratives.append({
            "name":            name,
            "mentions":        bucket["mentions"],
            "engagement":      bucket["engagement"],
            "weighted_signal": round(bucket["weighted_signal"], 2),
            "tokens":          NARRATIVE_TOKENS.get(name, []),
            "post_count":      len(set(bucket["post_ids"])),
        })

    narratives.sort(key=lambda n: n["weighted_signal"], reverse=True)

    log.info(f"Extracted {len(narratives)} active narratives from {len(signals)} signals")
    return narratives


def normalize_signal(value: float, min_val: float, max_val: float) -> float:
    """Normalize a value to 0–100 range."""
    if max_val == min_val:
        return 50.0
    return round(((value - min_val) / (max_val - min_val)) * 100, 1)


def compute_mentions_growth(narratives: list[dict]) -> dict:
    """Normalize mention counts across all narratives to a 0–100 growth score."""
    if not narratives:
        return {}
    values = [n["mentions"] for n in narratives]
    min_v, max_v = min(values), max(values)
    return {n["name"]: normalize_signal(n["mentions"], min_v, max_v) for n in narratives}


def compute_engagement_growth(narratives: list[dict]) -> dict:
    """Normalize engagement sums across all narratives to a 0–100 growth score."""
    if not narratives:
        return {}
    values = [n["engagement"] for n in narratives]
    min_v, max_v = min(values), max(values)
    return {n["name"]: normalize_signal(n["engagement"], min_v, max_v) for n in narratives}

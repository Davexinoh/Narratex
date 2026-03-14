"""
momentum.py
Narratex — Narrative Momentum Engine

Computes a weighted confidence score for each narrative
based on normalized signal dimensions.

Scoring weights:
  mentions_growth   → 50%  (social velocity is the strongest signal)
  engagement_growth → 30%  (depth of discussion matters)
  volume_growth     → 20%  (market confirmation signal)

Confidence = weighted sum, clamped to 0–100.
"""

import logging
import random
from datetime import datetime, timezone

from extractor import compute_mentions_growth, compute_engagement_growth

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scoring weights — must sum to 1.0
# ---------------------------------------------------------------------------
WEIGHT_MENTIONS    = 0.50
WEIGHT_ENGAGEMENT  = 0.30
WEIGHT_VOLUME      = 0.20

# Minimum confidence threshold to include in output
MIN_CONFIDENCE = 20


def get_volume_growth_proxy(narrative_name: str, seed: int = 42) -> float:
    """
    Volume growth proxy.

    In production this would pull from Binance REST API:
    GET /api/v3/ticker/24hr for tokens in the narrative.

    For now: deterministic pseudo-random seeded by narrative name,
    so scores are stable across runs while being distinct per narrative.
    """
    rng = random.Random(hash(narrative_name) % (2**32))
    return round(rng.uniform(30, 90), 1)


def score_narratives(narratives: list[dict]) -> list[dict]:
    """
    Takes extracted narratives and returns them with a computed
    confidence score and individual signal breakdowns.

    Output per narrative:
    {
        "name": str,
        "confidence": int (0–100),
        "mentions_growth": float,
        "engagement_growth": float,
        "volume_growth": float,
        "tokens": list[str],
        "scored_at": ISO timestamp,
    }
    """
    if not narratives:
        log.warning("No narratives to score")
        return []

    mentions_scores    = compute_mentions_growth(narratives)
    engagement_scores  = compute_engagement_growth(narratives)

    scored = []
    now = datetime.now(timezone.utc).isoformat()

    for n in narratives:
        name = n["name"]

        mg = mentions_scores.get(name, 0.0)
        eg = engagement_scores.get(name, 0.0)
        vg = get_volume_growth_proxy(name)

        # Weighted confidence score
        raw_confidence = (
            mg * WEIGHT_MENTIONS +
            eg * WEIGHT_ENGAGEMENT +
            vg * WEIGHT_VOLUME
        )

        confidence = int(min(100, max(0, round(raw_confidence))))

        if confidence < MIN_CONFIDENCE:
            log.debug(f"Skipping {name} — confidence {confidence} below threshold")
            continue

        scored.append({
            "name":              name,
            "confidence":        confidence,
            "mentions_growth":   round(mg, 1),
            "engagement_growth": round(eg, 1),
            "volume_growth":     round(vg, 1),
            "tokens":            n.get("tokens", []),
            "post_count":        n.get("post_count", 0),
            "scored_at":         now,
        })

    # Final sort: highest confidence first
    scored.sort(key=lambda n: n["confidence"], reverse=True)

    log.info(f"Scored {len(scored)} narratives above threshold")
    return scored

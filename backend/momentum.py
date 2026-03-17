"""
momentum.py
Narratex — Narrative Momentum Engine

Computes a weighted confidence score for each narrative
based on normalized signal dimensions.

Scoring weights:
  mentions_growth   → 50%  (social velocity is the strongest signal)
  engagement_growth → 30%  (depth of discussion matters)
  volume_growth     → 20%  (real market confirmation via Binance ticker)

Confidence = weighted sum, clamped to 0–100.
"""

import logging
import requests
from datetime import datetime, timezone

from extractor import compute_mentions_growth, compute_engagement_growth
from coingecko import fetch_multi_token_prices

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scoring weights — must sum to 1.0
# ---------------------------------------------------------------------------
WEIGHT_MENTIONS   = 0.50
WEIGHT_ENGAGEMENT = 0.30
WEIGHT_VOLUME     = 0.20

# Minimum confidence threshold to include in output
MIN_CONFIDENCE = 20


def get_lifecycle_stage(confidence: int, mentions_growth: float) -> str:
    """
    Classifies a narrative into one of four lifecycle stages.
    Must match the thresholds in dashboard.js getLifecycleStage()
    and fetch_narratives.py get_lifecycle_stage().
    """
    if confidence < 55:
        return "declining"
    if confidence < 68 and mentions_growth >= 60:
        return "emerging"
    if confidence < 68:
        return "declining"
    if confidence < 78:
        return "rising"
    return "peak"


def get_volume_growth(tokens: list[str]) -> float:
    """
    Blends Binance 24hr price change and CoinGecko 24hr change
    into a single normalized volume growth score (0–100).

    Binance is tried first for each token. CoinGecko fills in any gaps.
    Falls back to 50.0 if all requests fail.
    """
    top_tokens = tokens[:4]
    scores = []

    # --- Binance ticker ---
    binance_hits = set()
    for symbol in top_tokens:
        try:
            resp = requests.get(
                f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT",
                timeout=5,
            )
            if resp.status_code == 200:
                change = float(resp.json().get("priceChangePercent", 0))
                normalized = min(100.0, max(0.0, (change + 10.0) * 5.0))
                scores.append(normalized)
                binance_hits.add(symbol)
        except Exception as e:
            log.debug(f"Binance volume fetch failed for {symbol}: {e}")

    # --- CoinGecko fills gaps ---
    missing = [t for t in top_tokens if t not in binance_hits]
    if missing:
        try:
            cg_prices = fetch_multi_token_prices(missing)
            for symbol, data in cg_prices.items():
                change = data.get("price_change_24h") or 0
                normalized = min(100.0, max(0.0, (change + 10.0) * 5.0))
                scores.append(normalized)
        except Exception as e:
            log.debug(f"CoinGecko volume fallback failed: {e}")

    if not scores:
        log.debug("No volume data available, using neutral fallback 50.0")
        return 50.0

    return round(sum(scores) / len(scores), 1)


def score_narratives(narratives: list[dict]) -> list[dict]:
    """
    Takes extracted narratives and returns them with a computed
    confidence score, lifecycle stage, and individual signal breakdowns.

    Output per narrative:
    {
        "name":              str,
        "confidence":        int (0–100),
        "mentions_growth":   float,
        "engagement_growth": float,
        "volume_growth":     float,
        "stage":             str (emerging | rising | peak | declining),
        "tokens":            list[str],
        "post_count":        int,
        "scored_at":         ISO timestamp,
    }
    """
    if not narratives:
        log.warning("No narratives to score")
        return []

    mentions_scores   = compute_mentions_growth(narratives)
    engagement_scores = compute_engagement_growth(narratives)

    scored = []
    now = datetime.now(timezone.utc).isoformat()

    for n in narratives:
        name = n["name"]

        mg = mentions_scores.get(name, 0.0)
        eg = engagement_scores.get(name, 0.0)
        vg = get_volume_growth(n.get("tokens", []))

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
            "stage":             get_lifecycle_stage(confidence, round(mg, 1)),
            "tokens":            n.get("tokens", []),
            "post_count":        n.get("post_count", 0),
            "scored_at":         now,
        })

    # Final sort: highest confidence first
    scored.sort(key=lambda n: n["confidence"], reverse=True)

    log.info(f"Scored {len(scored)} narratives above threshold")
    return scored

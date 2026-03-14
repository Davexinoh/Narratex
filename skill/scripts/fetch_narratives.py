#!/usr/bin/env python3
"""
fetch_narratives.py
Narratex OpenClaw Skill — Live Data Fetcher

Called by OpenClaw agent to retrieve current narrative intelligence.
Hits the Narratex API first, falls back to Binance Square direct
collection if API is cold, falls back to seed data if both fail.

Output: JSON array to stdout — OpenClaw reads this.
"""

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ── Config ──────────────────────────────────────────────────────────────────
NARRATEX_API   = "https://narratex.onrender.com/api/narratives"
BINANCE_SQUARE = "https://www.binance.com/bapi/composite/v1/public/square/feed/list"
TIMEOUT        = 12  # seconds

# ── Narrative seed keywords ──────────────────────────────────────────────────
NARRATIVE_SEEDS = {
    "AI Infrastructure":     ["ai", "artificial intelligence", "llm", "gpu compute", "fetch", "rndr", "tao", "bittensor", "akt", "akash", "deai"],
    "DePIN Compute":         ["depin", "decentralized physical", "helium", "hnt", "iotex", "hivemapper", "filecoin", "compute network"],
    "Gaming Infrastructure": ["gamefi", "gaming", "web3 game", "play to earn", "imx", "immutable", "ronin", "ron", "magic", "gala"],
    "RWA Tokenization":      ["rwa", "real world asset", "tokenized", "ondo", "centrifuge", "maple", "treasury token"],
    "Layer 2 Scaling":       ["layer 2", "l2", "rollup", "optimism", "arbitrum", "base", "zksync", "polygon", "scaling"],
    "DeFi Resurgence":       ["defi", "yield", "liquidity", "amm", "dex", "aave", "uniswap", "curve", "gmx", "perp", "tvl"],
    "Bitcoin Ecosystem":     ["bitcoin", "btc", "ordinals", "brc-20", "runes", "stacks", "lightning", "btcfi"],
    "Solana Ecosystem":      ["solana", "sol", "jupiter", "jup", "raydium", "phantom", "bonk", "pyth", "saga"],
}

NARRATIVE_TOKENS = {
    "AI Infrastructure":     ["FET", "TAO", "RNDR", "AKT", "WLD", "AGIX", "OCEAN", "NMR"],
    "DePIN Compute":         ["HNT", "IOTX", "FIL", "AKT", "AR", "STORJ"],
    "Gaming Infrastructure": ["IMX", "RON", "MAGIC", "BEAM", "GALA", "SAND"],
    "RWA Tokenization":      ["ONDO", "CFG", "MPL", "TRU", "POLYX"],
    "Layer 2 Scaling":       ["ARB", "OP", "MATIC", "ZKS", "STRK", "MANTA"],
    "DeFi Resurgence":       ["AAVE", "UNI", "CRV", "GMX", "DYDX", "PENDLE"],
    "Bitcoin Ecosystem":     ["STX", "ORDI", "SATS", "RUNE", "WBTC"],
    "Solana Ecosystem":      ["SOL", "JUP", "RAY", "BONK", "PYTH", "JTO", "ORCA"],
}

SEED_DATA = [
    {"name": "AI Infrastructure",    "confidence": 84, "mentions_growth": 91.0, "engagement_growth": 88.0, "volume_growth": 62.0, "stage": "rising",   "tokens": ["FET","TAO","RNDR","AKT","WLD","AGIX"]},
    {"name": "Solana Ecosystem",      "confidence": 79, "mentions_growth": 86.0, "engagement_growth": 82.0, "volume_growth": 57.0, "stage": "peak",     "tokens": ["SOL","JUP","RAY","BONK","PYTH","JTO"]},
    {"name": "Bitcoin Ecosystem",     "confidence": 76, "mentions_growth": 84.0, "engagement_growth": 79.0, "volume_growth": 53.0, "stage": "peak",     "tokens": ["STX","ORDI","SATS","RUNE","WBTC"]},
    {"name": "DeFi Resurgence",       "confidence": 71, "mentions_growth": 77.0, "engagement_growth": 72.0, "volume_growth": 49.0, "stage": "rising",   "tokens": ["AAVE","UNI","CRV","GMX","DYDX"]},
    {"name": "DePIN Compute",         "confidence": 67, "mentions_growth": 71.0, "engagement_growth": 65.0, "volume_growth": 58.0, "stage": "emerging", "tokens": ["HNT","IOTX","FIL","AKT","AR"]},
    {"name": "Layer 2 Scaling",       "confidence": 63, "mentions_growth": 68.0, "engagement_growth": 61.0, "volume_growth": 44.0, "stage": "declining","tokens": ["ARB","OP","MATIC","ZKS","STRK"]},
    {"name": "RWA Tokenization",      "confidence": 58, "mentions_growth": 62.0, "engagement_growth": 55.0, "volume_growth": 41.0, "stage": "emerging", "tokens": ["ONDO","CFG","MPL","TRU","POLYX"]},
    {"name": "Gaming Infrastructure", "confidence": 52, "mentions_growth": 55.0, "engagement_growth": 49.0, "volume_growth": 46.0, "stage": "declining","tokens": ["IMX","RON","MAGIC","BEAM","GALA"]},
]


def get_lifecycle_stage(confidence, mentions_growth):
    if confidence < 55:
        return "declining"
    if confidence >= 55 and confidence < 68 and mentions_growth >= 60:
        return "emerging"
    if confidence >= 55 and confidence < 68:
        return "declining"
    if confidence >= 68 and confidence < 78:
        return "rising"
    return "peak"


def fetch_from_api():
    """Try the Narratex Render API first."""
    req = urllib.request.Request(
        NARRATEX_API,
        headers={"User-Agent": "NarratexSkill/1.0", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        body = json.loads(resp.read().decode())
        narratives = body.get("narratives", [])
        if not narratives:
            raise ValueError("Empty narratives from API")

        # Attach lifecycle stage if not present
        for n in narratives:
            if "stage" not in n:
                n["stage"] = get_lifecycle_stage(
                    n.get("confidence", 0),
                    n.get("mentions_growth", 0)
                )
        return narratives, "live"


def fetch_from_binance_square():
    """
    Direct Binance Square collection — used when Render is cold.
    Fetches 3 pages, scores against narrative seeds, returns top narratives.
    """
    from collections import defaultdict

    buckets = defaultdict(lambda: {"mentions": 0, "engagement": 0, "signal": 0.0})

    for page in range(1, 4):
        try:
            payload = json.dumps({"pageIndex": page, "pageSize": 20, "type": "ALL"}).encode()
            req = urllib.request.Request(
                BINANCE_SQUARE,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (compatible; NarratexSkill/1.0)",
                    "Referer": "https://www.binance.com/en/square",
                }
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                body = json.loads(resp.read().decode())
                posts = body.get("data", {}).get("list", [])

                for post in posts:
                    text = " ".join([
                        str(post.get("title", "")),
                        str(post.get("content", "")),
                        " ".join(t.get("name", "") if isinstance(t, dict) else t
                                 for t in (post.get("tagList") or []))
                    ]).lower()

                    engagement = (
                        post.get("likeCount", 0) +
                        post.get("commentCount", 0) +
                        post.get("shareCount", 0)
                    )

                    for narrative, keywords in NARRATIVE_SEEDS.items():
                        score = sum(2 if " " in kw else 1 for kw in keywords if kw in text)
                        if score >= 2:
                            buckets[narrative]["mentions"]   += 1
                            buckets[narrative]["engagement"] += engagement
                            buckets[narrative]["signal"]     += score * (1 + engagement / 100)

        except Exception:
            continue

    if not buckets:
        raise ValueError("No signals from Binance Square")

    # Normalize to 0-100 scores
    max_signal = max(b["signal"] for b in buckets.values()) or 1
    max_eng    = max(b["engagement"] for b in buckets.values()) or 1
    max_ment   = max(b["mentions"] for b in buckets.values()) or 1

    narratives = []
    for name, bucket in buckets.items():
        mg = round((bucket["mentions"]   / max_ment)   * 100, 1)
        eg = round((bucket["engagement"] / max_eng)    * 100, 1)
        vg = round((bucket["signal"]     / max_signal) * 100 * 0.6 + 30, 1)  # proxy

        confidence = int(mg * 0.50 + eg * 0.30 + vg * 0.20)
        confidence = min(100, max(0, confidence))

        narratives.append({
            "name":              name,
            "confidence":        confidence,
            "mentions_growth":   mg,
            "engagement_growth": eg,
            "volume_growth":     round(vg, 1),
            "tokens":            NARRATIVE_TOKENS.get(name, []),
            "stage":             get_lifecycle_stage(confidence, mg),
        })

    narratives.sort(key=lambda n: n["confidence"], reverse=True)
    return narratives, "binance_square"


def main():
    source = "seed"
    narratives = SEED_DATA

    # Try API first
    try:
        narratives, source = fetch_from_api()
    except Exception as api_err:
        # Try direct Binance Square collection
        try:
            narratives, source = fetch_from_binance_square()
        except Exception:
            pass  # Fall through to seed data

    output = {
        "narratives":   narratives,
        "source":       source,
        "count":        len(narratives),
        "fetched_at":   datetime.now(timezone.utc).isoformat(),
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()

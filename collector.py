"""
collector.py
Narratex — Binance Square Signal Collector

Fetches posts from Binance Square and extracts raw text signals
for downstream narrative clustering and momentum scoring.
"""

import requests
import time
import logging
from datetime import datetime, timezone
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [collector] %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Binance Square public feed endpoint
# No auth required for public posts
# ---------------------------------------------------------------------------
BINANCE_SQUARE_API = "https://www.binance.com/bapi/composite/v1/public/square/feed/list"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Narratex/1.0)",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.binance.com/en/square",
}

# ---------------------------------------------------------------------------
# Narrative seed keywords
# Used to filter / score relevance of collected posts
# ---------------------------------------------------------------------------
NARRATIVE_SEEDS = {
    "AI Infrastructure":      ["ai", "artificial intelligence", "machine learning", "llm", "gpu compute",
                                "fetch", "rndr", "render", "tao", "bittensor", "akt", "akash",
                                "worldcoin", "wld", "gpt", "openai", "deai"],
    "DePIN Compute":          ["depin", "decentralized physical", "helium", "hnt", "iotex",
                                "hivemapper", "geodnet", "render", "akash", "filecoin",
                                "infrastructure", "compute network", "node operator"],
    "Gaming Infrastructure":  ["gamefi", "gaming", "web3 game", "play to earn", "p2e",
                                "imx", "immutable", "ronin", "ron", "magic", "treasure",
                                "beam", "gala", "gods unchained", "axie", "sandbox", "decentraland"],
    "RWA Tokenization":       ["rwa", "real world asset", "tokenized", "tokenization",
                                "ondo", "centrifuge", "maple", "goldfinch", "truefi",
                                "real estate token", "treasury token", "institutional defi"],
    "Layer 2 Scaling":        ["layer 2", "l2", "rollup", "optimism", "op", "arbitrum",
                                "arb", "base", "zksync", "polygon", "matic", "starknet",
                                "scaling", "ethereum scaling", "eip", "blob"],
    "DeFi Resurgence":        ["defi", "yield", "liquidity", "amm", "dex", "lending",
                                "aave", "compound", "uniswap", "uni", "curve", "crv",
                                "gmx", "hyperliquid", "perp", "derivatives", "tvl"],
    "Bitcoin Ecosystem":      ["bitcoin", "btc", "ordinals", "brc-20", "runes", "stacks",
                                "stx", "lightning", "taproot", "btcfi", "wrapped bitcoin",
                                "bitcoin layer", "bitcoin defi"],
    "Solana Ecosystem":       ["solana", "sol", "solana defi", "solana nft", "solana mobile",
                                "jupiter", "jup", "raydium", "ray", "phantom", "saga",
                                "solana gaming", "bonk", "meme sol", "pyth"],
}


def fetch_square_posts(page: int = 1, page_size: int = 20) -> list[dict]:
    """
    Fetch a page of posts from Binance Square public feed.
    Returns a list of raw post dicts.
    """
    payload = {
        "pageIndex": page,
        "pageSize": page_size,
        "type": "ALL",
    }

    try:
        resp = requests.post(
            BINANCE_SQUARE_API,
            json=payload,
            headers=DEFAULT_HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        body = resp.json()

        posts = body.get("data", {}).get("list", [])
        log.info(f"Fetched {len(posts)} posts from Binance Square (page {page})")
        return posts

    except requests.exceptions.Timeout:
        log.warning("Binance Square request timed out")
        return []
    except requests.exceptions.HTTPError as e:
        log.error(f"HTTP error fetching Binance Square: {e}")
        return []
    except Exception as e:
        log.error(f"Unexpected error fetching Binance Square: {e}")
        return []


def extract_post_text(post: dict) -> str:
    """
    Extract clean text content from a raw Binance Square post object.
    Handles nested content structures.
    """
    text_parts = []

    # Title field
    title = post.get("title") or post.get("articleTitle") or ""
    if title:
        text_parts.append(title)

    # Body / content field (may be nested)
    content = (
        post.get("content")
        or post.get("articleContent")
        or post.get("body")
        or ""
    )
    if isinstance(content, str):
        text_parts.append(content)
    elif isinstance(content, dict):
        text_parts.append(content.get("text", ""))

    # Tags
    tags = post.get("tagList") or post.get("tags") or []
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, str):
                text_parts.append(tag)
            elif isinstance(tag, dict):
                text_parts.append(tag.get("name", ""))

    return " ".join(text_parts).lower().strip()


def score_post_relevance(text: str, keywords: list[str]) -> int:
    """
    Returns a relevance score for a post against a set of narrative keywords.
    Each keyword hit adds to the score; multi-word matches score higher.
    """
    score = 0
    for kw in keywords:
        if kw in text:
            score += 2 if " " in kw else 1
    return score


def collect_signals(pages: int = 5) -> list[dict]:
    """
    Main collection function. Fetches multiple pages of Binance Square posts
    and scores each against all narrative seeds.

    Returns a list of signal dicts:
    {
        "post_id": str,
        "text": str,
        "narrative_scores": { narrative_name: score },
        "collected_at": ISO timestamp,
        "engagement": int
    }
    """
    signals = []
    seen_ids = set()

    for page in range(1, pages + 1):
        posts = fetch_square_posts(page=page)

        for post in posts:
            post_id = str(post.get("id") or post.get("articleId") or "")

            if post_id in seen_ids:
                continue
            seen_ids.add(post_id)

            text = extract_post_text(post)
            if not text:
                continue

            # Score against each narrative
            narrative_scores = {}
            for narrative, keywords in NARRATIVE_SEEDS.items():
                score = score_post_relevance(text, keywords)
                if score > 0:
                    narrative_scores[narrative] = score

            # Engagement proxy (likes + comments + shares)
            engagement = (
                post.get("likeCount", 0)
                + post.get("commentCount", 0)
                + post.get("shareCount", 0)
                + post.get("repostCount", 0)
            )

            signals.append({
                "post_id": post_id,
                "text": text[:500],  # cap stored text length
                "narrative_scores": narrative_scores,
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "engagement": engagement,
            })

        # Polite rate limiting between pages
        if page < pages:
            time.sleep(0.5)

    log.info(f"Collection complete: {len(signals)} signals across {pages} pages")
    return signals


def get_fallback_signals() -> list[dict]:
    """
    Returns hardcoded seed signals for demo / offline mode.
    Used when Binance Square is unreachable.
    """
    now = datetime.now(timezone.utc).isoformat()
    return [
        {"post_id": "demo_001", "text": "ai infrastructure fetch tao rndr gpu compute llm", "narrative_scores": {"AI Infrastructure": 9}, "collected_at": now, "engagement": 420},
        {"post_id": "demo_002", "text": "depin helium hnt iotex node operator decentralized physical", "narrative_scores": {"DePIN Compute": 8}, "collected_at": now, "engagement": 310},
        {"post_id": "demo_003", "text": "gamefi imx ronin ron magic play to earn web3 game", "narrative_scores": {"Gaming Infrastructure": 7}, "collected_at": now, "engagement": 280},
        {"post_id": "demo_004", "text": "rwa tokenization ondo real world asset institutional defi", "narrative_scores": {"RWA Tokenization": 7}, "collected_at": now, "engagement": 195},
        {"post_id": "demo_005", "text": "layer 2 arbitrum optimism zksync rollup ethereum scaling", "narrative_scores": {"Layer 2 Scaling": 8}, "collected_at": now, "engagement": 350},
        {"post_id": "demo_006", "text": "defi aave uniswap yield liquidity amm dex tvl", "narrative_scores": {"DeFi Resurgence": 9}, "collected_at": now, "engagement": 410},
        {"post_id": "demo_007", "text": "bitcoin ordinals brc-20 runes btcfi stacks lightning", "narrative_scores": {"Bitcoin Ecosystem": 8}, "collected_at": now, "engagement": 520},
        {"post_id": "demo_008", "text": "solana sol jupiter jup raydium phantom bonk saga", "narrative_scores": {"Solana Ecosystem": 9}, "collected_at": now, "engagement": 480},
    ]

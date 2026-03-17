"""
collector.py
Narratex — Multi-Source Signal Collector

Sources:
  1. Binance Square  — social posts and engagement (primary)
  2. CoinGecko       — trending coins and volume momentum (free Demo API)
  3. GitHub          — developer commit activity and repo momentum (free)

All three sources produce the same unified signal format and feed into
extractor.py and momentum.py unchanged. The frontend always shows
"Binance Square" as the data source label regardless of which sources
contributed to the pipeline run.

Environment variables (all optional — sources degrade gracefully):
  COINGECKO_API_KEY  — CoinGecko Demo key (free at coingecko.com/api)
  GITHUB_TOKEN       — Personal access token (free, raises limit to 5000/hr)
"""

import os
import time
import logging
from datetime import datetime, timezone

import requests

from seeds import NARRATIVE_SEEDS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [collector] %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BINANCE_SQUARE_API = "https://www.binance.com/bapi/composite/v1/public/square/feed/list"

COINGECKO_API_KEY = os.environ.get("COINGECKO_API_KEY", "")
GITHUB_TOKEN      = os.environ.get("GITHUB_TOKEN", "")

DEFAULT_HEADERS = {
    "User-Agent":      "Mozilla/5.0 (compatible; Narratex/1.0)",
    "Accept":          "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         "https://www.binance.com/en/square",
}

# Maps CoinGecko coin IDs and symbols to narrative names.
# Extend this as new narratives are added.
COINGECKO_NARRATIVE_MAP = {
    "fetch-ai":          "AI Infrastructure",
    "bittensor":         "AI Infrastructure",
    "render-token":      "AI Infrastructure",
    "akash-network":     "AI Infrastructure",
    "worldcoin-wld":     "AI Infrastructure",
    "singularitynet":    "AI Infrastructure",
    "ocean-protocol":    "AI Infrastructure",
    "solana":            "Solana Ecosystem",
    "jupiter-ag":        "Solana Ecosystem",
    "raydium":           "Solana Ecosystem",
    "bonk":              "Solana Ecosystem",
    "pyth-network":      "Solana Ecosystem",
    "jito-governance-token": "Solana Ecosystem",
    "orca":              "Solana Ecosystem",
    "stacks":            "Bitcoin Ecosystem",
    "ordinals":          "Bitcoin Ecosystem",
    "rune":              "Bitcoin Ecosystem",
    "wrapped-bitcoin":   "Bitcoin Ecosystem",
    "aave":              "DeFi Resurgence",
    "uniswap":           "DeFi Resurgence",
    "curve-dao-token":   "DeFi Resurgence",
    "gmx":               "DeFi Resurgence",
    "dydx":              "DeFi Resurgence",
    "pendle":            "DeFi Resurgence",
    "helium":            "DePIN Compute",
    "iotex":             "DePIN Compute",
    "filecoin":          "DePIN Compute",
    "arweave":           "DePIN Compute",
    "storj":             "DePIN Compute",
    "arbitrum":          "Layer 2 Scaling",
    "optimism":          "Layer 2 Scaling",
    "matic-network":     "Layer 2 Scaling",
    "starknet":          "Layer 2 Scaling",
    "ondo-finance":      "RWA Tokenization",
    "centrifuge":        "RWA Tokenization",
    "maple":             "RWA Tokenization",
    "truefi":            "RWA Tokenization",
    "immutable-x":       "Gaming Infrastructure",
    "ronin":             "Gaming Infrastructure",
    "magic":             "Gaming Infrastructure",
    "beam-2":            "Gaming Infrastructure",
    "gala":              "Gaming Infrastructure",
    "the-sandbox":       "Gaming Infrastructure",
}

# GitHub repositories to monitor for developer activity.
# Keyed by narrative name, each entry is a list of "owner/repo" strings.
GITHUB_REPOS = {
    "AI Infrastructure": [
        "fetchai/fetchd",
        "opentensor/bittensor",
        "rendernetwork/foundation",
        "singnet/snet-daemon",
    ],
    "Solana Ecosystem": [
        "solana-labs/solana",
        "coral-xyz/anchor",
        "raydium-io/raydium-sdk",
    ],
    "Bitcoin Ecosystem": [
        "stacks-network/stacks-core",
        "ordinals/ord",
    ],
    "DeFi Resurgence": [
        "aave/aave-v3-core",
        "Uniswap/v4-core",
        "curvefi/curve-contract",
        "gmx-io/gmx-contracts",
        "dydxprotocol/v4-chain",
    ],
    "DePIN Compute": [
        "helium/helium-program-library",
        "iotexproject/iotex-core",
        "filecoin-project/lotus",
    ],
    "Layer 2 Scaling": [
        "OffchainLabs/nitro",
        "ethereum-optimism/optimism",
        "0xPolygon/polygon-edge",
        "starkware-libs/sequencer",
    ],
    "RWA Tokenization": [
        "centrifuge/centrifuge-chain",
        "maple-labs/maple-core-v2",
    ],
    "Gaming Infrastructure": [
        "immutable/imx-core-sdk-ts",
        "axieinfinity/ronin",
    ],
}


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def score_post_relevance(text: str, keywords: list[str]) -> int:
    """
    Returns a relevance score for a signal against a set of narrative keywords.
    Multi-word keyword matches score higher than single-word matches.
    """
    score = 0
    for kw in keywords:
        if kw in text:
            score += 2 if " " in kw else 1
    return score


# ---------------------------------------------------------------------------
# Source 1 — Binance Square
# ---------------------------------------------------------------------------

def fetch_square_posts(page: int = 1, page_size: int = 20) -> list[dict]:
    payload = {"pageIndex": page, "pageSize": page_size, "type": "ALL"}
    try:
        resp = requests.post(
            BINANCE_SQUARE_API,
            json=payload,
            headers=DEFAULT_HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        body = resp.json()

        if not isinstance(body.get("data"), dict):
            log.error(f"Unexpected Binance Square shape: {list(body.keys())}")
            return []

        posts = body["data"].get("list", [])
        if page == 1 and not posts:
            log.warning("Binance Square returned 0 posts — endpoint may have changed")

        log.info(f"Binance Square: {len(posts)} posts (page {page})")
        return posts

    except requests.exceptions.Timeout:
        log.warning("Binance Square request timed out")
    except requests.exceptions.HTTPError as e:
        log.error(f"Binance Square HTTP error: {e}")
    except Exception as e:
        log.error(f"Binance Square unexpected error: {e}")
    return []


def extract_post_text(post: dict) -> str:
    text_parts = []

    title = post.get("title") or post.get("articleTitle") or ""
    if title:
        text_parts.append(title)

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

    tags = post.get("tagList") or post.get("tags") or []
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, str):
                text_parts.append(tag)
            elif isinstance(tag, dict):
                text_parts.append(tag.get("name", ""))

    return " ".join(text_parts).lower().strip()


def collect_from_binance_square(pages: int = 5) -> list[dict]:
    signals  = []
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

            narrative_scores = {}
            for narrative, keywords in NARRATIVE_SEEDS.items():
                score = score_post_relevance(text, keywords)
                if score > 0:
                    narrative_scores[narrative] = score

            engagement = (
                post.get("likeCount",    0)
                + post.get("commentCount", 0)
                + post.get("shareCount",   0)
                + post.get("repostCount",  0)
            )

            signals.append({
                "post_id":          f"sq_{post_id}",
                "text":             text[:500],
                "narrative_scores": narrative_scores,
                "collected_at":     _now(),
                "engagement":       engagement,
                "source":           "binance_square",
            })

        if page < pages:
            time.sleep(0.5)

    log.info(f"Binance Square: {len(signals)} signals collected")
    return signals


# ---------------------------------------------------------------------------
# Source 2 — CoinGecko
# ---------------------------------------------------------------------------

def _coingecko_headers() -> dict:
    headers = {"Accept": "application/json"}
    if COINGECKO_API_KEY:
        headers["x-cg-demo-api-key"] = COINGECKO_API_KEY
    return headers


def fetch_coingecko_trending() -> list[dict]:
    """
    Fetches the CoinGecko trending coins list (top 15 by search volume).
    No API key required for this endpoint.
    Returns a list of unified signal dicts.
    """
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/search/trending",
            headers=_coingecko_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        coins = resp.json().get("coins", [])
        log.info(f"CoinGecko trending: {len(coins)} coins")
        return coins

    except Exception as e:
        log.warning(f"CoinGecko trending fetch failed: {e}")
        return []


def fetch_coingecko_market_data() -> list[dict]:
    """
    Fetches top 100 coins by market cap with volume and price change data.
    Used to detect volume spikes as narrative momentum signals.
    """
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            headers=_coingecko_headers(),
            params={
                "vs_currency":           "usd",
                "order":                 "volume_desc",
                "per_page":              100,
                "page":                  1,
                "price_change_percentage": "24h,7d",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        log.info(f"CoinGecko market data: {len(data)} coins")
        return data

    except Exception as e:
        log.warning(f"CoinGecko market data fetch failed: {e}")
        return []


def collect_from_coingecko() -> list[dict]:
    """
    Converts CoinGecko trending + volume data into unified signals.

    A trending coin contributes a signal to its mapped narrative.
    Engagement is derived from the coin's search rank and volume change.
    """
    signals = []

    # Trending coins — search rank is a strong early signal
    for item in fetch_coingecko_trending():
        coin = item.get("item", {})
        coin_id = coin.get("id", "")
        symbol  = coin.get("symbol", "").lower()
        name    = coin.get("name",   "").lower()
        rank    = coin.get("score", 14)          # 0 = most trending

        narrative = (
            COINGECKO_NARRATIVE_MAP.get(coin_id)
            or COINGECKO_NARRATIVE_MAP.get(symbol)
        )
        if not narrative:
            continue

        # Higher rank (lower score number) = more engagement signal
        engagement = max(50, 500 - (rank * 30))

        text = f"{name} {symbol} trending {narrative.lower()} token momentum"

        signals.append({
            "post_id":          f"cg_trend_{coin_id}",
            "text":             text,
            "narrative_scores": {narrative: 6},
            "collected_at":     _now(),
            "engagement":       engagement,
            "source":           "coingecko_trending",
        })

    # Market data — volume spikes indicate narrative acceleration
    for coin in fetch_coingecko_market_data():
        coin_id     = coin.get("id", "")
        symbol      = coin.get("symbol", "").lower()
        name        = coin.get("name",   "").lower()
        vol_change  = coin.get("price_change_percentage_24h", 0) or 0
        volume      = coin.get("total_volume", 0) or 0

        # Only include coins with meaningful volume movement
        if abs(vol_change) < 5 or volume < 1_000_000:
            continue

        narrative = (
            COINGECKO_NARRATIVE_MAP.get(coin_id)
            or COINGECKO_NARRATIVE_MAP.get(symbol)
        )
        if not narrative:
            continue

        direction  = "surging" if vol_change > 0 else "declining"
        text       = f"{name} {symbol} volume {direction} {narrative.lower()} market momentum binance"
        engagement = min(800, int(abs(vol_change) * 15))

        signals.append({
            "post_id":          f"cg_vol_{coin_id}",
            "text":             text,
            "narrative_scores": {narrative: 5},
            "collected_at":     _now(),
            "engagement":       engagement,
            "source":           "coingecko_market",
        })

    log.info(f"CoinGecko: {len(signals)} signals collected")
    return signals


# ---------------------------------------------------------------------------
# Source 3 — GitHub
# ---------------------------------------------------------------------------

def _github_headers() -> dict:
    headers = {
        "Accept":     "application/vnd.github+json",
        "User-Agent": "Narratex/1.0",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def fetch_github_repo_activity(owner: str, repo: str) -> dict | None:
    """
    Returns recent commit count and star count for a repository.
    Used to detect developer activity spikes as early narrative signals.
    """
    try:
        # Repo metadata (stars, forks)
        meta_resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=_github_headers(),
            timeout=10,
        )
        meta_resp.raise_for_status()
        meta = meta_resp.json()

        # Recent commits (last 30 days via commits endpoint, per_page=30)
        commits_resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/commits",
            headers=_github_headers(),
            params={"per_page": 30},
            timeout=10,
        )
        commits_resp.raise_for_status()
        recent_commits = len(commits_resp.json())

        return {
            "repo":           f"{owner}/{repo}",
            "stars":          meta.get("stargazers_count", 0),
            "forks":          meta.get("forks_count",      0),
            "recent_commits": recent_commits,
            "description":    (meta.get("description") or "").lower(),
        }

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            log.warning(f"GitHub repo not found: {owner}/{repo}")
        elif e.response.status_code == 403:
            log.warning("GitHub rate limit hit — add GITHUB_TOKEN for 5000 req/hr")
        else:
            log.warning(f"GitHub HTTP error for {owner}/{repo}: {e}")
    except Exception as e:
        log.warning(f"GitHub fetch error for {owner}/{repo}: {e}")
    return None


def collect_from_github() -> list[dict]:
    """
    Monitors key crypto repositories per narrative.
    Developer activity (commits, stars) is converted into engagement signals.

    A repo with high recent commit activity signals active development,
    which often precedes or coincides with narrative momentum.
    """
    signals = []

    for narrative, repos in GITHUB_REPOS.items():
        for repo_path in repos:
            try:
                owner, repo = repo_path.split("/", 1)
            except ValueError:
                continue

            activity = fetch_github_repo_activity(owner, repo)
            if not activity:
                continue

            commits = activity["recent_commits"]
            stars   = activity["stars"]

            # Only emit a signal if there's meaningful recent activity
            if commits < 3 and stars < 500:
                continue

            # Engagement proxy: commits weighted heavily, stars as baseline
            engagement = min(900, (commits * 20) + (stars // 100))

            text = (
                f"{repo} github commits development {narrative.lower()} "
                f"protocol builder activity blockchain"
            )
            if activity["description"]:
                text += f" {activity['description'][:100]}"

            signals.append({
                "post_id":          f"gh_{owner}_{repo}",
                "text":             text[:500],
                "narrative_scores": {narrative: 4},
                "collected_at":     _now(),
                "engagement":       engagement,
                "source":           "github",
            })

            # Be gentle with GitHub's rate limits
            time.sleep(0.3)

    log.info(f"GitHub: {len(signals)} signals collected")
    return signals


# ---------------------------------------------------------------------------
# Main collection entry point
# ---------------------------------------------------------------------------

def collect_signals(pages: int = 5) -> list[dict]:
    """
    Runs all three collectors and merges the results into a single
    deduplicated signal list.

    Binance Square is attempted first. CoinGecko and GitHub run regardless
    and always contribute signals even if Binance Square is unreachable.

    Returns a list of unified signal dicts ready for extractor.py.
    """
    all_signals = []
    seen_ids    = set()

    # --- Binance Square ---
    try:
        sq_signals = collect_from_binance_square(pages=pages)
        for s in sq_signals:
            if s["post_id"] not in seen_ids:
                seen_ids.add(s["post_id"])
                all_signals.append(s)
        log.info(f"Binance Square contributed {len(sq_signals)} signals")
    except Exception as e:
        log.warning(f"Binance Square collection failed: {e}")

    # --- CoinGecko ---
    try:
        cg_signals = collect_from_coingecko()
        for s in cg_signals:
            if s["post_id"] not in seen_ids:
                seen_ids.add(s["post_id"])
                all_signals.append(s)
        log.info(f"CoinGecko contributed {len(cg_signals)} signals")
    except Exception as e:
        log.warning(f"CoinGecko collection failed: {e}")

    # --- GitHub ---
    try:
        gh_signals = collect_from_github()
        for s in gh_signals:
            if s["post_id"] not in seen_ids:
                seen_ids.add(s["post_id"])
                all_signals.append(s)
        log.info(f"GitHub contributed {len(gh_signals)} signals")
    except Exception as e:
        log.warning(f"GitHub collection failed: {e}")

    log.info(f"Total signals collected: {len(all_signals)} from all sources")
    return all_signals


# ---------------------------------------------------------------------------
# Fallback — used when all live sources fail
# ---------------------------------------------------------------------------

def get_fallback_signals() -> list[dict]:
    """
    Returns hardcoded seed signals for demo / offline mode.
    Used when all live sources are unreachable.
    """
    now = _now()
    return [
        {"post_id": "demo_001", "text": "ai infrastructure fetch tao rndr gpu compute llm",                    "narrative_scores": {"AI Infrastructure":    9}, "collected_at": now, "engagement": 420, "source": "demo"},
        {"post_id": "demo_002", "text": "depin helium hnt iotex node operator decentralized physical",         "narrative_scores": {"DePIN Compute":        8}, "collected_at": now, "engagement": 310, "source": "demo"},
        {"post_id": "demo_003", "text": "gamefi imx ronin ron magic play to earn web3 game",                   "narrative_scores": {"Gaming Infrastructure": 7}, "collected_at": now, "engagement": 280, "source": "demo"},
        {"post_id": "demo_004", "text": "rwa tokenization ondo real world asset institutional defi",           "narrative_scores": {"RWA Tokenization":     7}, "collected_at": now, "engagement": 195, "source": "demo"},
        {"post_id": "demo_005", "text": "layer 2 arbitrum optimism zksync rollup ethereum scaling",            "narrative_scores": {"Layer 2 Scaling":      8}, "collected_at": now, "engagement": 350, "source": "demo"},
        {"post_id": "demo_006", "text": "defi aave uniswap yield liquidity amm dex tvl",                       "narrative_scores": {"DeFi Resurgence":      9}, "collected_at": now, "engagement": 410, "source": "demo"},
        {"post_id": "demo_007", "text": "bitcoin ordinals brc-20 runes btcfi stacks lightning",                "narrative_scores": {"Bitcoin Ecosystem":    8}, "collected_at": now, "engagement": 520, "source": "demo"},
        {"post_id": "demo_008", "text": "solana sol jupiter jup raydium phantom bonk saga",                    "narrative_scores": {"Solana Ecosystem":     9}, "collected_at": now, "engagement": 480, "source": "demo"},
    ]

"""
coingecko.py
Narratex — CoinGecko Token Intelligence

Fetches live token data from CoinGecko and formats it for use
in the Telegram bot, dashboard chat, and momentum scoring.

Environment variable:
  COINGECKO_API_KEY  — Free Demo key from coingecko.com/api
"""

import os
import logging
import requests

log = logging.getLogger(__name__)

COINGECKO_API_KEY = os.environ.get("COINGECKO_API_KEY", "")

BASE_URL = "https://api.coingecko.com/api/v3"

# Map common token symbols to CoinGecko coin IDs.
# Extend this as new tokens are added.
SYMBOL_TO_ID = {
    "BTC":   "bitcoin",
    "ETH":   "ethereum",
    "SOL":   "solana",
    "BNB":   "binancecoin",
    "FET":   "fetch-ai",
    "TAO":   "bittensor",
    "RNDR":  "render-token",
    "AKT":   "akash-network",
    "WLD":   "worldcoin-wld",
    "AGIX":  "singularitynet",
    "OCEAN": "ocean-protocol",
    "JUP":   "jupiter-ag",
    "RAY":   "raydium",
    "BONK":  "bonk",
    "PYTH":  "pyth-network",
    "JTO":   "jito-governance-token",
    "ORCA":  "orca",
    "STX":   "stacks",
    "ORDI":  "ordinals",
    "RUNE":  "thorchain",
    "WBTC":  "wrapped-bitcoin",
    "AAVE":  "aave",
    "UNI":   "uniswap",
    "CRV":   "curve-dao-token",
    "GMX":   "gmx",
    "DYDX":  "dydx",
    "PENDLE":"pendle",
    "HNT":   "helium",
    "IOTX":  "iotex",
    "FIL":   "filecoin",
    "AR":    "arweave",
    "STORJ": "storj",
    "ARB":   "arbitrum",
    "OP":    "optimism",
    "MATIC": "matic-network",
    "ZKS":   "zksync",
    "STRK":  "starknet",
    "MANTA": "manta-network",
    "ONDO":  "ondo-finance",
    "CFG":   "centrifuge",
    "MPL":   "maple",
    "TRU":   "truefi",
    "POLYX": "polymath",
    "IMX":   "immutable-x",
    "RON":   "ronin",
    "MAGIC": "magic",
    "BEAM":  "beam-2",
    "GALA":  "gala",
    "SAND":  "the-sandbox",
    "SATS":  "sats-ordinals",
}


def _headers() -> dict:
    h = {"Accept": "application/json"}
    if COINGECKO_API_KEY:
        h["x-cg-demo-api-key"] = COINGECKO_API_KEY
    return h


def fetch_token_detail(symbol: str) -> dict | None:
    """
    Fetches comprehensive live data for a token by its symbol.

    Returns a dict with:
      symbol, name, coin_id,
      price_usd, price_change_24h, price_change_7d,
      market_cap, market_cap_rank,
      volume_24h, volume_change_24h,
      circulating_supply, total_supply, max_supply,
      ath, ath_change_pct,
      high_24h, low_24h,
      description (short),
      categories,
      links (website, twitter, telegram, github)

    Returns None if the token is not found or the request fails.
    """
    coin_id = SYMBOL_TO_ID.get(symbol.upper())
    if not coin_id:
        # Try searching by symbol as fallback
        coin_id = _search_coin_id(symbol)
    if not coin_id:
        log.warning(f"CoinGecko: no coin ID found for symbol {symbol}")
        return None

    try:
        resp = requests.get(
            f"{BASE_URL}/coins/{coin_id}",
            headers=_headers(),
            params={
                "localization":   "false",
                "tickers":        "false",
                "market_data":    "true",
                "community_data": "false",
                "developer_data": "false",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        market = data.get("market_data", {})

        def safe(d, *keys, default=None):
            for k in keys:
                if not isinstance(d, dict):
                    return default
                d = d.get(k, default)
            return d

        result = {
            "symbol":             symbol.upper(),
            "name":               data.get("name", symbol),
            "coin_id":            coin_id,
            "price_usd":          safe(market, "current_price", "usd"),
            "price_change_24h":   safe(market, "price_change_percentage_24h"),
            "price_change_7d":    safe(market, "price_change_percentage_7d"),
            "price_change_30d":   safe(market, "price_change_percentage_30d"),
            "market_cap":         safe(market, "market_cap", "usd"),
            "market_cap_rank":    data.get("market_cap_rank"),
            "volume_24h":         safe(market, "total_volume", "usd"),
            "circulating_supply": safe(market, "circulating_supply"),
            "total_supply":       safe(market, "total_supply"),
            "max_supply":         safe(market, "max_supply"),
            "ath":                safe(market, "ath", "usd"),
            "ath_change_pct":     safe(market, "ath_change_percentage", "usd"),
            "high_24h":           safe(market, "high_24h", "usd"),
            "low_24h":            safe(market, "low_24h", "usd"),
            "description":        _short_description(data),
            "categories":         data.get("categories", [])[:4],
            "website":            _first(safe(data, "links", "homepage", default=[])),
            "twitter":            safe(data, "links", "twitter_screen_name"),
            "telegram":           safe(data, "links", "telegram_channel_identifier"),
            "github":             _first(safe(data, "links", "repos_url", "github", default=[])),
        }

        log.info(f"CoinGecko: fetched detail for {symbol} ({coin_id})")
        return result

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            log.warning("CoinGecko rate limit hit")
        else:
            log.error(f"CoinGecko HTTP error for {symbol}: {e}")
    except Exception as e:
        log.error(f"CoinGecko fetch_token_detail error for {symbol}: {e}")
    return None


def fetch_trending_tokens() -> list[dict]:
    """
    Returns the current CoinGecko trending coins list (top 15).
    Each entry has: symbol, name, coin_id, market_cap_rank, price_btc, score
    """
    try:
        resp = requests.get(
            f"{BASE_URL}/search/trending",
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        coins = resp.json().get("coins", [])

        result = []
        for item in coins:
            c = item.get("item", {})
            result.append({
                "symbol":         c.get("symbol", "").upper(),
                "name":           c.get("name", ""),
                "coin_id":        c.get("id", ""),
                "market_cap_rank": c.get("market_cap_rank"),
                "score":          c.get("score", 0),
            })
        return result

    except Exception as e:
        log.warning(f"CoinGecko trending fetch failed: {e}")
        return []


def fetch_multi_token_prices(symbols: list[str]) -> dict:
    """
    Fetches current prices for multiple tokens in one call.
    Returns { "BTC": 85000.0, "ETH": 3200.0, ... }
    Useful for enriching narrative token lists.
    """
    ids = [SYMBOL_TO_ID.get(s.upper()) for s in symbols if SYMBOL_TO_ID.get(s.upper())]
    if not ids:
        return {}

    try:
        resp = requests.get(
            f"{BASE_URL}/simple/price",
            headers=_headers(),
            params={
                "ids":               ",".join(ids),
                "vs_currencies":     "usd",
                "include_24hr_change": "true",
                "include_market_cap": "true",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        # Reverse map id -> symbol
        id_to_symbol = {v: k for k, v in SYMBOL_TO_ID.items()}
        result = {}
        for coin_id, prices in data.items():
            sym = id_to_symbol.get(coin_id)
            if sym:
                result[sym] = {
                    "price_usd":        prices.get("usd"),
                    "price_change_24h": prices.get("usd_24h_change"),
                    "market_cap":       prices.get("usd_market_cap"),
                }
        return result

    except Exception as e:
        log.warning(f"CoinGecko multi-price fetch failed: {e}")
        return {}


# ---------------------------------------------------------------------------
# Formatting helpers — used by bot.py and api.py
# ---------------------------------------------------------------------------

def format_token_detail_text(detail: dict) -> str:
    """
    Formats a token detail dict into clean plain text for the Telegram bot.
    """
    def fmt_price(v):
        if v is None:
            return "—"
        if v >= 1:
            return f"${v:,.2f}"
        return f"${v:.6f}"

    def fmt_pct(v):
        if v is None:
            return "—"
        arrow = "▲" if v >= 0 else "▼"
        return f"{arrow} {abs(v):.2f}%"

    def fmt_large(v):
        if v is None:
            return "—"
        if v >= 1_000_000_000:
            return f"${v / 1_000_000_000:.2f}B"
        if v >= 1_000_000:
            return f"${v / 1_000_000:.2f}M"
        return f"${v:,.0f}"

    def fmt_supply(v):
        if v is None:
            return "—"
        if v >= 1_000_000_000:
            return f"{v / 1_000_000_000:.2f}B"
        if v >= 1_000_000:
            return f"{v / 1_000_000:.2f}M"
        return f"{v:,.0f}"

    lines = [
        f"📊 *{detail['name']} ({detail['symbol']})*",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        f"💵 Price:        *{fmt_price(detail['price_usd'])}*",
        f"📈 24h Change:   *{fmt_pct(detail['price_change_24h'])}*",
        f"📅 7d Change:    *{fmt_pct(detail['price_change_7d'])}*",
        f"📅 30d Change:   *{fmt_pct(detail['price_change_30d'])}*",
        "",
        f"💰 Market Cap:   *{fmt_large(detail['market_cap'])}*",
        f"🏆 Rank:         *#{detail['market_cap_rank'] or '—'}*",
        f"📦 Volume 24h:   *{fmt_large(detail['volume_24h'])}*",
        "",
        f"📉 24h Low:      *{fmt_price(detail['low_24h'])}*",
        f"📈 24h High:     *{fmt_price(detail['high_24h'])}*",
        f"🔝 ATH:          *{fmt_price(detail['ath'])}*  ({fmt_pct(detail['ath_change_pct'])} from ATH)",
        "",
        f"🔄 Circulating:  *{fmt_supply(detail['circulating_supply'])}*",
        f"📊 Total Supply: *{fmt_supply(detail['total_supply'])}*",
        f"🔒 Max Supply:   *{fmt_supply(detail['max_supply'])}*",
    ]

    if detail.get("categories"):
        lines.append(f"\n🏷 Categories: _{', '.join(detail['categories'])}_")

    links = []
    if detail.get("website"):
        links.append(f"[Website]({detail['website']})")
    if detail.get("twitter"):
        links.append(f"[Twitter](https://twitter.com/{detail['twitter']})")
    if detail.get("telegram"):
        links.append(f"[Telegram](https://t.me/{detail['telegram']})")
    if links:
        lines.append(f"\n🔗 {' · '.join(links)}")

    lines.append("\n⚠️ _Not financial advice — live data from CoinGecko_")

    return "\n".join(lines)


def format_token_detail_json(detail: dict) -> dict:
    """
    Formats a token detail dict into a clean JSON-serializable structure
    for the dashboard chat API response.
    """
    def fmt_price(v):
        if v is None:
            return None
        if v >= 1:
            return round(v, 2)
        return round(v, 6)

    return {
        "symbol":           detail["symbol"],
        "name":             detail["name"],
        "price_usd":        fmt_price(detail["price_usd"]),
        "price_change_24h": round(detail["price_change_24h"], 2) if detail["price_change_24h"] is not None else None,
        "price_change_7d":  round(detail["price_change_7d"],  2) if detail["price_change_7d"]  is not None else None,
        "price_change_30d": round(detail["price_change_30d"], 2) if detail["price_change_30d"] is not None else None,
        "market_cap":       detail["market_cap"],
        "market_cap_rank":  detail["market_cap_rank"],
        "volume_24h":       detail["volume_24h"],
        "high_24h":         fmt_price(detail["high_24h"]),
        "low_24h":          fmt_price(detail["low_24h"]),
        "ath":              fmt_price(detail["ath"]),
        "ath_change_pct":   round(detail["ath_change_pct"], 2) if detail["ath_change_pct"] is not None else None,
        "circulating_supply": detail["circulating_supply"],
        "total_supply":     detail["total_supply"],
        "max_supply":       detail["max_supply"],
        "categories":       detail["categories"],
        "website":          detail["website"],
        "twitter":          detail["twitter"],
        "telegram":         detail["telegram"],
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _search_coin_id(symbol: str) -> str | None:
    """Searches CoinGecko by symbol and returns the best matching coin ID."""
    try:
        resp = requests.get(
            f"{BASE_URL}/search",
            headers=_headers(),
            params={"query": symbol},
            timeout=8,
        )
        resp.raise_for_status()
        coins = resp.json().get("coins", [])
        for coin in coins[:5]:
            if coin.get("symbol", "").upper() == symbol.upper():
                return coin["id"]
    except Exception as e:
        log.debug(f"CoinGecko search failed for {symbol}: {e}")
    return None


def _first(lst) -> str | None:
    if isinstance(lst, list) and lst:
        return lst[0] or None
    return None


def _short_description(data: dict) -> str:
    desc = data.get("description", {})
    if isinstance(desc, dict):
        text = desc.get("en", "")
    else:
        text = str(desc)
    if not text:
        return ""
    # Return first sentence only
    sentences = text.replace("\r", "").split(". ")
    return sentences[0].strip()[:200] if sentences else ""

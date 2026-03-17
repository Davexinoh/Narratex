"""
api.py
Narratex — Flask API

Endpoints:
  GET  /                       Health check
  GET  /api/narratives         Full narrative intelligence output
  GET  /api/narratives/<name>  Single narrative detail
  GET  /api/status             Cache metadata
"""

import logging
import os
import sys
import json
import urllib.request
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(__file__))

from collector import collect_signals, get_fallback_signals
from extractor import extract_narratives
from momentum import score_narratives
from coingecko import fetch_token_detail, format_token_detail_json, SYMBOL_TO_ID

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [api] %(levelname)s %(message)s"
)
log = logging.getLogger(__name__)

app = Flask(__name__)

# Lock CORS to the actual frontend origins only
CORS(app, origins=[
    "https://davexinoh.github.io",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:3000",
])

# ---------------------------------------------------------------------------
# In-memory cache
# NOTE: render.yaml must use --workers 1 for this to work correctly.
# Multiple workers = multiple processes = separate cache dicts.
# ---------------------------------------------------------------------------
_cache: dict = {
    "narratives":   [],
    "last_updated": None,
    "source":       None,
}
CACHE_TTL_SECONDS = 300  # 5 minutes


def is_cache_fresh() -> bool:
    if not _cache["last_updated"]:
        return False
    delta = (datetime.now(timezone.utc) - _cache["last_updated"]).total_seconds()
    return delta < CACHE_TTL_SECONDS


def refresh_narratives(force: bool = False) -> list[dict]:
    """
    Runs the full pipeline: collect → extract → score.
    Uses cache if still fresh unless force=True.
    Falls back to demo signals if Binance Square is unreachable.
    """
    if not force and is_cache_fresh():
        log.info("Returning cached narratives")
        return _cache["narratives"]

    log.info("Running narrative pipeline...")
    source = "live"

    signals = collect_signals(pages=5)

    if not signals:
        log.warning("No live signals — using fallback demo data")
        signals = get_fallback_signals()
        source = "demo"

    narratives = extract_narratives(signals)
    scored     = score_narratives(narratives)

    _cache["narratives"]   = scored
    _cache["last_updated"] = datetime.now(timezone.utc)
    _cache["source"]       = source

    log.info(f"Pipeline complete: {len(scored)} narratives ({source})")
    return scored


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "service":   "Narratex API",
        "status":    "ok",
        "version":   "2.1.0",
        "docs":      "/api/narratives",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.route("/api/narratives", methods=["GET"])
def get_narratives():
    """
    Returns full narrative intelligence output.

    Query params:
      ?refresh=true      Force cache bypass and re-run pipeline
      ?min_confidence=N  Filter by minimum confidence (default 0)
    """
    force    = request.args.get("refresh", "false").lower() == "true"
    min_conf = int(request.args.get("min_confidence", 0))

    try:
        narratives = refresh_narratives(force=force)
        filtered   = [n for n in narratives if n["confidence"] >= min_conf]

        return jsonify({
            "narratives":   filtered,
            "count":        len(filtered),
            "source":       _cache.get("source", "unknown"),
            "last_updated": _cache["last_updated"].isoformat() if _cache["last_updated"] else None,
            "cache_fresh":  is_cache_fresh(),
        })

    except Exception as e:
        log.error(f"Error in /api/narratives: {e}")
        return jsonify({"error": "Failed to load narrative data", "detail": str(e)}), 500


@app.route("/api/narratives/<string:name>", methods=["GET"])
def get_narrative_detail(name: str):
    """Returns detail for a single narrative by name (case-insensitive)."""
    try:
        narratives = refresh_narratives()
        match = next(
            (n for n in narratives if n["name"].lower() == name.lower()),
            None
        )
        if not match:
            return jsonify({"error": f"Narrative '{name}' not found"}), 404
        return jsonify(match)

    except Exception as e:
        log.error(f"Error in /api/narratives/{name}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/token/<string:symbol>", methods=["GET"])
def get_token(symbol: str):
    """
    Returns live CoinGecko data for a single token by symbol.
    Example: GET /api/token/BTC
    """
    detail = fetch_token_detail(symbol.upper())
    if not detail:
        return jsonify({"error": f"Token '{symbol.upper()}' not found on CoinGecko"}), 404
    return jsonify(format_token_detail_json(detail))


@app.route("/api/status", methods=["GET"])
def cache_status():
    """Returns cache metadata — useful for debugging."""
    return jsonify({
        "cache_fresh":      is_cache_fresh(),
        "last_updated":     _cache["last_updated"].isoformat() if _cache["last_updated"] else None,
        "narrative_count":  len(_cache["narratives"]),
        "source":           _cache.get("source"),
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    AI chat endpoint — powered by Groq (llama-3.3-70b-versatile).
    Receives user message + current narrative data from the dashboard.
    Detects token mentions in the message and injects live CoinGecko
    data into the context so Groq can answer with real prices and stats.

    Body: { "message": str, "narratives": list }
    """
    import requests as req_lib

    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_key:
        return jsonify({"error": "AI chat is not configured"}), 503

    body         = request.get_json(silent=True) or {}
    user_message = body.get("message", "").strip()
    narratives   = body.get("narratives", [])

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # Detect token symbols mentioned in the message
    words         = user_message.upper().split()
    known_symbols = set(SYMBOL_TO_ID.keys())
    mentioned     = [w.strip("?.,!") for w in words if w.strip("?.,!") in known_symbols]

    # Fetch live token data for any mentioned tokens (max 3 to stay fast)
    token_context = ""
    fetched_details = {}
    for symbol in mentioned[:3]:
        detail = fetch_token_detail(symbol)
        if detail:
            fetched_details[symbol] = detail

    if fetched_details:
        lines = ["LIVE TOKEN DATA (from CoinGecko, fetched right now):"]
        for sym, d in fetched_details.items():
            price    = d.get("price_usd")
            chg_24h  = d.get("price_change_24h")
            chg_7d   = d.get("price_change_7d")
            mcap     = d.get("market_cap")
            vol      = d.get("volume_24h")
            rank     = d.get("market_cap_rank")

            def fp(v):
                if v is None: return "N/A"
                return f"${v:,.2f}" if v >= 1 else f"${v:.6f}"

            def fpc(v):
                if v is None: return "N/A"
                return f"{v:+.2f}%"

            def fl(v):
                if v is None: return "N/A"
                if v >= 1e9: return f"${v/1e9:.2f}B"
                if v >= 1e6: return f"${v/1e6:.2f}M"
                return f"${v:,.0f}"

            lines.append(
                f"{sym} ({d['name']}): price={fp(price)}, "
                f"24h={fpc(chg_24h)}, 7d={fpc(chg_7d)}, "
                f"mcap={fl(mcap)}, vol_24h={fl(vol)}, rank=#{rank}"
            )
        token_context = "\n".join(lines)

    # Build narrative context
    narrative_context = json.dumps(narratives, indent=2) if narratives else "No live narrative data."

    system_prompt = f"""You are Narratex, an elite crypto narrative intelligence agent powered by Binance Square signal analysis and live CoinGecko market data.

CURRENT NARRATIVE DATA:
{narrative_context}

{token_context}

INSTRUCTIONS:
- Answer questions using the live data above
- When token data is provided, always reference the actual current price, 24h change, market cap, and volume
- Be concise and direct — traders want fast answers
- Never make price predictions — report data and signal strength only
- If asked about a narrative, reference its confidence score and lifecycle stage
- Keep responses under 250 words unless more detail is requested
- Never say you don't have access to live data — you do, it is provided above"""

    try:
        resp = req_lib.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {groq_key}",
                "Content-Type":  "application/json",
            },
            json={
                "model":      "llama-3.3-70b-versatile",
                "max_tokens": 600,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_message},
                ],
            },
            timeout=20,
        )
        resp.raise_for_status()
        response = resp.json()["choices"][0]["message"]["content"]

        # Also return structured token data for the dashboard to render
        result = {"response": response}
        if fetched_details:
            result["token_data"] = {
                sym: format_token_detail_json(d)
                for sym, d in fetched_details.items()
            }
        return jsonify(result)

    except Exception as e:
        log.error(f"Groq chat error: {e}")
        return jsonify({"response": "Narratex is warming up — please try again in 30 seconds."}), 200


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    log.info(f"Starting Narratex API on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)

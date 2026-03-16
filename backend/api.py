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
import threading
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(__file__))

from collector import collect_signals, get_fallback_signals
from extractor import extract_narratives
from momentum import score_narratives

# import telegram bot starter
from telegram_bot import run_bot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [api] %(levelname)s %(message)s"
)
log = logging.getLogger(__name__)

app = Flask(__name__)

CORS(app, origins=[
    "https://davexinoh.github.io",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:3000",
])

_cache: dict = {
    "narratives":   [],
    "last_updated": None,
    "source":       None,
}

CACHE_TTL_SECONDS = 300


def is_cache_fresh() -> bool:
    if not _cache["last_updated"]:
        return False

    delta = (datetime.now(timezone.utc) - _cache["last_updated"]).total_seconds()
    return delta < CACHE_TTL_SECONDS


def refresh_narratives(force: bool = False) -> list[dict]:

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
    scored = score_narratives(narratives)

    _cache["narratives"] = scored
    _cache["last_updated"] = datetime.now(timezone.utc)
    _cache["source"] = source

    log.info(f"Pipeline complete: {len(scored)} narratives ({source})")
    return scored


@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "service": "Narratex API",
        "status": "ok",
        "version": "2.1.0",
        "docs": "/api/narratives",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.route("/api/narratives", methods=["GET"])
def get_narratives():

    force = request.args.get("refresh", "false").lower() == "true"
    min_conf = int(request.args.get("min_confidence", 0))

    try:
        narratives = refresh_narratives(force=force)
        filtered = [n for n in narratives if n["confidence"] >= min_conf]

        return jsonify({
            "narratives": filtered,
            "count": len(filtered),
            "source": _cache.get("source", "unknown"),
            "last_updated": _cache["last_updated"].isoformat() if _cache["last_updated"] else None,
            "cache_fresh": is_cache_fresh(),
        })

    except Exception as e:
        log.error(f"Error in /api/narratives: {e}")

        return jsonify({
            "error": "Failed to load narrative data",
            "detail": str(e)
        }), 500


@app.route("/api/narratives/<string:name>", methods=["GET"])
def get_narrative_detail(name: str):

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


@app.route("/api/status", methods=["GET"])
def cache_status():

    return jsonify({
        "cache_fresh": is_cache_fresh(),
        "last_updated": _cache["last_updated"].isoformat() if _cache["last_updated"] else None,
        "narrative_count": len(_cache["narratives"]),
        "source": _cache.get("source"),
    })


def start_telegram_bot():

    try:
        log.info("Starting Narratex Telegram bot thread")

        thread = threading.Thread(target=run_bot)
        thread.daemon = True
        thread.start()

    except Exception as e:
        log.error(f"Failed to start Telegram bot: {e}")


if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    start_telegram_bot()

    log.info(f"Starting Narratex API on port {port}")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
  )

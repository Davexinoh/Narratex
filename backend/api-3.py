"""
api.py
Narratex — Flask API

Endpoints:
  GET  /                      Health check
  GET  /api/narratives        Full narrative intelligence output
  GET  /api/narratives/<n>    Single narrative detail
  GET  /api/status            Cache metadata
  POST /api/chat              Dual AI chat (Groq + Gemini in parallel)
"""

import logging
import os
import sys
import json
import concurrent.futures
from datetime import datetime, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests as http

sys.path.insert(0, os.path.dirname(__file__))

from collector import collect_signals, get_fallback_signals
from extractor import extract_narratives
from momentum import score_narratives

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

# ── AI keys ──────────────────────────────────────────────────────────────────
GROQ_KEY   = os.environ.get("GROQ_API_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

# ---------------------------------------------------------------------------
# In-memory cache — requires --workers 1 in render.yaml
# ---------------------------------------------------------------------------
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


def refresh_narratives(force: bool = False) -> list:
    if not force and is_cache_fresh():
        log.info("Returning cached narratives")
        return _cache["narratives"]

    log.info("Running narrative pipeline...")
    source  = "live"
    signals = collect_signals(pages=5)

    if not signals:
        log.warning("No live signals — using fallback demo data")
        signals = get_fallback_signals()
        source  = "demo"

    narratives = extract_narratives(signals)
    scored     = score_narratives(narratives)

    _cache["narratives"]   = scored
    _cache["last_updated"] = datetime.now(timezone.utc)
    _cache["source"]       = source

    log.info(f"Pipeline complete: {len(scored)} narratives ({source})")
    return scored


# ---------------------------------------------------------------------------
# Dual AI helpers
# ---------------------------------------------------------------------------

def build_system_prompt(narratives: list) -> str:
    return f"""You are Narratex, an elite crypto narrative intelligence agent powered by Binance Square.

Current live narrative data:
{json.dumps(narratives, indent=2)}

Rules:
- Answer based on this data only
- Be concise and direct — traders want fast answers
- Use emojis sparingly
- Never make price predictions — report signal strength only
- Mention specific narrative names, confidence scores, and tokens when relevant
- Keep responses under 250 words"""


def call_groq(question: str, system: str):
    if not GROQ_KEY:
        return None
    try:
        resp = http.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "max_tokens": 600,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": question}
                ]
            },
            timeout=15
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log.error(f"Groq failed: {e}")
        return None


def call_gemini(question: str, system: str):
    if not GEMINI_KEY:
        return None
    try:
        resp = http.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={GEMINI_KEY}",
            headers={"Content-Type": "application/json"},
            json={
                "system_instruction": {"parts": [{"text": system}]},
                "contents": [{"parts": [{"text": question}]}],
                "generationConfig": {"maxOutputTokens": 600}
            },
            timeout=15
        )
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        log.error(f"Gemini failed: {e}")
        return None


def merge_responses(groq_resp, gemini_resp, question: str) -> str:
    """Groq + Gemini run in parallel. Gemini synthesizes both into one answer."""
    if groq_resp and gemini_resp and GEMINI_KEY:
        try:
            merge_prompt = f"""Two AI analysts answered this crypto question: "{question}"

Analyst 1 (Speed/Groq): {groq_resp}

Analyst 2 (Depth/Gemini): {gemini_resp}

Synthesize both into one definitive, concise response under 200 words.
Keep only the best insights from each. No preamble — just the answer."""

            resp = http.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={GEMINI_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": merge_prompt}]}],
                    "generationConfig": {"maxOutputTokens": 400}
                },
                timeout=12
            )
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            log.error(f"Merge failed: {e}")
            # Fall through to simple combine
            return f"{groq_resp}\n\n{gemini_resp}"

    if groq_resp and gemini_resp:
        return f"{groq_resp}\n\n{gemini_resp}"

    return groq_resp or gemini_resp or "Narratex is warming up — please try again in 30 seconds."


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "service":   "Narratex API",
        "status":    "ok",
        "version":   "3.0.0",
        "docs":      "/api/narratives",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.route("/api/narratives", methods=["GET"])
def get_narratives():
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
    try:
        narratives = refresh_narratives()
        match = next((n for n in narratives if n["name"].lower() == name.lower()), None)
        if not match:
            return jsonify({"error": f"Narrative '{name}' not found"}), 404
        return jsonify(match)
    except Exception as e:
        log.error(f"Error in /api/narratives/{name}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Dual AI chat — Groq and Gemini run in parallel.
    Gemini synthesizes both responses into one final answer.

    Body: { "message": str, "narratives": list (optional) }
    """
    try:
        body       = request.get_json(silent=True) or {}
        question   = (body.get("message") or "").strip()
        narratives = body.get("narratives") or _cache.get("narratives") or []

        if not question:
            return jsonify({"error": "message is required"}), 400

        if not GROQ_KEY and not GEMINI_KEY:
            return jsonify({"response": "AI keys not configured. Add GROQ_API_KEY and GEMINI_API_KEY to Render environment."}), 200

        system = build_system_prompt(narratives)

        # Run both models in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            groq_future   = executor.submit(call_groq,   question, system)
            gemini_future = executor.submit(call_gemini, question, system)
            groq_resp   = groq_future.result(timeout=18)
            gemini_resp = gemini_future.result(timeout=18)

        response = merge_responses(groq_resp, gemini_resp, question)

        return jsonify({
            "response": response,
            "sources":  {"groq": bool(groq_resp), "gemini": bool(gemini_resp)},
        })

    except Exception as e:
        log.error(f"Error in /api/chat: {e}")
        return jsonify({"response": "Narratex is warming up — please try again in 30 seconds."}), 200


@app.route("/api/status", methods=["GET"])
def cache_status():
    return jsonify({
        "cache_fresh":     is_cache_fresh(),
        "last_updated":    _cache["last_updated"].isoformat() if _cache["last_updated"] else None,
        "narrative_count": len(_cache["narratives"]),
        "source":          _cache.get("source"),
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    log.info(f"Starting Narratex API on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)

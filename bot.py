"""
bot.py
Narratex Telegram Bot

A standalone AI-powered Telegram bot that delivers crypto narrative
intelligence from the Narratex API. Runs on Render as a background worker.

Commands:
  /start        — Introduction and command list
  /briefing     — Full narrative intelligence briefing
  /leaderboard  — Top narratives ranked by confidence
  /rotation     — Capital rotation between narrative sectors
  /predictions  — Predicted emerging narratives
  /tokens       — Tokens associated with a narrative
  /refresh      — Force re-fetch of live data
"""

import os
import json
import logging
import requests
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
from telegram.constants import ParseMode

logging.basicConfig(
    format="%(asctime)s [bot] %(levelname)s %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN  = os.environ.get("TELEGRAM_TOKEN", "")
NARRATEX_API    = os.environ.get("NARRATEX_API", "https://narratex.onrender.com/api/narratives")
ANTHROPIC_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")

# ── Seed fallback ────────────────────────────────────────────────────────────
SEED = [
    {"name": "AI Infrastructure",    "confidence": 84, "mentions_growth": 91, "engagement_growth": 88, "volume_growth": 62, "stage": "rising",   "tokens": ["FET","TAO","RNDR","AKT","WLD","AGIX"]},
    {"name": "Solana Ecosystem",      "confidence": 79, "mentions_growth": 86, "engagement_growth": 82, "volume_growth": 57, "stage": "peak",     "tokens": ["SOL","JUP","RAY","BONK","PYTH","JTO"]},
    {"name": "Bitcoin Ecosystem",     "confidence": 76, "mentions_growth": 84, "engagement_growth": 79, "volume_growth": 53, "stage": "peak",     "tokens": ["STX","ORDI","SATS","RUNE","WBTC"]},
    {"name": "DeFi Resurgence",       "confidence": 71, "mentions_growth": 77, "engagement_growth": 72, "volume_growth": 49, "stage": "rising",   "tokens": ["AAVE","UNI","CRV","GMX","DYDX"]},
    {"name": "DePIN Compute",         "confidence": 67, "mentions_growth": 71, "engagement_growth": 65, "volume_growth": 58, "stage": "emerging", "tokens": ["HNT","IOTX","FIL","AKT","AR"]},
    {"name": "Layer 2 Scaling",       "confidence": 63, "mentions_growth": 68, "engagement_growth": 61, "volume_growth": 44, "stage": "declining","tokens": ["ARB","OP","MATIC","ZKS","STRK"]},
    {"name": "RWA Tokenization",      "confidence": 58, "mentions_growth": 62, "engagement_growth": 55, "volume_growth": 41, "stage": "emerging", "tokens": ["ONDO","CFG","MPL","TRU","POLYX"]},
    {"name": "Gaming Infrastructure", "confidence": 52, "mentions_growth": 55, "engagement_growth": 49, "volume_growth": 46, "stage": "declining","tokens": ["IMX","RON","MAGIC","BEAM","GALA"]},
]

# ── Helpers ──────────────────────────────────────────────────────────────────
STAGE_ICONS = {
    "emerging":  "↗", "rising": "↑", "peak": "▲", "declining": "↘"
}

def confidence_bar(score, width=8):
    filled = round((score / 100) * width)
    return "█" * filled + "░" * (width - filled)

def fetch_narratives(force=False):
    """Fetch from Narratex API, fall back to seed data."""
    try:
        url = f"{NARRATEX_API}?refresh=true" if force else NARRATEX_API
        resp = requests.get(url, timeout=15, headers={"User-Agent": "NarratexBot/1.0"})
        resp.raise_for_status()
        data = resp.json()
        narratives = data.get("narratives", [])
        if narratives:
            return narratives, data.get("source", "live")
    except Exception as e:
        log.warning(f"API fetch failed: {e}")
    return SEED, "cached"

def get_lifecycle_stage(n):
    """Use API stage field if present, otherwise derive from scores."""
    if n.get("stage") in ["emerging","rising","peak","declining"]:
        return n["stage"]
    score    = n.get("confidence", 0)
    mentions = n.get("mentions_growth", 0)
    if score >= 78:                              return "peak"
    if score >= 68:                              return "rising"
    if score >= 55 and mentions >= 60:           return "emerging"
    return "declining"

def source_label(source):
    return {
        "live":           "🟢 LIVE · BINANCE SQUARE",
        "binance_square": "🟡 DIRECT · BINANCE SQUARE",
        "cached":         "🔵 CACHED · SEED DATA",
        "demo":           "🔵 CACHED · DEMO DATA",
    }.get(source, f"● {source.upper()}")

def now_utc():
    return datetime.now(timezone.utc).strftime("%H:%M UTC · %b %d")

# ── AI response via Claude ───────────────────────────────────────────────────
def ask_claude(question, narratives):
    """Call Claude API with narrative context to answer user questions."""
    if not ANTHROPIC_KEY:
        return None

    system = f"""You are Narratex, an elite crypto narrative intelligence agent powered by Binance Square.

Current live narrative data:
{json.dumps(narratives, indent=2)}

Rules:
- Answer questions based on this data only
- Be concise and direct — traders want fast answers
- Use emojis sparingly for readability
- Never make price predictions — report signal strength only
- Always mention specific narrative names, confidence scores, and tokens when relevant
- Keep responses under 300 words"""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1000,
                "system": system,
                "messages": [{"role": "user", "content": question}]
            },
            timeout=20
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]
    except Exception as e:
        log.warning(f"Claude API failed: {e}")
        return None

# ── Command handlers ─────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = (
        "📡 *NARRATEX*\n"
        "_Crypto Narrative Intelligence Engine_\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Detect emerging crypto narratives from Binance Square signals — before they trend.\n\n"
        "*Commands*\n"
        "/briefing — Full narrative briefing\n"
        "/leaderboard — Top narratives ranked\n"
        "/rotation — Capital rotation between sectors\n"
        "/predictions — Predicted emerging narratives\n"
        "/tokens `<narrative>` — Tokens for a narrative\n"
        "/refresh — Force live data refresh\n\n"
        "Or just ask me anything about crypto narratives.\n\n"
        "🔗 [Full Dashboard](https://davexinoh.github.io/Narratex/dashboard.html)"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_briefing(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📡 Scanning Binance Square...")
    narratives, source = fetch_narratives()

    lines = [
        "📡 *NARRATEX INTELLIGENCE BRIEFING*",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        source_label(source),
        f"Updated: {now_utc()}",
        "",
        "*TOP NARRATIVES*",
        "",
    ]

    for i, n in enumerate(narratives[:5], 1):
        stage = get_lifecycle_stage(n)
        icon  = STAGE_ICONS.get(stage, "↑")
        bar   = confidence_bar(n["confidence"])
        tokens = " · ".join(n.get("tokens", [])[:4])
        lines += [
            f"{i}\\. *{n['name']}*",
            f"`{bar}` {n['confidence']}%  {icon} {stage.upper()}",
            f"_{tokens}_",
            f"Mentions +{n.get('mentions_growth',0)}%  ·  Engagement +{n.get('engagement_growth',0)}%",
            "",
        ]

    # Lifecycle summary
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("*LIFECYCLE*")
    for stage in ["emerging","rising","peak","declining"]:
        group = [n["name"] for n in narratives if get_lifecycle_stage(n) == stage]
        if group:
            lines.append(f"{STAGE_ICONS[stage]} {stage.upper()}: {' · '.join(group)}")

    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "🔗 [Full Dashboard](https://davexinoh.github.io/Narratex/dashboard.html)",
    ]

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


async def cmd_leaderboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    narratives, source = fetch_narratives()
    sorted_n = sorted(narratives, key=lambda x: x["confidence"], reverse=True)

    lines = [
        "🏆 *NARRATIVE LEADERBOARD*",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        source_label(source),
        "",
    ]

    medals = ["🥇","🥈","🥉"]
    for i, n in enumerate(sorted_n, 1):
        prefix = medals[i-1] if i <= 3 else f"{i}\\."
        stage  = get_lifecycle_stage(n)
        icon   = STAGE_ICONS.get(stage, "↑")
        lines.append(f"{prefix} *{n['name']}* — {n['confidence']}%  {icon}")

    lines += [
        "",
        "🔗 [Full Dashboard](https://davexinoh.github.io/Narratex/dashboard.html)",
    ]

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


async def cmd_rotation(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    narratives, source = fetch_narratives()

    gainers  = [n for n in narratives if get_lifecycle_stage(n) in ["peak","rising"]]
    losers   = [n for n in narratives if get_lifecycle_stage(n) == "declining"]
    emerging = [n for n in narratives if get_lifecycle_stage(n) == "emerging"]

    lines = [
        "🔄 *CAPITAL ROTATION RADAR*",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        source_label(source),
        "",
        "*Capital Flow Direction*",
        "",
    ]

    flows = []
    for i, loser in enumerate(losers):
        target = gainers[i % len(gainers)] if gainers else None
        if target:
            flows.append((loser["name"], target["name"], loser["confidence"]))

    for e in emerging:
        if gainers:
            flows.append((gainers[0]["name"], e["name"], e.get("mentions_growth", 50)))

    if flows:
        for from_n, to_n, strength in flows[:5]:
            lines.append(f"↘ _{from_n}_ → ↑ *{to_n}*  `{strength}% signal`")
    else:
        lines.append("_Insufficient data to detect rotation patterns_")

    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "🔗 [Full Dashboard](https://davexinoh.github.io/Narratex/dashboard.html)",
    ]

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


async def cmd_predictions(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    narratives, source = fetch_narratives()

    predictions = []
    for n in narratives:
        mentions    = n.get("mentions_growth", 0)
        engagement  = n.get("engagement_growth", 0)
        confidence  = n["confidence"]
        avg_signal  = (mentions + engagement) / 2
        gap         = max(0, avg_signal - confidence)
        probability = min(95, max(40, round(confidence * 0.5 + gap * 0.5)))
        strength    = "STRONG" if probability >= 75 else "MODERATE" if probability >= 60 else "SPECULATIVE"
        predictions.append({**n, "probability": probability, "strength": strength})

    predictions.sort(key=lambda x: x["probability"], reverse=True)

    lines = [
        "🔮 *NARRATIVE PREDICTIONS*",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "_Based on signal acceleration vs current confidence_",
        source_label(source),
        "",
    ]

    for i, n in enumerate(predictions[:6], 1):
        tokens = " · ".join(n.get("tokens", [])[:3])
        lines += [
            f"{i}\\. *{n['name']}* — {n['probability']}%",
            f"_{n['strength']}  ·  {tokens}_",
            "",
        ]

    lines += [
        "⚠️ _Not financial advice — signal strength only_",
        "",
        "🔗 [Full Dashboard](https://davexinoh.github.io/Narratex/dashboard.html)",
    ]

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


async def cmd_tokens(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = " ".join(ctx.args).strip().lower() if ctx.args else ""
    narratives, source = fetch_narratives()

    if not query:
        # Show all narratives with tokens
        lines = ["🎯 *NARRATIVE TOKEN MAP*", "━━━━━━━━━━━━━━━━━━━━━━━━", ""]
        for n in narratives:
            stage  = get_lifecycle_stage(n)
            icon   = STAGE_ICONS.get(stage, "↑")
            tokens = " · ".join(n.get("tokens", []))
            lines += [f"{icon} *{n['name']}* ({n['confidence']}%)", f"`{tokens}`", ""]
        lines.append("🔗 [Full Dashboard](https://davexinoh.github.io/Narratex/dashboard.html)")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
        return

    # Search for specific narrative
    match = next((n for n in narratives if query in n["name"].lower()), None)
    if not match:
        await update.message.reply_text(
            f"❌ No narrative found matching *{query}*\n\nTry: AI, Solana, Bitcoin, DeFi, DePIN, Layer 2, RWA, Gaming",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    stage  = get_lifecycle_stage(match)
    icon   = STAGE_ICONS.get(stage, "↑")
    tokens = match.get("tokens", [])

    lines = [
        f"🎯 *{match['name']} — TOKENS*",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        f"Confidence: *{match['confidence']}%*  {icon} {stage.upper()}",
        f"Mentions: +{match.get('mentions_growth',0)}%",
        "",
        "*Associated Tokens*",
    ]
    for t in tokens:
        lines.append(f"  · *{t}*")

    lines += [
        "",
        "🔗 [Full Dashboard](https://davexinoh.github.io/Narratex/dashboard.html)",
    ]

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


async def cmd_refresh(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Refreshing live data from Binance Square...")
    narratives, source = fetch_narratives(force=True)
    top = narratives[0] if narratives else {}
    await update.message.reply_text(
        f"✅ *Refreshed*\n"
        f"{source_label(source)}\n\n"
        f"Top narrative: *{top.get('name','—')}* — {top.get('confidence','—')}%\n\n"
        f"Use /briefing for the full report.",
        parse_mode=ParseMode.MARKDOWN
    )


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle free-text questions using Claude AI."""
    text = update.message.text.strip()
    if not text:
        return

    await update.message.reply_text("🤔 Analysing...")

    narratives, source = fetch_narratives()

    # Try Claude first
    reply = ask_claude(text, narratives)

    if not reply:
        # Fallback: keyword routing
        text_lower = text.lower()
        if any(w in text_lower for w in ["briefing","brief","summary","top"]):
            await cmd_briefing(update, ctx)
            return
        elif any(w in text_lower for w in ["leaderboard","rank","best","strongest"]):
            await cmd_leaderboard(update, ctx)
            return
        elif any(w in text_lower for w in ["rotation","flow","capital","moving"]):
            await cmd_rotation(update, ctx)
            return
        elif any(w in text_lower for w in ["predict","prediction","emerging","next"]):
            await cmd_predictions(update, ctx)
            return
        elif any(w in text_lower for w in ["token","coin","buy","watch"]):
            await cmd_tokens(update, ctx)
            return
        else:
            reply = (
                "I can help you with crypto narrative intelligence.\n\n"
                "Try:\n"
                "/briefing — Full market briefing\n"
                "/leaderboard — Top narratives\n"
                "/predictions — What's emerging\n"
                "/tokens — Token associations\n"
                "/rotation — Capital flow"
            )

    await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)


import threading
import asyncio
from flask import Flask as FlaskApp

health_app = FlaskApp(__name__)

@health_app.route("/")
def health():
    return {"service": "narratex-bot", "status": "running"}, 200


def run_bot_polling():
    """Run the Telegram bot in its own thread with its own event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    tg_app = Application.builder().token(TELEGRAM_TOKEN).build()

    tg_app.add_handler(CommandHandler("start",       cmd_start))
    tg_app.add_handler(CommandHandler("briefing",    cmd_briefing))
    tg_app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))
    tg_app.add_handler(CommandHandler("rotation",    cmd_rotation))
    tg_app.add_handler(CommandHandler("predictions", cmd_predictions))
    tg_app.add_handler(CommandHandler("tokens",      cmd_tokens))
    tg_app.add_handler(CommandHandler("refresh",     cmd_refresh))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("Bot polling started")
    tg_app.run_polling(allowed_updates=Update.ALL_TYPES)


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    if not TELEGRAM_TOKEN:
        log.error("TELEGRAM_TOKEN environment variable not set")
        return

    log.info("Starting Narratex Bot...")

    # Start bot polling in background thread with its own event loop
    bot_thread = threading.Thread(target=run_bot_polling, daemon=True)
    bot_thread.start()

    # Run Flask health server in main thread — satisfies Render web service check
    port = int(os.environ.get("PORT", 8080))
    log.info(f"Health server on port {port}")
    health_app.run(host="0.0.0.0", port=port, use_reloader=False)


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
          

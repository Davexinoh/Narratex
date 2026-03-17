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
from coingecko import fetch_token_detail, format_token_detail_text, fetch_trending_tokens, SYMBOL_TO_ID

logging.basicConfig(
    format="%(asctime)s [bot] %(levelname)s %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN  = os.environ.get("TELEGRAM_TOKEN", "")
NARRATEX_API    = os.environ.get("NARRATEX_API", "https://narratex.onrender.com/api/narratives")
GROQ_KEY        = os.environ.get("GROQ_API_KEY", "")

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

# ── AI response via Groq ─────────────────────────────────────────────────────
def ask_groq(question, narratives):
    """Call Groq API with narrative context and live token data to answer user questions."""
    if not GROQ_KEY:
        return None

    # Detect token symbols in the question
    words         = question.upper().split()
    known_symbols = set(SYMBOL_TO_ID.keys())
    mentioned     = [w.strip("?.,!") for w in words if w.strip("?.,!") in known_symbols]

    token_context = ""
    for symbol in mentioned[:3]:
        detail = fetch_token_detail(symbol)
        if detail:
            p   = detail.get("price_usd")
            c24 = detail.get("price_change_24h")
            mc  = detail.get("market_cap")
            vol = detail.get("volume_24h")

            fp  = (f"${p:,.2f}" if p and p >= 1 else f"${p:.6f}") if p else "N/A"
            fc  = f"{c24:+.2f}%" if c24 is not None else "N/A"
            fmc = (f"${mc/1e9:.2f}B" if mc and mc >= 1e9 else f"${mc/1e6:.2f}M") if mc else "N/A"
            fv  = (f"${vol/1e9:.2f}B" if vol and vol >= 1e9 else f"${vol/1e6:.2f}M") if vol else "N/A"

            token_context += (
                f"\nLIVE DATA for {symbol} ({detail['name']}): "
                f"price={fp}, 24h change={fc}, market cap={fmc}, volume={fv}, rank=#{detail.get('market_cap_rank','N/A')}"
            )

    system = f"""You are Narratex, an elite crypto narrative intelligence agent powered by Binance Square and live CoinGecko data.

Current narrative data:
{json.dumps(narratives, indent=2)}
{token_context}

Rules:
- Answer questions based on this data only
- When token data is provided above, always cite the actual price, 24h change, market cap, and volume
- Be concise and direct — traders want fast answers
- Use emojis sparingly for readability
- Never make price predictions — report signal strength and live data only
- Keep responses under 300 words"""

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "max_tokens": 1000,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": question}
                ]
            },
            timeout=20
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        log.error(f"Groq API HTTP error: {e.response.status_code} — {e.response.text}")
        return None
    except Exception as e:
        log.error(f"Groq API failed: {type(e).__name__}: {e}")
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
        "/token `<symbol>` — Live data for any token (price, mcap, volume)\n"
        "/trending — Top trending tokens on CoinGecko right now\n"
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


async def cmd_token(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Fetch and display full live token data from CoinGecko."""
    query = " ".join(ctx.args).strip().upper() if ctx.args else ""

    if not query:
        await update.message.reply_text(
            "Please provide a token symbol.\n\nExample: `/token BTC` or `/token SOL`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    await update.message.reply_text(f"📡 Fetching live data for *{query}*...", parse_mode=ParseMode.MARKDOWN)

    detail = fetch_token_detail(query)
    if not detail:
        await update.message.reply_text(
            f"❌ Token *{query}* not found on CoinGecko.\n\n"
            f"Try standard symbols like BTC, ETH, SOL, FET, RNDR, AAVE etc.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    text = format_token_detail_text(detail)
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


async def cmd_trending(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show CoinGecko trending tokens right now."""
    await update.message.reply_text("📡 Fetching trending tokens from CoinGecko...")

    trending = fetch_trending_tokens()
    if not trending:
        await update.message.reply_text("❌ Could not fetch trending data. Try again shortly.")
        return

    lines = [
        "🔥 *TRENDING ON COINGECKO*",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "_Top coins by search volume right now_",
        "",
    ]
    for i, coin in enumerate(trending[:10], 1):
        rank = f"#{coin['market_cap_rank']}" if coin.get("market_cap_rank") else "unranked"
        lines.append(f"{i}\\. *{coin['name']}* ({coin['symbol']})  ·  {rank}")

    lines += [
        "",
        "Use `/token <symbol>` for full data on any token",
        "🔗 [Full Dashboard](https://davexinoh.github.io/Narratex/dashboard.html)",
    ]

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


async def cmd_refresh(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Refreshing live data from all sources...")
    narratives, source = fetch_narratives(force=True)

    source_detail = {
        "live":           "🟢 *LIVE*\nBinance Square pulled successfully.",
        "binance_square": "🟢 *LIVE*\nBinance Square pulled successfully.",
        "demo":           "🔵 *CACHED*\nBinance Square unreachable — using seed data.\nCoinGecko and GitHub signals still active.",
        "cached":         "🔵 *CACHED*\nBinance Square unreachable — using seed data.\nCoinGecko and GitHub signals still active.",
    }.get(source, f"🟡 *{source.upper()}*")

    top3 = narratives[:3]
    top3_lines = "\n".join(
        f"{i+1}\\. *{n['name']}* — {n['confidence']}%  {STAGE_ICONS.get(get_lifecycle_stage(n), '↑')} {get_lifecycle_stage(n).upper()}"
        for i, n in enumerate(top3)
    )

    await update.message.reply_text(
        f"✅ *REFRESH COMPLETE*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{source_detail}\n\n"
        f"*TOP NARRATIVES*\n"
        f"{top3_lines}\n\n"
        f"Total: *{len(narratives)} narratives* detected\n\n"
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
    reply = ask_groq(text, narratives)

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



import asyncio
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from telegram.ext import ApplicationBuilder


async def homepage(request):
    return JSONResponse({"service": "narratex-bot", "status": "running"})


async def run():
    if not TELEGRAM_TOKEN:
        log.error("TELEGRAM_TOKEN not set")
        return

    port = int(os.environ.get("PORT", 8080))

    tg_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    tg_app.add_handler(CommandHandler("start",       cmd_start))
    tg_app.add_handler(CommandHandler("briefing",    cmd_briefing))
    tg_app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))
    tg_app.add_handler(CommandHandler("rotation",    cmd_rotation))
    tg_app.add_handler(CommandHandler("predictions", cmd_predictions))
    tg_app.add_handler(CommandHandler("tokens",      cmd_tokens))
    tg_app.add_handler(CommandHandler("token",       cmd_token))
    tg_app.add_handler(CommandHandler("trending",    cmd_trending))
    tg_app.add_handler(CommandHandler("refresh",     cmd_refresh))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    starlette_app = Starlette(routes=[Route("/", homepage)])
    config = uvicorn.Config(starlette_app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(config)

    log.info(f"Starting Narratex Bot on port {port}")

    async with tg_app:
        await tg_app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await tg_app.start()
        log.info("Bot polling started")
        await server.serve()
        await tg_app.updater.stop()
        await tg_app.stop()


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
  

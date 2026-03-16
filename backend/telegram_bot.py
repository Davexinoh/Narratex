import os
import requests
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

API_URL = "https://narratex.onrender.com/api/narratives"
TOKEN = os.environ.get("TELEGRAM_TOKEN")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("telegram_bot")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "Narratex Narrative Intelligence\n\n"
        "Commands:\n"
        "/leaderboard — Top narratives\n"
        "/briefing — Market briefing"
    )


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        r = requests.get(API_URL)
        data = r.json()

        text = "Narratex Narrative Leaderboard\n\n"

        for i, n in enumerate(data["narratives"][:5], start=1):

            text += (
                f"{i}. {n['name']}\n"
                f"Confidence: {n['confidence']}%\n"
                f"Tokens: {', '.join(n['tokens'])}\n\n"
            )

        await update.message.reply_text(text)

    except Exception as e:

        log.error(e)

        await update.message.reply_text(
            "Unable to fetch narrative data."
        )


async def briefing(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        r = requests.get(API_URL)
        data = r.json()

        top = data["narratives"][0]

        text = (
            "Narratex Market Briefing\n\n"
            f"Top Narrative: {top['name']}\n"
            f"Confidence Score: {top['confidence']}%\n"
            f"Tokens: {', '.join(top['tokens'])}"
        )

        await update.message.reply_text(text)

    except Exception as e:

        log.error(e)

        await update.message.reply_text(
            "Unable to fetch briefing."
        )


def run_bot():

    if not TOKEN:

        raise ValueError("TELEGRAM_TOKEN environment variable not set")

    log.info("Starting Narratex Telegram bot")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("briefing", briefing))

    app.run_polling()

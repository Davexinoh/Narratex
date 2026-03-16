import os
import threading
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

API_URL = "https://narratex.onrender.com/api/narratives"
TOKEN = os.environ.get("TELEGRAM_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Narratex Narrative Intelligence\n\n"
        "/leaderboard — top narratives\n"
        "/briefing — market briefing"
    )


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):

    r = requests.get(API_URL)
    data = r.json()

    text = "Narratex Narrative Leaderboard\n\n"

    for i, n in enumerate(data["narratives"][:5], start=1):

        text += f"{i}. {n['name']} — {n['confidence']}%\n"

    await update.message.reply_text(text)


async def briefing(update: Update, context: ContextTypes.DEFAULT_TYPE):

    r = requests.get(API_URL)
    data = r.json()

    top = data["narratives"][0]

    text = (
        f"Narratex Market Briefing\n\n"
        f"Top Narrative: {top['name']}\n"
        f"Confidence: {top['confidence']}%\n"
        f"Tokens: {', '.join(top['tokens'])}"
    )

    await update.message.reply_text(text)


def run_bot():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("briefing", briefing))

    app.run_polling()


def start_bot_thread():

    thread = threading.Thread(target=run_bot)
    thread.start()

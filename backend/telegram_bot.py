import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

API_URL = "https://narratex.onrender.com/api/narratives"

# Telegram token pulled from Render environment variable
TOKEN = os.environ.get("TELEGRAM_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Narratex Narrative Intelligence\n\n"
        "Commands:\n"
        "/leaderboard — Top crypto narratives\n"
        "/briefing — Current market narrative briefing\n"
    )

    await update.message.reply_text(text)


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        r = requests.get(API_URL)
        data = r.json()

        text = "Narratex Narrative Leaderboard\n\n"

        for i, n in enumerate(data["narratives"][:8], start=1):

            text += (
                f"{i}. {n['name']}\n"
                f"Confidence: {n['confidence']}%\n"
                f"Tokens: {', '.join(n['tokens'])}\n\n"
            )

        await update.message.reply_text(text)

    except Exception as e:

        await update.message.reply_text(
            "Narratex API is currently unavailable."
        )


async def briefing(update: Update, context: ContextTypes.DEFAULT_TYPE):

    try:
        r = requests.get(API_URL)
        data = r.json()

        top = data["narratives"][0]

        text = (
            "Narratex Market Briefing\n\n"
            f"Top Narrative: {top['name']}\n"
            f"Confidence Score: {top['confidence']}%\n\n"
            f"Key Tokens:\n{', '.join(top['tokens'])}"
        )

        await update.message.reply_text(text)

    except Exception:

        await update.message.reply_text(
            "Unable to fetch narrative briefing."
        )


def main():

    if not TOKEN:
        raise ValueError("TELEGRAM_TOKEN environment variable not set")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("briefing", briefing))

    app.run_polling()


if __name__ == "__main__":
    main()

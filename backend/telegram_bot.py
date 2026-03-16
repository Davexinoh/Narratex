import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

API_URL = "https://narratex.onrender.com/api/narratives"
TOKEN = "8749835569:AAHrpPvrBua1pz0T3H8NMcpyIgeEkJPUMVQ"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Narratex\n\nAI Narrative Intelligence Engine\n\nCommands:\n/leaderboard\n/briefing"
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

def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("briefing", briefing))

    app.run_polling()

if __name__ == "__main__":
    main()

import os
import requests
from flask import Flask
from threading import Thread

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
IPTV_API_KEY = os.environ["IPTV_API_KEY"]

API_URL = "https://4k.online-cms.ru/api/api.php"

app = Flask(__name__)


@app.route("/")
def home():
    return "Hatifi IPTV Bot is running ✅"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


keyboard = [
    ["➕ New M3U", "📺 New MAG"],
    ["🔄 Renew M3U", "🔄 Renew MAG"],
    ["🔎 Device Info", "📦 Packages"],
    ["💰 Credits"],
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📺 Hatifi IPTV Bot\n\n"
        "👋 مرحبا\n"
        "اختار العملية:",
        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        ),
    )


async def credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get(
            API_URL,
            params={
                "action": "reseller",
                "api_key": IPTV_API_KEY,
            },
            timeout=20,
        )

        data = response.json()

        if str(data.get("status")).lower() == "true":
            username = data.get("username", "-")
            credits_value = data.get("credits", "-")

            await update.message.reply_text(
                f"✅ الحساب متصل\n\n"
                f"👤 Username: {username}\n"
                f"💰 Credits: {credits_value}"
            )
        else:
            await update.message.reply_text(
                f"❌ API response:\n{data}"
            )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Error:\n{e}"
        )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "💰 Credits":
        await credits(update, context)

    elif text == "➕ New M3U":
        await update.message.reply_text("⏳ New M3U غادي نفعّلوه فالمرحلة الجاية.")

    elif text == "📺 New MAG":
        await update.message.reply_text("⏳ New MAG غادي نفعّلوه فالمرحلة الجاية.")

    elif text == "🔄 Renew M3U":
        await update.message.reply_text("⏳ Renew M3U غادي نفعّلوه فالمرحلة الجاية.")

    elif text == "🔄 Renew MAG":
        await update.message.reply_text("⏳ Renew MAG غادي نفعّلوه فالمرحلة الجاية.")

    elif text == "🔎 Device Info":
        await update.message.reply_text("⏳ Device Info غادي نفعّلوه فالمرحلة الجاية.")

    elif text == "📦 Packages":
        await update.message.reply_text("⏳ Packages غادي نفعّلوه فالمرحلة الجاية.")


def main():
    Thread(target=run_web, daemon=True).start()

    bot = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, buttons))

    print("Hatifi IPTV Bot started")
    bot.run_polling()


if __name__ == "__main__":
    main()

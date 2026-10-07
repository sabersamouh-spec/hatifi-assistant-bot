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

# =========================
# SETTINGS
# =========================

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
IPTV_API_KEY = os.environ["IPTV_API_KEY"]

API_URL = "https://4k.online-cms.ru/api/api.php"

# =========================
# WEB SERVER FOR RENDER
# =========================

app = Flask(__name__)


@app.route("/")
def home():
    return "Hatifi IPTV Bot is running ✅"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# =========================
# TELEGRAM MENU
# =========================

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


# =========================
# CREDITS
# =========================

async def credits(update: Update):

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
                "✅ الحساب متصل\n\n"
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


# =========================
# PACKAGES
# =========================

async def packages(update: Update):

    try:

        response = requests.get(
            API_URL,
            params={
                "action": "bouquet",
                "api_key": IPTV_API_KEY,
            },
            timeout=20,
        )

        data = response.json()

        await update.message.reply_text(
            f"📦 Packages:\n\n{data}"
        )

    except Exception as e:

        await update.message.reply_text(
            f"❌ Error:\n{e}"
        )


# =========================
# BUTTONS
# =========================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if text == "💰 Credits":

        await credits(update)

    elif text == "📦 Packages":

        await packages(update)

    elif text == "➕ New M3U":

        await update.message.reply_text(
            "⏳ New M3U غادي نفعّلوه من بعد."
        )

    elif text == "📺 New MAG":

        await update.message.reply_text(
            "⏳ New MAG غادي نفعّلوه من بعد."
        )

    elif text == "🔄 Renew M3U":

        await update.message.reply_text(
            "⏳ Renew M3U غادي نفعّلوه من بعد."
        )

    elif text == "🔄 Renew MAG":

        await update.message.reply_text(
            "⏳ Renew MAG غادي نفعّلوه من بعد."
        )

    elif text == "🔎 Device Info":

        await update.message.reply_text(
            "⏳ Device Info غادي نفعّلوه من بعد."
        )


# =========================
# START BOT
# =========================

def main():

    Thread(
        target=run_web,
        daemon=True
    ).start()

    bot = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    bot.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    bot.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            buttons
        )
    )

    print("Hatifi IPTV Bot started ✅")

    bot.run_polling()


if __name__ == "__main__":
    main()

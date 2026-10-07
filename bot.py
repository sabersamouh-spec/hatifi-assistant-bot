import os
import threading
import requests
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# =========================================================
# CONFIG
# =========================================================

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
IPTV_API_KEY = os.environ["IPTV_API_KEY"]

API_URL = "https://4k.online-cms.ru/api/api.php"

# =========================================================
# KEEP ALIVE FOR RENDER
# =========================================================

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "Hatifi IPTV Bot is running ✅"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)


# =========================================================
# KEYBOARDS
# =========================================================

main_keyboard = ReplyKeyboardMarkup(
    [
        ["➕ New M3U", "📺 New MAG"],
        ["🔄 Renew M3U", "🔄 Renew MAG"],
        ["🔎 Device Info", "📦 Packages"],
        ["💰 Credits"],
    ],
    resize_keyboard=True,
)

cancel_keyboard = ReplyKeyboardMarkup(
    [["❌ Cancel"]],
    resize_keyboard=True,
)

# =========================================================
# STATES
# =========================================================

(
    NEW_M3U_PACKAGE,
    NEW_M3U_DURATION,
    NEW_M3U_COUNTRY,
    NEW_M3U_CONFIRM,
) = range(4)


# =========================================================
# API FUNCTION
# =========================================================

def api_request(params):
    params["api_key"] = IPTV_API_KEY

    try:
        response = requests.get(
            API_URL,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        try:
            return response.json()
        except Exception:
            return {
                "status": "false",
                "message": response.text,
            }

    except Exception as e:
        return {
            "status": "false",
            "message": str(e),
        }


# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "📺 Hatifi IPTV Bot\n\n"
        "👋 مرحبا\n"
        "اختار العملية:"
    )

    await update.message.reply_text(
        text,
        reply_markup=main_keyboard,
    )


# =========================================================
# CREDITS
# =========================================================

async def credits(update: Update, context: ContextTypes.DEFAULT_TYPE):

    data = api_request({
        "action": "reseller"
    })

    if str(data.get("status")).lower() == "true":

        username = data.get("username", "-")
        credits_value = data.get("credits", "0")

        await update.message.reply_text(
            f"✅ الحساب متصل\n\n"
            f"👤 Username: {username}\n"
            f"💰 Credits: {credits_value}",
            reply_markup=main_keyboard,
        )

    else:

        await update.message.reply_text(
            "❌ خطأ في الاتصال بالـ API\n\n"
            f"{data.get('message', data)}",
            reply_markup=main_keyboard,
        )


# =========================================================
# PACKAGES
# =========================================================

def get_packages():

    data = api_request({
        "action": "bouquet"
    })

    # API can return list directly
    if isinstance(data, list):
        return data

    # Or inside another field
    if isinstance(data, dict):

        for key in ["packages", "bouquets", "data"]:

            value = data.get(key)

            if isinstance(value, list):
                return value

    return []


async def packages(update: Update, context: ContextTypes.DEFAULT_TYPE):

    packs = get_packages()

    if not packs:

        await update.message.reply_text(
            "❌ ماقدرتش نجيب Packages.",
            reply_markup=main_keyboard,
        )

        return

    text = "📦 Packages:\n\n"

    for pack in packs:

        pack_id = pack.get("id", "-")
        name = pack.get("name", "-")

        text += (
            f"📦 {name}\n"
            f"🆔 {pack_id}\n\n"
        )

    await update.message.reply_text(
        text,
        reply_markup=main_keyboard,
    )


# =========================================================
# NEW M3U
# =========================================================

async def new_m3u_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    packs = get_packages()

    if not packs:

        await update.message.reply_text(
            "❌ ماقدرتش نجيب Packages."
        )

        return ConversationHandler.END

    context.user_data["packages"] = packs

    buttons = []

    for pack in packs:

        pack_id = str(pack.get("id"))
        name = str(pack.get("name"))

        buttons.append([
            f"{name} | {pack_id}"
        ])

    buttons.append(["❌ Cancel"])

    keyboard = ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True,
    )

    await update.message.reply_text(
        "➕ New M3U\n\n"
        "📦 اختار الباقة:",
        reply_markup=keyboard,
    )

    return NEW_M3U_PACKAGE


async def new_m3u_package(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    text = update.message.text.strip()

    if text == "❌ Cancel":
        return await cancel(update, context)

    if "|" not in text:

        await update.message.reply_text(
            "❌ اختار الباقة من الأزرار."
        )

        return NEW_M3U_PACKAGE

    try:

        name, pack_id = text.rsplit("|", 1)

        context.user_data["pack_name"] = name.strip()
        context.user_data["pack_id"] = pack_id.strip()

    except Exception:

        await update.message.reply_text(
            "❌ الباقة غير صحيحة."
        )

        return NEW_M3U_PACKAGE

    keyboard = ReplyKeyboardMarkup(
        [
            ["1", "3"],
            ["6", "12"],
            ["❌ Cancel"],
        ],
        resize_keyboard=True,
    )

    await update.message.reply_text(
        "⏳ اختار مدة الاشتراك بالشهور:",
        reply_markup=keyboard,
    )

    return NEW_M3U_DURATION


async def new_m3u_duration(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    duration = update.message.text.strip()

    if duration == "❌ Cancel":
        return await cancel(update, context)

    if duration not in ["1", "3", "6", "12"]:

        await update.message.reply_text(
            "❌ اختار 1 أو 3 أو 6 أو 12."
        )

        return NEW_M3U_DURATION

    context.user_data["duration"] = duration

    keyboard = ReplyKeyboardMarkup(
        [
            ["MA

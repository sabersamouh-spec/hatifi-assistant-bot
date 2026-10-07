import os
import requests

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# Secrets from Render
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
IPTV_API_KEY = os.environ["IPTV_API_KEY"]

API_URL = "https://4k.online-cms.ru/api/api.php"


def api_request(**params):
    params["api_key"] = IPTV_API_KEY

    response = requests.get(
        API_URL,
        params=params,
        timeout=20
    )

    response.raise_for_status()
    return response.json()


def main_menu():
    keyboard = [
        [
            InlineKeyboardButton("➕ New M3U", callback_data="new_m3u"),
            InlineKeyboardButton("📺 New MAG", callback_data="new_mag"),
        ],
        [
            InlineKeyboardButton("🔄 Renew M3U", callback_data="renew_m3u"),
            InlineKeyboardButton("🔄 Renew MAG", callback_data="renew_mag"),
        ],
        [
            InlineKeyboardButton("🔎 Device Info", callback_data="device_info"),
            InlineKeyboardButton("📦 Packages", callback_data="packages"),
        ],
        [
            InlineKeyboardButton("💰 Credits", callback_data="credits"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📺 Hatifi IPTV Bot\n\n"
        "مرحبا 👋\n"
        "اختار العملية:",
        reply_markup=main_menu()
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:

        # Credits
        if query.data == "credits":

            data = api_request(action="reseller")

            if isinstance(data, list) and len(data) > 0:
                info = data[0]

                text = (
                    "💰 Reseller Info\n\n"
                    f"👤 Username: {info.get('username', '-')}\n"
                    f"💳 Credits: {info.get('credits', '-')}\n"
                    f"✅ Enabled: {info.get('enabled', '-')}"
                )

            else:
                text = f"❌ API response:\n{data}"

            await query.edit_message_text(
                text,
                reply_markup=main_menu()
            )

        # Packages
        elif query.data == "packages":

            data = api_request(action="bouquet")

            if not isinstance(data, list) or len(data) == 0:
                await query.edit_message_text(
                    "❌ ما لقيت حتى Package.",
                    reply_markup=main_menu()
                )
                return

            text = "📦 IPTV Packages\n\n"

            for package in data:
                text += (
                    f"📺 {package.get('name', '-')}\n"
                    f"ID: {package.get('id', '-')}\n\n"
                )

            await query.edit_message_text(
                text[:4000],
                reply_markup=main_menu()
            )

        # New M3U
        elif query.data == "new_m3u":

            await query.edit_message_text(
                "➕ New M3U\n\n"
                "هاد الزر خدام ✅\n"
                "غادي نضيفو ليه اختيار Package والمدة.",
                reply_markup=main_menu()
            )

        # New MAG
        elif query.data == "new_mag":

            await query.edit_message_text(
                "📺 New MAG\n\n"
                "هاد الزر خدام ✅\n"
                "غادي نضيفو إدخال MAC + Package + المدة.",
                reply_markup=main_menu()
            )

        # Renew M3U
        elif query.data == "renew_m3u":

            await query.edit_message_text(
                "🔄 Renew M3U\n\n"
                "غادي نضيفو Username + Password + مدة التجديد.",
                reply_markup=main_menu()
            )

        # Renew MAG
        elif query.data == "renew_mag":

            await query.edit_message_text(
                "🔄 Renew MAG\n\n"
                "غادي نضيفو MAC + مدة التجديد.",
                reply_markup=main_menu()
            )

        # Device Info
        elif query.data == "device_info":

            await query.edit_message_text(
                "🔎 Device Info\n\n"
                "غادي نضيفو البحث بـ M3U أو MAC.",
                reply_markup=main_menu()
            )

    except requests.RequestException as e:

        await query.edit_message_text(
            f"❌ خطأ في الاتصال بالـ IPTV API:\n{e}",
            reply_markup=main_menu()
        )

    except Exception as e:

        await query.edit_message_text(
            f"❌ Error:\n{e}",
            reply_markup=main_menu()
        )


def main():

    print("Starting Hatifi IPTV Bot...")

    app = Application.builder().token(
        TELEGRAM_BOT_TOKEN
    ).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CallbackQueryHandler(menu)
    )

    print("Bot is running.")

    app.run_polling()


if __name__ == "__main__":
    main()

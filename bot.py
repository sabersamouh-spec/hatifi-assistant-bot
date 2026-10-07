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

# ============================================================
# CONFIG
# ============================================================

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
IPTV_API_KEY = os.environ["IPTV_API_KEY"]

API_URL = "https://4k.online-cms.ru/api/api.php"


# ============================================================
# RENDER WEB SERVER
# ============================================================

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "Hatifi IPTV Bot is running"


def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host="0.0.0.0", port=port)


# ============================================================
# KEYBOARDS
# ============================================================

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


# ============================================================
# CONVERSATION STATES
# ============================================================

(
    M3U_PACKAGE,
    M3U_DURATION,
    M3U_COUNTRY,
    M3U_CONFIRM,
) = range(4)


# ============================================================
# API
# ============================================================

def api_request(params):
    params = dict(params)
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

    except Exception as error:
        return {
            "status": "false",
            "message": str(error),
        }


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "📺 Hatifi IPTV Bot\n\n"
        "👋 مرحبا\n"
        "اختار العملية:",
        reply_markup=main_keyboard,
    )


# ============================================================
# CREDITS
# ============================================================

async def credits(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    data = api_request(
        {
            "action": "reseller",
        }
    )

    if isinstance(data, dict) and str(
        data.get("status")
    ).lower() == "true":

        username = data.get("username", "-")
        credit_value = data.get("credits", "0")

        await update.message.reply_text(
            "✅ الحساب متصل\n\n"
            f"👤 Username: {username}\n"
            f"💰 Credits: {credit_value}",
            reply_markup=main_keyboard,
        )

    else:
        await update.message.reply_text(
            "❌ خطأ في الاتصال بالـ API\n\n"
            f"{data}",
            reply_markup=main_keyboard,
        )


# ============================================================
# PACKAGES
# ============================================================

def get_packages():
    data = api_request(
        {
            "action": "bouquet",
        }
    )

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in [
            "packages",
            "bouquets",
            "data",
        ]:
            value = data.get(key)

            if isinstance(value, list):
                return value

    return []


async def packages(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    pack_list = get_packages()

    if not pack_list:
        await update.message.reply_text(
            "❌ ماقدرتش نجيب Packages.",
            reply_markup=main_keyboard,
        )
        return

    lines = ["📦 Packages:", ""]

    for pack in pack_list:
        pack_id = pack.get("id", "-")
        pack_name = pack.get("name", "-")

        lines.append(
            f"📦 {pack_name} — ID: {pack_id}"
        )

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=main_keyboard,
    )


# ============================================================
# NEW M3U - STEP 1
# ============================================================

async def new_m3u_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    pack_list = get_packages()

    if not pack_list:
        await update.message.reply_text(
            "❌ ماقدرتش نجيب لائحة Packages.",
            reply_markup=main_keyboard,
        )

        return ConversationHandler.END

    context.user_data["packages"] = pack_list

    buttons = []

    for pack in pack_list:
        pack_id = str(pack.get("id", ""))
        pack_name = str(pack.get("name", ""))

        buttons.append(
            [f"{pack_name} | {pack_id}"]
        )

    buttons.append(["❌ Cancel"])

    keyboard = ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True,
    )

    await update.message.reply_text(
        "➕ New M3U\n\n"
        "📦 اختار Package:",
        reply_markup=keyboard,
    )

    return M3U_PACKAGE


# ============================================================
# NEW M3U - STEP 2
# ============================================================

async def new_m3u_package(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = update.message.text.strip()

    if text == "❌ Cancel":
        return await cancel(update, context)

    if "|" not in text:
        await update.message.reply_text(
            "❌ اختار Package من الأزرار."
        )
        return M3U_PACKAGE

    try:
        pack_name, pack_id = text.rsplit("|", 1)

        pack_name = pack_name.strip()
        pack_id = pack_id.strip()

        context.user_data["pack_name"] = pack_name
        context.user_data["pack_id"] = pack_id

    except Exception:
        await update.message.reply_text(
            "❌ Package غير صحيح."
        )
        return M3U_PACKAGE

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

    return M3U_DURATION


# ============================================================
# NEW M3U - STEP 3
# ============================================================

async def new_m3u_duration(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    duration = update.message.text.strip()

    if duration == "❌ Cancel":
        return await cancel(update, context)

    if duration not in [
        "1",
        "3",
        "6",
        "12",
    ]:
        await update.message.reply_text(
            "❌ اختار 1 أو 3 أو 6 أو 12."
        )
        return M3U_DURATION

    context.user_data["duration"] = duration

    keyboard = ReplyKeyboardMarkup(
        [
            ["MA", "FR"],
            ["ES", "BE"],
            ["ALL"],
            ["❌ Cancel"],
        ],
        resize_keyboard=True,
    )

    await update.message.reply_text(
        "🌍 اختار Country:\n\n"
        "🇲🇦 MA = Morocco\n"
        "🇫🇷 FR = France\n"
        "🇪🇸 ES = Spain\n"
        "🇧🇪 BE = Belgium\n"
        "🌐 ALL = VPN / جميع الدول",
        reply_markup=keyboard,
    )

    return M3U_COUNTRY


# ============================================================
# NEW M3U - STEP 4
# ============================================================

async def new_m3u_country(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    country = update.message.text.strip().upper()

    if country == "❌ CANCEL":
        return await cancel(update, context)

    if country != "ALL" and len(country) != 2:
        await update.message.reply_text(
            "❌ دخل Country بحال MA أو FR أو ALL."
        )
        return M3U_COUNTRY

    context.user_data["country"] = country

    pack_name = context.user_data.get(
        "pack_name",
        "-",
    )

    pack_id = context.user_data.get(
        "pack_id",
        "-",
    )

    duration = context.user_data.get(
        "duration",
        "-",
    )

    keyboard = ReplyKeyboardMarkup(
        [
            ["✅ Confirm"],
            ["❌ Cancel"],
        ],
        resize_keyboard=True,
    )

    await update.message.reply_text(
        "📋 تأكيد الطلب\n\n"
        f"📦 Package: {pack_name}\n"
        f"🆔 Pack ID: {pack_id}\n"
        f"⏳ Duration: {duration} month(s)\n"
        f"🌍 Country: {country}\n\n"
        "⚠️ Confirm يمكن يخصم Credits.",
        reply_markup=keyboard,
    )

    return M3U_CONFIRM


# ============================================================
# NEW M3U - CREATE
# ============================================================

async def new_m3u_confirm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = update.message.text.strip()

    if text == "❌ Cancel":
        return await cancel(update, context)

    if text != "✅ Confirm":
        await update.message.reply_text(
            "اختار ✅ Confirm أو ❌ Cancel."
        )
        return M3U_CONFIRM

    await update.message.reply_text(
        "⏳ جاري إنشاء M3U..."
    )

    data = api_request(
        {
            "action": "new",
            "type": "m3u",
            "sub": context.user_data["duration"],
            "pack": context.user_data["pack_id"],
            "country": context.user_data["country"],
            "notes": "Hatifi Telegram Bot",
        }
    )

    if isinstance(data, dict) and str(
        data.get("status")
    ).lower() == "true":

        username = (
            data.get("username")
            or data.get("user")
            or "-"
        )

        password = (
            data.get("password")
            or data.get("pass")
            or "-"
        )

        server_url = (
            data.get("url")
            or data.get("server")
            or data.get("m3u")
            or data.get("link")
            or ""
        )

        result = (
            "✅ M3U CREATED SUCCESSFULLY\n\n"
            f"👤 Username: {username}\n"
            f"🔑 Password: {password}\n\n"
            f"📦 Package: "
            f"{context.user_data['pack_name']}\n"
            f"⏳ Duration: "
            f"{context.user_data['duration']} month(s)\n"
            f"🌍 Country: "
            f"{context.user_data['country']}"
        )

        if server_url:
            result += (
                "\n\n"
                f"🔗 URL:\n{server_url}"
            )

        await update.message.reply_text(
            result,
            reply_markup=main_keyboard,
        )

    else:
        await update.message.reply_text(
            "❌ فشل إنشاء M3U\n\n"
            f"API response:\n{data}",
            reply_markup=main_keyboard,
        )

    context.user_data.clear()

    return ConversationHandler.END


# ============================================================
# CANCEL
# ============================================================

async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()

    await update.message.reply_text(
        "❌ تم إلغاء العملية.",
        reply_markup=main_keyboard,
    )

    return ConversationHandler.END


# ============================================================
# OTHER BUTTONS
# ============================================================

async def other_buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    text = update.message.text.strip()

    if text == "📺 New MAG":
        await update.message.reply_text(
            "⏳ New MAG غادي نفعّلوه من بعد.",
            reply_markup=main_keyboard,
        )

    elif text == "🔄 Renew M3U":
        await update.message.reply_text(
            "⏳ Renew M3U غادي نفعّلوه من بعد.",
            reply_markup=main_keyboard,
        )

    elif text == "🔄 Renew MAG":
        await update.message.reply_text(
            "⏳ Renew MAG غادي نفعّلوه من بعد.",
            reply_markup=main_keyboard,
        )

    elif text == "🔎 Device Info":
        await update.message.reply_text(
            "⏳ Device Info غادي نفعّلوه من بعد.",
            reply_markup=main_keyboard,
        )


# ============================================================
# MAIN
# ============================================================

def main():
    threading.Thread(
        target=run_web_server,
        daemon=True,
    ).start()

    application = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    new_m3u_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(r"^➕ New M3U$"),
                new_m3u_start,
            )
        ],
        states={
            M3U_PACKAGE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    new_m3u_package,
                )
            ],
            M3U_DURATION: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    new_m3u_duration,
                )
            ],
            M3U_COUNTRY: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    new_m3u_country,
                )
            ],
            M3U_CONFIRM: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    new_m3u_confirm,
                )
            ],
        },
        fallbacks=[
            CommandHandler(
                "cancel",
                cancel,
            )
        ],
    )

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        new_m3u_conversation
    )

    application.add_handler(
        MessageHandler(
            filters.Regex(r"^💰 Credits$"),
            credits,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex(r"^📦 Packages$"),
            packages,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            other_buttons,
        )
    )

    print("Hatifi IPTV Bot started")

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()

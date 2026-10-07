import os
import threading
import requests

from urllib.parse import urlparse, parse_qs

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


# ============================================================
# STATES
# ============================================================

(
    M3U_PACKAGE,
    M3U_DURATION,
    M3U_COUNTRY,
    M3U_CONFIRM,
    RENEW_USERNAME,
    RENEW_PASSWORD,
    RENEW_DURATION,
    RENEW_CONFIRM,
) = range(8)


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
            timeout=30
        )

        response.raise_for_status()

        try:
            return response.json()
        except Exception:
            return {
                "status": "false",
                "message": response.text
            }

    except Exception as error:
        return {
            "status": "false",
            "message": str(error)
        }


# ============================================================
# HELPERS
# ============================================================

def is_success(data):
    if not isinstance(data, dict):
        return False

    value = data.get("status")

    if value is True:
        return True

    return str(value).lower() == "true"


def extract_m3u_credentials(url):
    username = None
    password = None

    if not url:
        return username, password

    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        username_list = query.get("username")
        password_list = query.get("password")

        if username_list:
            username = username_list[0]

        if password_list:
            password = password_list[0]

    except Exception:
        pass

    return username, password


# ============================================================
# START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "📺 Hatifi IPTV Bot\n\n"
        "👋 مرحبا\n"
        "اختار العملية:",
        reply_markup=main_keyboard
    )


# ============================================================
# CANCEL
# ============================================================

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "❌ تم إلغاء العملية.",
        reply_markup=main_keyboard
    )

    return ConversationHandler.END


# ============================================================
# CREDITS
# ============================================================

async def credits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = api_request({
        "action": "reseller"
    })

    if is_success(data):
        username = data.get("username", "-")
        credit_value = data.get("credits", "0")

        await update.message.reply_text(
            "✅ الحساب متصل\n\n"
            f"👤 Username: {username}\n"
            f"💰 Credits: {credit_value}",
            reply_markup=main_keyboard
        )

    else:
        await update.message.reply_text(
            "❌ خطأ في الاتصال بالـ API\n\n"
            f"{data}",
            reply_markup=main_keyboard
        )


# ============================================================
# PACKAGES
# ============================================================

def get_packages():
    data = api_request({
        "action": "bouquet"
    })

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ["packages", "bouquets", "data"]:
            value = data.get(key)

            if isinstance(value, list):
                return value

    return []


async def packages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pack_list = get_packages()

    if not pack_list:
        await update.message.reply_text(
            "❌ ماقدرتش نجيب Packages.",
            reply_markup=main_keyboard
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
        reply_markup=main_keyboard
    )


# ============================================================
# NEW M3U
# ============================================================

async def new_m3u_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    pack_list = get_packages()

    if not pack_list:
        await update.message.reply_text(
            "❌ ماقدرتش نجيب Packages.",
            reply_markup=main_keyboard
        )
        return ConversationHandler.END

    buttons = []

    for pack in pack_list:
        pack_id = str(pack.get("id", ""))
        pack_name = str(pack.get("name", ""))

        buttons.append([
            f"{pack_name} | {pack_id}"
        ])

    buttons.append(["❌ Cancel"])

    keyboard = ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True
    )

    await update.message.reply_text(
        "➕ New M3U\n\n"
        "📦 اختار Package:",
        reply_markup=keyboard
    )

    return M3U_PACKAGE


async def new_m3u_package(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

        context.user_data["pack_name"] = pack_name.strip()
        context.user_data["pack_id"] = pack_id.strip()

    except Exception:
        await update.message.reply_text(
            "❌ Package غير صحيح."
        )
        return M3U_PACKAGE

    keyboard = ReplyKeyboardMarkup(
        [
            ["1", "3"],
            ["6", "12"],
            ["❌ Cancel"]
        ],
        resize_keyboard=True
    )

    await update.message.reply_text(
        "⏳ اختار مدة الاشتراك بالشهور:",
        reply_markup=keyboard
    )

    return M3U_DURATION


async def new_m3u_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    duration = update.message.text.strip()

    if duration == "❌ Cancel":
        return await cancel(update, context)

    if duration not in ["1", "3", "6", "12"]:
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
            ["❌ Cancel"]
        ],
        resize_keyboard=True
    )

    await update.message.reply_text(
        "🌍 اختار Country:\n\n"
        "🇲🇦 MA = Morocco\n"
        "🇫🇷 FR = France\n"
        "🇪🇸 ES = Spain\n"
        "🇧🇪 BE = Belgium\n"
        "🌐 ALL = جميع الدول / VPN",
        reply_markup=keyboard
    )

    return M3U_COUNTRY


async def new_m3u_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    country = update.message.text.strip().upper()

    if country == "❌ CANCEL":
        return await cancel(update, context)

    if country != "ALL" and len(country) != 2:
        await update.message.reply_text(
            "❌ دخل Country بحال MA أو FR أو ALL."
        )
        return M3U_COUNTRY

    context.user_data["country"] = country

    keyboard = ReplyKeyboardMarkup(
        [
            ["✅ Confirm"],
            ["❌ Cancel"]
        ],
        resize_keyboard=True
    )

    await update.message.reply_text(
        "📋 تأكيد إنشاء M3U\n\n"
        f"📦 Package: {context.user_data['pack_name']}\n"
        f"⏳ Duration: {context.user_data['duration']} month(s)\n"
        f"🌍 Country: {country}\n\n"
        "⚠️ Confirm يمكن يخصم Credits.",
        reply_markup=keyboard
    )

    return M3U_CONFIRM


async def new_m3u_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    data = api_request({
        "action": "new",
        "type": "m3u",
        "sub": context.user_data["duration"],
        "pack": context.user_data["pack_id"],
        "country": context.user_data["country"],
        "notes": "Hatifi Telegram Bot"
    })

    if is_success(data):
        m3u_url = (
            data.get("url")
            or data.get("m3u")
            or data.get("link")
            or data.get("playlist")
            or ""
        )

        username = (
            data.get("username")
            or data.get("user")
        )

        password = (
            data.get("password")
            or data.get("pass")
        )

        url_username, url_password = extract_m3u_credentials(
            m3u_url
        )

        if not username:
            username = url_username

        if not password:
            password = url_password

        username = username or "-"
        password = password or "-"

        result = (
            "✅ M3U CREATED SUCCESSFULLY\n\n"
            f"👤 Username: {username}\n"
            f"🔑 Password: {password}\n\n"
            f"📦 Package: {context.user_data['pack_name']}\n"
            f"⏳ Duration: {context.user_data['duration']} month(s)\n"
            f"🌍 Country: {context.user_data['country']}"
        )

        if m3u_url:
            result += (
                "\n\n"
                "🔗 M3U URL:\n"
                f"{m3u_url}"
            )

        await update.message.reply_text(
            result,
            reply_markup=main_keyboard,
            disable_web_page_preview=True
        )

    else:
        await update.message.reply_text(
            "❌ فشل إنشاء M3U\n\n"
            f"{data}",
            reply_markup=main_keyboard
        )

    context.user_data.clear()

    return ConversationHandler.END


# ============================================================
# RENEW M3U
# ============================================================

async def renew_m3u_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "🔄 Renew M3U\n\n"
        "👤 دخل Username ديال الاشتراك:",
        reply_markup=ReplyKeyboardMarkup(
            [["❌ Cancel"]],
            resize_keyboard=True
        )
    )

    return RENEW_USERNAME


async def renew_m3u_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()

    if username == "❌ Cancel":
        return await cancel(update, context)

    if not username:
        await update.message.reply_text(
            "❌ دخل Username صحيح."
        )
        return RENEW_USERNAME

    context.user_data["renew_username"] = username

    await update.message.reply_text(
        "🔑 دابا دخل Password ديال الاشتراك:"
    )

    return RENEW_PASSWORD


async def renew_m3u_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()

    if password == "❌ Cancel":
        return await cancel(update, context)

    if not password:
        await update.message.reply_text(
            "❌ دخل Password صحيح."
        )
        return RENEW_PASSWORD

    context.user_data["renew_password"] = password

    keyboard = ReplyKeyboardMarkup(
        [
            ["1", "3"],
            ["6", "12"],
            ["❌ Cancel"]
        ],
        resize_keyboard=True
    )

    await update.message.reply_text(
        "⏳ شحال بغيتي تجدد؟\n\n"
        "اختار عدد الشهور:",
        reply_markup=keyboard
    )

    return RENEW_DURATION


async def renew_m3u_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    duration = update.message.text.strip()

    if duration == "❌ Cancel":
        return await cancel(update, context)

    if duration not in ["1", "3", "6", "12"]:
        await update.message.reply_text(
            "❌ اختار 1 أو 3 أو 6 أو 12."
        )
        return RENEW_DURATION

    context.user_data["renew_duration"] = duration

    keyboard = ReplyKeyboardMarkup(
        [
            ["✅ Confirm Renew"],
            ["❌ Cancel"]
        ],
        resize_keyboard=True
    )

    await update.message.reply_text(
        "📋 تأكيد التجديد\n\n"
        f"👤 Username: {context.user_data['renew_username']}\n"
        f"🔑 Password: {context.user_data['renew_password']}\n"
        f"⏳ Renewal: {duration} month(s)\n\n"
        "⚠️ الضغط على Confirm Renew غادي يدير التجديد الحقيقي وقد يخصم Credits.",
        reply_markup=keyboard
    )

    return RENEW_CONFIRM


async def renew_m3u_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "❌ Cancel":
        return await cancel(update, context)

    if text != "✅ Confirm Renew":
        await update.message.reply_text(
            "اختار ✅ Confirm Renew أو ❌ Cancel."
        )
        return RENEW_CONFIRM

    username = context.user_data["renew_username"]
    password = context.user_data["renew_password"]
    duration = context.user_data["renew_duration"]

    await update.message.reply_text(
        "⏳ جاري تجديد الاشتراك..."
    )

    data = api_request({
        "action": "renew",
        "type": "m3u",
        "username": username,
        "password": password,
        "sub": duration
    })

    if is_success(data):
        message = data.get(
            "message",
            "M3U renew successful"
        )

        await update.message.reply_text(
            "✅ تم تجديد M3U بنجاح\n\n"
            f"👤 Username: {username}\n"
            f"⏳ Added: {duration} month(s)\n"
            f"📡 API: {message}",
            reply_markup=main_keyboard
        )

    else:
        error_message = (
            data.get("message", str(data))
            if isinstance(data, dict)
            else str(data)
        )

        await update.message.reply_text(
            "❌ فشل التجديد\n\n"
            f"📡 API: {error_message}",
            reply_markup=main_keyboard
        )

    context.user_data.clear()

    return ConversationHandler.END


# ============================================================
# OTHER BUTTONS
# ============================================================

async def other_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text == "📺 New MAG":
        await update.message.reply_text(
            "⏳ New MAG مازال غادي نفعّلوه.",
            reply_markup=main_keyboard
        )

    elif text == "🔄 Renew MAG":
        await update.message.reply_text(
            "⏳ Renew MAG مازال غادي نفعّلوه.",
            reply_markup=main_keyboard
        )

    elif text == "🔎 Device Info":
        await update.message.reply_text(
            "⏳ Device Info مازال غادي نفعّلوه.",
            reply_markup=main_keyboard
        )


# ============================================================
# MAIN
# ============================================================

def main():
    threading.Thread(
        target=run_web_server,
        daemon=True
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
                new_m3u_start
            )
        ],
        states={
            M3U_PACKAGE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    new_m3u_package
                )
            ],
            M3U_DURATION: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    new_m3u_duration
                )
            ],
            M3U_COUNTRY: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    new_m3u_country
                )
            ],
            M3U_CONFIRM: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    new_m3u_confirm
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel)
        ]
    )

    renew_m3u_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(r"^🔄 Renew M3U$"),
                renew_m3u_start
            )
        ],
        states={
            RENEW_USERNAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    renew_m3u_username
                )
            ],
            RENEW_PASSWORD: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    renew_m3u_password
                )
            ],
            RENEW_DURATION: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    renew_m3u_duration
                )
            ],
            RENEW_CONFIRM: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    renew_m3u_confirm
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel)
        ]
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        new_m3u_conversation
    )

    application.add_handler(
        renew_m3u_conversation
    )

    application.add_handler(
        MessageHandler(
            filters.Regex(r"^💰 Credits$"),
            credits
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex(r"^📦 Packages$"),
            packages
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            other_buttons
        )
    )

    print("Hatifi IPTV Bot started")

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()

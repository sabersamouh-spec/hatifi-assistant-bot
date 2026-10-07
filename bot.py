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

    web_app.run(
        host="0.0.0.0",
        port=port
    )


# ============================================================
# KEYBOARDS
# ============================================================

main_keyboard = ReplyKeyboardMarkup(
    [
        ["➕ New M3U", "📺 New MAG"],
        ["🔄 Renew M3U", "🔄 Renew MAG"],
        ["🔎 Device Info", "⚙️ Device Status"],
        ["📦 Packages", "💰 Credits"],
    ],
    resize_keyboard=True,
)


cancel_keyboard = ReplyKeyboardMarkup(
    [
        ["❌ Cancel"]
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

    INFO_TYPE,
    INFO_M3U_USERNAME,
    INFO_M3U_PASSWORD,
    INFO_MAG_MAC,

    STATUS_USER_ID,
    STATUS_ACTION,
    STATUS_CONFIRM,

) = range(15)


# ============================================================
# API
# ============================================================

def api_request(params):

    request_params = dict(params)

    request_params["api_key"] = IPTV_API_KEY

    try:

        response = requests.get(
            API_URL,
            params=request_params,
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

    status = data.get("status")

    if status is True:
        return True

    return str(status).lower() == "true"


def extract_m3u_credentials(url):

    username = None
    password = None

    if not url:
        return username, password

    try:

        parsed = urlparse(url)

        query = parse_qs(
            parsed.query
        )

        username_values = query.get(
            "username"
        )

        password_values = query.get(
            "password"
        )

        if username_values:
            username = username_values[0]

        if password_values:
            password = password_values[0]

    except Exception:
        pass

    return username, password


def clean_value(value):

    if value is None:
        return "-"

    if value == "":
        return "-"

    return str(value)


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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

async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data.clear()

    await update.message.reply_text(
        "❌ تم إلغاء العملية.",
        reply_markup=main_keyboard
    )

    return ConversationHandler.END


# ============================================================
# CREDITS
# ============================================================

async def credits(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    data = api_request({
        "action": "reseller"
    })

    if is_success(data):

        username = clean_value(
            data.get("username")
        )

        credit_value = clean_value(
            data.get("credits")
        )

        enabled = clean_value(
            data.get("enabled")
        )

        await update.message.reply_text(
            "✅ الحساب متصل\n\n"
            f"👤 Username: {username}\n"
            f"💰 Credits: {credit_value}\n"
            f"🟢 Enabled: {enabled}",
            reply_markup=main_keyboard
        )

    else:

        message = (
            data.get("message", str(data))
            if isinstance(data, dict)
            else str(data)
        )

        await update.message.reply_text(
            "❌ خطأ في الاتصال بالـ API\n\n"
            f"{message}",
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

        for key in [
            "packages",
            "bouquets",
            "data"
        ]:

            value = data.get(key)

            if isinstance(value, list):
                return value

    return []


async def packages(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    pack_list = get_packages()

    if not pack_list:

        await update.message.reply_text(
            "❌ ماقدرتش نجيب Packages.",
            reply_markup=main_keyboard
        )

        return

    lines = [
        "📦 Packages",
        ""
    ]

    for pack in pack_list:

        pack_id = clean_value(
            pack.get("id")
        )

        pack_name = clean_value(
            pack.get("name")
        )

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

async def new_m3u_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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

        pack_id = str(
            pack.get("id", "")
        )

        pack_name = str(
            pack.get("name", "")
        )

        buttons.append(
            [
                f"{pack_name} | {pack_id}"
            ]
        )

    buttons.append(
        ["❌ Cancel"]
    )

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


async def new_m3u_package(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text.strip()

    if text == "❌ Cancel":

        return await cancel(
            update,
            context
        )

    if "|" not in text:

        await update.message.reply_text(
            "❌ اختار Package من الأزرار."
        )

        return M3U_PACKAGE

    try:

        pack_name, pack_id = text.rsplit(
            "|",
            1
        )

        context.user_data[
            "pack_name"
        ] = pack_name.strip()

        context.user_data[
            "pack_id"
        ] = pack_id.strip()

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


async def new_m3u_duration(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    duration = update.message.text.strip()

    if duration == "❌ Cancel":

        return await cancel(
            update,
            context
        )

    if duration not in [
        "1",
        "3",
        "6",
        "12"
    ]:

        await update.message.reply_text(
            "❌ اختار 1 أو 3 أو 6 أو 12."
        )

        return M3U_DURATION

    context.user_data[
        "duration"
    ] = duration

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


async def new_m3u_country(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    country = (
        update.message.text
        .strip()
        .upper()
    )

    if country == "❌ CANCEL":

        return await cancel(
            update,
            context
        )

    if (
        country != "ALL"
        and len(country) != 2
    ):

        await update.message.reply_text(
            "❌ دخل Country بحال MA أو FR أو ALL."
        )

        return M3U_COUNTRY

    context.user_data[
        "country"
    ] = country

    keyboard = ReplyKeyboardMarkup(
        [
            ["✅ Confirm"],
            ["❌ Cancel"]
        ],
        resize_keyboard=True
    )

    await update.message.reply_text(
        "📋 تأكيد إنشاء M3U\n\n"
        f"📦 Package: "
        f"{context.user_data['pack_name']}\n"
        f"⏳ Duration: "
        f"{context.user_data['duration']} month(s)\n"
        f"🌍 Country: {country}\n\n"
        "⚠️ Confirm يمكن يخصم Credits.",
        reply_markup=keyboard
    )

    return M3U_CONFIRM


async def new_m3u_confirm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text.strip()

    if text == "❌ Cancel":

        return await cancel(
            update,
            context
        )

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
        "sub": context.user_data[
            "duration"
        ],
        "pack": context.user_data[
            "pack_id"
        ],
        "country": context.user_data[
            "country"
        ],
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

        url_username, url_password = (
            extract_m3u_credentials(
                m3u_url
            )
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
            f"📦 Package: "
            f"{context.user_data['pack_name']}\n"
            f"⏳ Duration: "
            f"{context.user_data['duration']} month(s)\n"
            f"🌍 Country: "
            f"{context.user_data['country']}"
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

        message = (
            data.get("message", str(data))
            if isinstance(data, dict)
            else str(data)
        )

        await update.message.reply_text(
            "❌ فشل إنشاء M3U\n\n"
            f"📡 API: {message}",
            reply_markup=main_keyboard
        )

    context.user_data.clear()

    return ConversationHandler.END


# ============================================================
# RENEW M3U
# ============================================================

async def renew_m3u_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data.clear()

    await update.message.reply_text(
        "🔄 Renew M3U\n\n"
        "👤 دخل Username:",
        reply_markup=cancel_keyboard
    )

    return RENEW_USERNAME


async def renew_m3u_username(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    username = update.message.text.strip()

    if username == "❌ Cancel":

        return await cancel(
            update,
            context
        )

    if not username:

        await update.message.reply_text(
            "❌ دخل Username صحيح."
        )

        return RENEW_USERNAME

    context.user_data[
        "renew_username"
    ] = username

    await update.message.reply_text(
        "🔑 دخل Password:"
    )

    return RENEW_PASSWORD


async def renew_m3u_password(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    password = update.message.text.strip()

    if password == "❌ Cancel":

        return await cancel(
            update,
            context
        )

    if not password:

        await update.message.reply_text(
            "❌ دخل Password صحيح."
        )

        return RENEW_PASSWORD

    context.user_data[
        "renew_password"
    ] = password

    keyboard = ReplyKeyboardMarkup(
        [
            ["1", "3"],
            ["6", "12"],
            ["❌ Cancel"]
        ],
        resize_keyboard=True
    )

    await update.message.reply_text(
        "⏳ اختار مدة التجديد:",
        reply_markup=keyboard
    )

    return RENEW_DURATION


async def renew_m3u_duration(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    duration = update.message.text.strip()

    if duration == "❌ Cancel":

        return await cancel(
            update,
            context
        )

    if duration not in [
        "1",
        "3",
        "6",
        "12"
    ]:

        await update.message.reply_text(
            "❌ اختار 1 أو 3 أو 6 أو 12."
        )

        return RENEW_DURATION

    context.user_data[
        "renew_duration"
    ] = duration

    keyboard = ReplyKeyboardMarkup(
        [
            ["✅ Confirm Renew"],
            ["❌ Cancel"]
        ],
        resize_keyboard=True
    )

    await update.message.reply_text(
        "📋 تأكيد التجديد\n\n"
        f"👤 Username: "
        f"{context.user_data['renew_username']}\n"
        f"🔑 Password: "
        f"{context.user_data['renew_password']}\n"
        f"⏳ Duration: {duration} month(s)\n\n"
        "⚠️ العملية قد تخصم Credits.",
        reply_markup=keyboard
    )

    return RENEW_CONFIRM


async def renew_m3u_confirm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text.strip()

    if text == "❌ Cancel":

        return await cancel(
            update,
            context
        )

    if text != "✅ Confirm Renew":

        await update.message.reply_text(
            "اختار ✅ Confirm Renew أو ❌ Cancel."
        )

        return RENEW_CONFIRM

    username = context.user_data[
        "renew_username"
    ]

    password = context.user_data[
        "renew_password"
    ]

    duration = context.user_data[
        "renew_duration"
    ]

    await update.message.reply_text(
        "⏳ جاري تجديد M3U..."
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
            f"⏳ Added: {duration} month(s)\n\n"
            f"📡 {message}",
            reply_markup=main_keyboard
        )

    else:

        message = (
            data.get("message", str(data))
            if isinstance(data, dict)
            else str(data)
        )

        await update.message.reply_text(
            "❌ فشل التجديد\n\n"
            f"📡 API: {message}",
            reply_markup=main_keyboard
        )

    context.user_data.clear()

    return ConversationHandler.END


# ============================================================
# DEVICE INFO
# ============================================================

async def device_info_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data.clear()

    keyboard = ReplyKeyboardMarkup(
        [
            ["📱 M3U", "📺 MAG"],
            ["❌ Cancel"]
        ],
        resize_keyboard=True
    )

    await update.message.reply_text(
        "🔎 Device Info\n\n"
        "اختار نوع الجهاز:",
        reply_markup=keyboard
    )

    return INFO_TYPE


async def device_info_type(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text.strip()

    if text == "❌ Cancel":

        return await cancel(
            update,
            context
        )

    if text == "📱 M3U":

        context.user_data[
            "info_type"
        ] = "m3u"

        await update.message.reply_text(
            "👤 دخل Username:",
            reply_markup=cancel_keyboard
        )

        return INFO_M3U_USERNAME

    if text == "📺 MAG":

        context.user_data[
            "info_type"
        ] = "mag"

        await update.message.reply_text(
            "📺 دخل MAC Address\n\n"
            "مثال:\n"
            "00:1A:79:12:34:56",
            reply_markup=cancel_keyboard
        )

        return INFO_MAG_MAC

    await update.message.reply_text(
        "❌ اختار M3U أو MAG."
    )

    return INFO_TYPE


async def device_info_m3u_username(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    username = update.message.text.strip()

    if username == "❌ Cancel":

        return await cancel(
            update,
            context
        )

    context.user_data[
        "info_username"
    ] = username

    await update.message.reply_text(
        "🔑 دخل Password:"
    )

    return INFO_M3U_PASSWORD


async def device_info_m3u_password(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    password = update.message.text.strip()

    if password == "❌ Cancel":

        return await cancel(
            update,
            context
        )

    username = context.user_data[
        "info_username"
    ]

    await update.message.reply_text(
        "⏳ جاري البحث عن الاشتراك..."
    )

    data = api_request({
        "action": "device_info",
        "username": username,
        "password": password
    })

    await send_device_info(
        update,
        context,
        data
    )

    return ConversationHandler.END


async def device_info_mag(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    mac = update.message.text.strip()

    if mac == "❌ Cancel":

        return await cancel(
            update,
            context
        )

    await update.message.reply_text(
        "⏳ جاري البحث عن MAG..."
    )

    data = api_request({
        "action": "device_info",
        "mac": mac
    })

    await send_device_info(
        update,
        context,
        data
    )

    return ConversationHandler.END


async def send_device_info(
    update,
    context,
    data
):

    if not is_success(data):

        message = (
            data.get("message", str(data))
            if isinstance(data, dict)
            else str(data)
        )

        await update.message.reply_text(
            "❌ لم يتم العثور على الجهاز\n\n"
            f"📡 API: {message}",
            reply_markup=main_keyboard
        )

        context.user_data.clear()

        return

    username = clean_value(
        data.get("username")
    )

    password = clean_value(
        data.get("password")
    )

    user_id = clean_value(
        data.get("user_id")
        or data.get("id")
    )

    expire = clean_value(
        data.get("expire")
        or data.get("expiry")
        or data.get("exp_date")
    )

    country = clean_value(
        data.get("country")
    )

    notes = clean_value(
        data.get("notes")
        or data.get("note")
    )

    enabled = clean_value(
        data.get("enabled")
        or data.get("status_user")
    )

    url = clean_value(
        data.get("url")
    )

    result = (
        "🔎 DEVICE INFORMATION\n\n"
        f"🆔 User ID: {user_id}\n"
        f"👤 Username: {username}\n"
        f"🔑 Password: {password}\n"
        f"📅 Expire: {expire}\n"
        f"🌍 Country: {country}\n"
        f"🟢 Enabled: {enabled}\n"
        f"📝 Notes: {notes}"
    )

    if url != "-":

        result += (
            "\n\n"
            "🔗 URL:\n"
            f"{url}"
        )

    await update.message.reply_text(
        result,
        reply_markup=main_keyboard,
        disable_web_page_preview=True
    )

    context.user_data.clear()


# ============================================================
# DEVICE STATUS
# ============================================================

async def device_status_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data.clear()

    await update.message.reply_text(
        "⚙️ Device Status\n\n"
        "🆔 دخل User ID ديال الجهاز:",
        reply_markup=cancel_keyboard
    )

    return STATUS_USER_ID


async def device_status_user_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user_id = update.message.text.strip()

    if user_id == "❌ Cancel":

        return await cancel(
            update,
            context
        )

    if not user_id:

        await update.message.reply_text(
            "❌ دخل User ID صحيح."
        )

        return STATUS_USER_ID

    context.user_data[
        "status_user_id"
    ] = user_id

    keyboard = ReplyKeyboardMarkup(
        [
            ["✅ Enable", "⛔ Disable"],
            ["❌ Cancel"]
        ],
        resize_keyboard=True
    )

    await update.message.reply_text(
        "⚙️ شنو بغيتي تدير للجهاز؟",
        reply_markup=keyboard
    )

    return STATUS_ACTION


async def device_status_action(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text.strip()

    if text == "❌ Cancel":

        return await cancel(
            update,
            context
        )

    if text == "✅ Enable":

        status = "enable"
        action_name = "ENABLE"

    elif text == "⛔ Disable":

        status = "disable"
        action_name = "DISABLE"

    else:

        await update.message.reply_text(
            "❌ اختار Enable أو Disable."
        )

        return STATUS_ACTION

    context.user_data[
        "device_status"
    ] = status

    context.user_data[
        "status_action_name"
    ] = action_name

    keyboard = ReplyKeyboardMarkup(
        [
            ["✅ Confirm Status"],
            ["❌ Cancel"]
        ],
        resize_keyboard=True
    )

    await update.message.reply_text(
        "⚠️ تأكيد العملية\n\n"
        f"🆔 User ID: "
        f"{context.user_data['status_user_id']}\n"
        f"⚙️ Action: {action_name}\n\n"
        "واش متأكد؟",
        reply_markup=keyboard
    )

    return STATUS_CONFIRM


async def device_status_confirm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text.strip()

    if text == "❌ Cancel":

        return await cancel(
            update,
            context
        )

    if text != "✅ Confirm Status":

        await update.message.reply_text(
            "اختار ✅ Confirm Status أو ❌ Cancel."
        )

        return STATUS_CONFIRM

    user_id = context.user_data[
        "status_user_id"
    ]

    status = context.user_data[
        "device_status"
    ]

    action_name = context.user_data[
        "status_action_name"
    ]

    await update.message.reply_text(
        "⏳ جاري تنفيذ العملية..."
    )

    data = api_request({
        "action": "device_status",
        "id": user_id,
        "status": status
    })

    if is_success(data):

        message = data.get(
            "message",
            "User status updated"
        )

        await update.message.reply_text(
            "✅ تمت العملية بنجاح\n\n"
            f"🆔 User ID: {user_id}\n"
            f"⚙️ Status: {action_name}\n\n"
            f"📡 {message}",
            reply_markup=main_keyboard
        )

    else:

        message = (
            data.get("message", str(data))
            if isinstance(data, dict)
            else str(data)
        )

        await update.message.reply_text(
            "❌ فشلت العملية\n\n"
            f"📡 API: {message}",
            reply_markup=main_keyboard
        )

    context.user_data.clear()

    return ConversationHandler.END


# ============================================================
# NEW MAG / RENEW MAG
# ============================================================

async def other_buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    text = update.message.text.strip()

    if text == "📺 New MAG":

        await update.message.reply_text(
            "📺 New MAG\n\n"
            "⏳ غادي نفعّلوه منين نتأكد من جميع "
            "Parameters ديال MAG.",
            reply_markup=main_keyboard
        )

    elif text == "🔄 Renew MAG":

        await update.message.reply_text(
            "🔄 Renew MAG\n\n"
            "⏳ غادي نفعّلوه منين نتأكد من Parameters "
            "ديال Renew MAC.",
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

    # --------------------------------------------------------
    # NEW M3U CONVERSATION
    # --------------------------------------------------------

    new_m3u_conversation = ConversationHandler(

        entry_points=[
            MessageHandler(
                filters.Regex(
                    r"^➕ New M3U$"
                ),
                new_m3u_start
            )
        ],

        states={

            M3U_PACKAGE: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    new_m3u_package
                )
            ],

            M3U_DURATION: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    new_m3u_duration
                )
            ],

            M3U_COUNTRY: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    new_m3u_country
                )
            ],

            M3U_CONFIRM: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    new_m3u_confirm
                )
            ],
        },

        fallbacks=[
            CommandHandler(
                "cancel",
                cancel
            )
        ]
    )

    # --------------------------------------------------------
    # RENEW M3U CONVERSATION
    # --------------------------------------------------------

    renew_m3u_conversation = ConversationHandler(

        entry_points=[
            MessageHandler(
                filters.Regex(
                    r"^🔄 Renew M3U$"
                ),
                renew_m3u_start
            )
        ],

        states={

            RENEW_USERNAME: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    renew_m3u_username
                )
            ],

            RENEW_PASSWORD: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    renew_m3u_password
                )
            ],

            RENEW_DURATION: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    renew_m3u_duration
                )
            ],

            RENEW_CONFIRM: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    renew_m3u_confirm
                )
            ],
        },

        fallbacks=[
            CommandHandler(
                "cancel",
                cancel
            )
        ]
    )

    # --------------------------------------------------------
    # DEVICE INFO CONVERSATION
    # --------------------------------------------------------

    device_info_conversation = ConversationHandler(

        entry_points=[
            MessageHandler(
                filters.Regex(
                    r"^🔎 Device Info$"
                ),
                device_info_start
            )
        ],

        states={

            INFO_TYPE: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    device_info_type
                )
            ],

            INFO_M3U_USERNAME: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    device_info_m3u_username
                )
            ],

            INFO_M3U_PASSWORD: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    device_info_m3u_password
                )
            ],

            INFO_MAG_MAC: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    device_info_mag
                )
            ],
        },

        fallbacks=[
            CommandHandler(
                "cancel",
                cancel
            )
        ]
    )

    # --------------------------------------------------------
    # DEVICE STATUS CONVERSATION
    # --------------------------------------------------------

    device_status_conversation = ConversationHandler(

        entry_points=[
            MessageHandler(
                filters.Regex(
                    r"^⚙️ Device Status$"
                ),
                device_status_start
            )
        ],

        states={

            STATUS_USER_ID: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    device_status_user_id
                )
            ],

            STATUS_ACTION: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    device_status_action
                )
            ],

            STATUS_CONFIRM: [
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    device_status_confirm
                )
            ],
        },

        fallbacks=[
            CommandHandler(
                "cancel",
                cancel
            )
        ]
    )

    # ========================================================
    # ADD HANDLERS
    # ========================================================

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
        device_info_conversation
    )

    application.add_handler(
        device_status_conversation
    )

    application.add_handler(
        MessageHandler(
            filters.Regex(
                r"^📦 Packages$"
            ),
            packages
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex(
                r"^💰 Credits$"
            ),
            credits
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            other_buttons
        )
    )

    print(
        "Hatifi IPTV Bot started"
    )

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()

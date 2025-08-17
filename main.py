import os
import json
import shutil
import tempfile
import threading
from typing import Dict, Any

from filelock import FileLock
from dotenv import load_dotenv
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ============================
# إعداد البيئة والمسارات
# ============================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
GROUP_ID_ENV = os.getenv("GROUP_ID", "").strip()
GROUP_JOIN_LINK = os.getenv("GROUP_JOIN_LINK", "https://t.me/+cVAKJyQd-e84ZDk0").strip()

if not BOT_TOKEN:
    raise RuntimeError(" BOT_TOKEN غير معرّف. ضع قيمة المفتاح داخل ملف .env مثال:\nBOT_TOKEN=123456:ABC-DEF ")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = BASE_DIR
REFERRALS_FILE = os.path.join(DATA_DIR, "referrals.json")
BACKUP_FILE = os.path.join(DATA_DIR, "referrals_backup.json")
LOCK_FILE = REFERRALS_FILE + ".lock"

# حوّل GROUP_ID إلى int إذا تم تعريفه
GROUP_ID = None
if GROUP_ID_ENV:
    try:
        GROUP_ID = int(GROUP_ID_ENV)
    except ValueError:
        GROUP_ID = None

# ============================
# أدوات المزامنة والكتابة الذرّية
# ============================
file_lock = FileLock(LOCK_FILE)
memory_lock = threading.RLock()


def write_json_atomic(file_path: str, data: Dict[str, Any]) -> None:
    dir_name = os.path.dirname(file_path)
    os.makedirs(dir_name, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(prefix="tmp_", suffix=".json", dir=dir_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(temp_path, file_path)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def load_json_safely(file_path: str) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # حاول الاستعادة من النسخة الاحتياطية إذا كانت صالحة
        if os.path.exists(BACKUP_FILE):
            try:
                with open(BACKUP_FILE, "r", encoding="utf-8") as b:
                    data = json.load(b)
                # إن كانت النسخة الاحتياطية صالحة، ارجعها إلى الملف الأساسي
                with file_lock:
                    write_json_atomic(file_path, data)
                return data
            except Exception:
                return {}
        return {}
    except FileNotFoundError:
        return {}


def save_referrals_to_disk(data: Dict[str, Any]) -> None:
    with file_lock:
        write_json_atomic(REFERRALS_FILE, data)
        shutil.copyfile(REFERRALS_FILE, BACKUP_FILE)


# ============================
# تحميل البيانات في الذاكرة
# ============================
referrals: Dict[str, Dict[str, Any]] = load_json_safely(REFERRALS_FILE)


# ============================
# تهيئة البوت
# ============================
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
BOT_USERNAME = bot.get_me().username


# ============================
# دوال مساعدة
# ============================

def get_display_name(username: str | None, first_name: str | None) -> str:
    if username:
        return f"@{username}"
    return first_name or "مستخدم"


def ensure_user_exists(user_id: str, username: str | None, first_name: str | None) -> None:
    with memory_lock:
        if user_id not in referrals:
            referrals[user_id] = {"username": username or first_name or "", "refs": []}
            save_referrals_to_disk(referrals)


def add_referral_if_valid(ref_id: str, new_user_id: str) -> str | None:
    if ref_id == new_user_id:
        return None
    with memory_lock:
        if ref_id in referrals and new_user_id not in referrals[ref_id].get("refs", []):
            referrals[ref_id]["refs"].append(new_user_id)
            save_referrals_to_disk(referrals)
            return ref_id
    return None


def send_safe(chat_id: int, text: str) -> None:
    try:
        bot.send_message(chat_id, text)
    except Exception:
        pass


# ============================
# الأوامر ومعالجات الأزرار
# ============================
@bot.message_handler(commands=["start"])
def start_handler(message):
    args = message.text.split() if message.text else []
    user_id = str(message.from_user.id)
    username = message.from_user.username
    first_name = message.from_user.first_name

    ensure_user_exists(user_id, username, first_name)

    # معالجة إحالة إن وُجدت
    if len(args) > 1:
        ref_id = args[1].strip()
        added_ref = add_referral_if_valid(ref_id, user_id)
        if added_ref:
            ref_display = get_display_name(
                referrals.get(added_ref, {}).get("username"),
                None,
            )
            new_user_display = get_display_name(username, first_name)

            # رسالة إلى المجموعة إن تم تعريف GROUP_ID
            if GROUP_ID is not None:
                text = f"🎉 تم إحالة {new_user_display} من طرف {ref_display} (ID: {added_ref})."
                send_safe(GROUP_ID, text)

            # رسالة خاصة إلى المُحيل
            try:
                send_safe(int(added_ref), f"🎉 لديك إحالة جديدة من {new_user_display}!")
            except Exception:
                pass

    # لوحة الأزرار
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔗 دخول المجموعة", url=GROUP_JOIN_LINK),
        InlineKeyboardButton("📞 الدعم الفني", url="https://t.me/prohacker41"),
        InlineKeyboardButton("📜 قوانين المجموعة", callback_data="show_rules"),
        InlineKeyboardButton("ℹ️ تعريف الشركة", callback_data="show_company"),
        InlineKeyboardButton("👥 إحالاتي", callback_data="show_refs"),
        InlineKeyboardButton("🏆 أفضل3 الأعضاء", callback_data="show_top"),
        InlineKeyboardButton("🔗 رابط إحالة", callback_data="show_myref"),
    )

    welcome_text = (
        f"مرحبًا بك {get_display_name(username, first_name)} 👋\n\n"
        "هذا بوت خاص بنظام الإحالات لشركة Ultimate.\n\n"
        "لتتعرف على المزيد، استخدم الأزرار بالأسفل."
    )

    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = str(call.from_user.id)

    if call.data == "show_rules":
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            (
                "قوانين المجموعة:\n"
                "- احترام الجميع واجب\n"
                "- في المجموعة نساء ورجال مع عائلاتهم، المجموعة بمثابة عائلة كبيرة\n"
                "- عدم نشر أي روابط أو صور مخالفة لمجال المجموعة\n"
                "- أي تجاوز يتم حظر المستخدم\n"
                "- ڨروب التدريبات خاص فقط بمن فعل حسابه\n"
                "- إحترام المتحدث في البث المباشر\n"
            ),
        )

    elif call.data == "show_company":
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            (
                "شركة Ultimate:\n"
                "شركة جزائرية تعمل على صناعة مواد التجميل الطبيعية والمكملات الغذائية الطبيعية 100٪"
            ),
        )

    elif call.data == "show_refs":
        bot.answer_callback_query(call.id)
        with memory_lock:
            if user_id in referrals:
                user_refs = referrals[user_id].get("refs", [])
                count = len(user_refs)
                if count == 0:
                    text = "ليس لديك أي إحالات حتى الآن."
                else:
                    names: list[str] = []
                    for uid in user_refs:
                        uname = referrals.get(uid, {}).get("username")
                        fname = None
                        names.append(get_display_name(uname, fname))
                    text = f"لديك {count} إحالة:\n" + "\n".join(names)
            else:
                text = "لم يتم تسجيلك في نظام الإحالات بعد. اضغط /start."
        bot.send_message(call.message.chat.id, text)

    elif call.data == "show_top":
        bot.answer_callback_query(call.id)
        with memory_lock:
            sorted_refs = sorted(
                referrals.items(), key=lambda x: len(x[1].get("refs", [])), reverse=True
            )
            top = sorted_refs[:3]
            if not top:
                text = "لا يوجد أعضاء لديهم إحالات حتى الآن."
            else:
                lines = ["🏆 أفضل 3 أعضاء حسب الإحالات:"]
                for i, (uid, data) in enumerate(top, start=1):
                    uname = data.get("username", "غير معروف")
                    count = len(data.get("refs", []))
                    lines.append(f"{i}. @{uname} - {count} إحالة")
                text = "\n".join(lines)
        bot.send_message(call.message.chat.id, text)

    elif call.data == "show_myref":
        bot.answer_callback_query(call.id)
        ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        text = (
            f"🔗 رابط إحالتك الخاص:\n{ref_link}\n\n"
            "شارك هذا الرابط مع أصدقائك ليقوموا بالضغط عليه ويصبحوا من إحالاتك."
        )
        bot.send_message(call.message.chat.id, text)


@bot.message_handler(commands=["ref"])
def ref_handler(message):
    user_id = str(message.from_user.id)
    ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    bot.send_message(message.chat.id, f"🔗 رابط إحالتك الخاص:\n{ref_link}")


if __name__ == "__main__":
    # تشغيل الاستطلاع اللانهائي مع تخطي الرسائل المتراكمة
    bot.infinity_polling(skip_pending=True, timeout=30)
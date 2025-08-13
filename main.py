import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import json

TOKEN = "8083798896:AAEgGBINdsJ25yeGGSI0P0IksZ5LnmKGEMY"
GROUP_ID = -1002649082844
ADMIN_ID = 7112140383  # رقم المشرف

bot = telebot.TeleBot(TOKEN)

REFERRALS_FILE = "referrals.json"
BUTTONS_FILE = "buttons.json"

# تحميل بيانات الإحالات
def load_referrals():
    try:
        with open(REFERRALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_referrals(data):
    with open(REFERRALS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# تحميل أزرار لوحة التحكم
def load_buttons():
    try:
        with open(BUTTONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return [
            {"text": "🔗 دخول المجموعة", "url": "https://t.me/+cVAKJyQd-e84ZDk0"},
            {"text": "📞 الدعم الفني", "url": "https://t.me/prohacker41"},
            {"text": "📜 قوانين المجموعة", "callback_data": "show_rules"},
            {"text": "ℹ️ تعريف الشركة", "callback_data": "show_company"},
            {"text": "👥 إحالاتي", "callback_data": "show_refs"},
            {"text": "🏆 أفضل 3 أعضاء", "callback_data": "show_top"},
            {"text": "🔗 رابط إحالة", "callback_data": "show_myref"}
        ]

def save_buttons(buttons):
    with open(BUTTONS_FILE, "w", encoding="utf-8") as f:
        json.dump(buttons, f, ensure_ascii=False, indent=2)

referrals = load_referrals()
buttons = load_buttons()

def build_markup():
    markup = InlineKeyboardMarkup(row_width=2)
    for btn in buttons:
        if "url" in btn:
            markup.add(InlineKeyboardButton(btn["text"], url=btn["url"]))
        else:
            markup.add(InlineKeyboardButton(btn["text"], callback_data=btn.get("callback_data", "none")))
    return markup

@bot.message_handler(commands=['start'])
def start_handler(message):
    args = message.text.split()
    user_id = str(message.from_user.id)
    username = message.from_user.username or f"@{message.from_user.first_name}"

    if user_id not in referrals:
        referrals[user_id] = {"username": username, "refs": []}

        if len(args) > 1:
            ref_id = args[1]
            if ref_id != user_id and ref_id in referrals:
                referrals[ref_id]["refs"].append(user_id)
                save_referrals(referrals)

                ref_username = referrals.get(ref_id, {}).get("username", f"@{ref_id}")
                text = f"🎉 تم إحالة @{username} من طرف {ref_username}."
                bot.send_message(GROUP_ID, text)
                bot.send_message(ref_id, f"🎉 لديك إحالة جديدة من @{username}!")
                bot.send_message(ADMIN_ID, f"📢 إحالة جديدة:\n@{username} من طرف {ref_username}")

                if len(referrals[ref_id]["refs"]) == 5:
                    bot.send_message(ref_id, "🎉 تهانينا! لقد وصلت إلى 5 إحالات ناجحة! استمر في النجاح 🎉")

    welcome_text = f"""\
مرحبًا بك @{username} 👋

هذا بوت خاص بنظام الإحالات لشركة Ultimate.

لتتعرف على المزيد، استخدم الأزرار بالأسفل.
"""

    bot.send_message(message.chat.id, welcome_text, reply_markup=build_markup())

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = str(call.from_user.id)

    if call.data == "show_rules":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, """\
قوانين المجموعة:
- احترام الجميع واجب
- في المجموعة نساء ورجال مع عائلاتهم، المجموعة بمثابة عائلة كبيرة
- عدم نشر أي روابط أو صور مخالفة لمجال المجموعة
- أي تجاوز يتم حظر المستخدم
- ڨروب التدريبات خاص فقط بمن فعل حسابه
- إحترام المتحدث في البث المباشر
""")

    elif call.data == "show_company":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, """\
شركة Ultimate:
شركة جزائرية تعمل على صناعة مواد التجميل الطبيعية والمكملات الغذائية الطبيعية 100٪
""")

    elif call.data == "show_refs":
        bot.answer_callback_query(call.id)
        if user_id in referrals:
            user_refs = referrals[user_id]["refs"]
            count = len(user_refs)
            if count == 0:
                text = "ليس لديك أي إحالات حتى الآن."
            else:
                names = []
                for uid in user_refs:
                    uname = referrals.get(uid, {}).get("username", "")
                    if uname.startswith("@"):
                        uname_no_at = uname[1:]
                    else:
                        uname_no_at = uname
                    # نعرض اسم المستخدم كرابط
                    names.append(f"<a href='https://t.me/{uname_no_at}'>{uname}</a>")
                text = f"لديك {count} إحالة:\n" + "\n".join(names)
        else:
            text = "لم يتم تسجيلك في نظام الإحالات بعد. اضغط /start."
        bot.send_message(call.message.chat.id, text, parse_mode='HTML')

    elif call.data == "show_top":
        bot.answer_callback_query(call.id)
        sorted_refs = sorted(referrals.items(), key=lambda x: len(x[1]["refs"]), reverse=True)
        top = sorted_refs[:3]
        if not top:
            text = "لا يوجد أعضاء لديهم إحالات حتى الآن."
        else:
            text = "🏆 أفضل 3 أعضاء حسب الإحالات:\n"
            for i, (uid, data) in enumerate(top, start=1):
                uname = data.get("username", "")
                if uname.startswith("@"):
                    uname_no_at = uname[1:]
                else:
                    uname_no_at = uname
                count = len(data["refs"])
                text += f"{i}. <a href='https://t.me/{uname_no_at}'>{uname}</a> - {count} إحالة\n"
        bot.send_message(call.message.chat.id, text, parse_mode='HTML')

    elif call.data == "show_myref":
        bot.answer_callback_query(call.id)
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        text = f"🔗 رابط إحالتك الخاص:\n{ref_link}\n\nشارك هذا الرابط مع أصدقائك ليقوموا بالضغط عليه ويصبحوا من إحالاتك."
        bot.send_message(call.message.chat.id, text)

@bot.message_handler(commands=['ref'])
def ref_handler(message):
    user_id = str(message.from_user.id)
    bot_username = bot.get_me().username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    bot.send_message(message.chat.id, f"🔗 رابط إحالتك الخاص:\n{ref_link}")

@bot.message_handler(commands=['addbutton'])
def add_button_handler(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "ليس لديك صلاحية لاستخدام هذا الأمر.")
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "الاستخدام: /addbutton نص_الزر رابط_أو_callback_data")
        return
    text_btn = parts[1]
    link_or_data = parts[2]
    buttons.append({"text": text_btn, "url": link_or_data})
    save_buttons(buttons)
    bot.reply_to(message, f"تم إضافة الزر: {text_btn}")

@bot.message_handler(commands=['buttons'])
def show_buttons_handler(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "ليس لديك صلاحية لاستخدام هذا الأمر.")
        return
    text = "الأزرار الحالية:\n"
    for i, btn in enumerate(buttons, start=1):
        text += f"{i}. {btn['text']} - {btn.get('url', btn.get('callback_data', ''))}\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['broadcast'])
def broadcast_handler(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "ليس لديك صلاحية لاستخدام هذا الأمر.")
        return
    text = message.text[len('/broadcast '):].strip()
    if not text:
        bot.reply_to(message, "اكتب نص الرسالة بعد الأمر.")
        return

    count = 0
    for user_id in referrals.keys():
        try:
            bot.send_message(user_id, text)
            count += 1
        except Exception as e:
            print(f"خطأ في إرسال رسالة إلى {user_id}: {e}")
    bot.reply_to(message, f"تم إرسال الرسالة إلى {count} مستخدم.")

bot.infinity_polling()

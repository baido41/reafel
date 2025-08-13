import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import json

TOKEN = "8083798896:AAEgGBINdsJ25yeGGSI0P0IksZ5LnmKGEMY"
GROUP_ID = -1002649082844  # ID المجموعة هنا

bot = telebot.TeleBot(TOKEN)

REFERRALS_FILE = "referrals.json"

def load_referrals():
    try:
        with open(REFERRALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_referrals(data):
    with open(REFERRALS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

referrals = load_referrals()

@bot.message_handler(commands=['start'])
def start_handler(message):
    args = message.text.split()
    user_id = str(message.from_user.id)
    username = message.from_user.username or message.from_user.first_name

    if user_id not in referrals:
        referrals[user_id] = {"username": username, "refs": []}

        if len(args) > 1:
            ref_id = args[1]
            if ref_id != user_id and ref_id in referrals:
                referrals[ref_id]["refs"].append(user_id)
                save_referrals(referrals)

                ref_data = referrals.get(ref_id, {})
                ref_username = ref_data.get("username", "غير معروف")
                ref_display = f"@{ref_username}" if ref_username != "غير معروف" else ref_data.get("first_name", "غير معروف")

                text = f"🎉 تم إحالة @{username} من طرف {ref_display} (ID: {ref_id})."
                bot.send_message(GROUP_ID, text)

                bot.send_message(ref_id, f"🎉 لديك إحالة جديدة من @{username}!")

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔗 دخول المجموعة",
                             url="https://t.me/+cVAKJyQd-e84ZDk0"),
        InlineKeyboardButton("📞 الدعم الفني", url="https://t.me/prohacker41"),
        InlineKeyboardButton("📜 قوانين المجموعة", callback_data="show_rules"),
        InlineKeyboardButton("ℹ️ تعريف الشركة", callback_data="show_company"),
        InlineKeyboardButton("👥 إحالاتي", callback_data="show_refs"),
        InlineKeyboardButton("🏆 أفضل3 الأعضاء", callback_data="show_top"),
        InlineKeyboardButton("🔗 رابط إحالة", callback_data="show_myref"))

    welcome_text = f"""\
مرحبًا بك @{username} 👋

هذا بوت خاص بنظام الإحالات لشركة Ultimate.

لتتعرف على المزيد، استخدم الأزرار بالأسفل.
"""

    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = str(call.from_user.id)

    if call.data == "show_rules":
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id, """\
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
        bot.send_message(
            call.message.chat.id, """\
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
                    uname = referrals.get(uid, {}).get("username", "غير معروف")
                    names.append(f"@{uname}")
                text = f"لديك {count} إحالة:\n" + "\n".join(names)
        else:
            text = "لم يتم تسجيلك في نظام الإحالات بعد. اضغط /start."
        bot.send_message(call.message.chat.id, text)

    elif call.data == "show_top":
        bot.answer_callback_query(call.id)
        sorted_refs = sorted(referrals.items(),
                             key=lambda x: len(x[1]["refs"]),
                             reverse=True)
        top = sorted_refs[:3]
        if not top:
            text = "لا يوجد أعضاء لديهم إحالات حتى الآن."
        else:
            text = "🏆 أفضل 3 أعضاء حسب الإحالات:\n"
            for i, (uid, data) in enumerate(top, start=1):
                uname = data.get("username", "غير معروف")
                count = len(data["refs"])
                text += f"{i}. @{uname} - {count} إحالة\n"
        bot.send_message(call.message.chat.id, text)

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

bot.infinity_polling()

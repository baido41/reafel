import psycopg2
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8083798896:AAEgGBINdsJ25yeGGSI0P0IksZ5LnmKGEMY"
GROUP_ID = -1002649082844
ADMIN_ID = 7112140383

bot = telebot.TeleBot(TOKEN)

# بيانات الاتصال بقاعدة البيانات من متغيرات البيئة
import os

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_PORT = os.getenv("DB_PORT")

conn = psycopg2.connect(
    host=DB_HOST,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASS,
    port=DB_PORT
)
conn.autocommit = True
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS referrals (
    user_id VARCHAR PRIMARY KEY,
    username VARCHAR,
    refs TEXT[]
);
""")

def load_referrals():
    cursor.execute("SELECT user_id, username, refs FROM referrals;")
    rows = cursor.fetchall()
    data = {}
    for user_id, username, refs in rows:
        data[user_id] = {"username": username, "refs": refs or []}
    return data

def save_referrals(referrals):
    for user_id, info in referrals.items():
        cursor.execute("""
        INSERT INTO referrals (user_id, username, refs) VALUES (%s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username, refs = EXCLUDED.refs;
        """, (user_id, info['username'], info['refs']))

referrals = load_referrals()

@bot.message_handler(commands=['start'])
def start_handler(message):
    args = message.text.split()
    user_id = str(message.from_user.id)
    username_display = f"@{message.from_user.username}" if message.from_user.username else f"@{message.from_user.first_name}"

    if user_id not in referrals:
        referrals[user_id] = {"username": message.from_user.username or message.from_user.first_name, "refs": []}

        if len(args) > 1:
            ref_id = args[1]
            if ref_id != user_id and ref_id in referrals:
                referrals[ref_id]["refs"].append(user_id)
                save_referrals(referrals)

                ref_display = f"@{referrals[ref_id]['username']}" if referrals[ref_id]['username'] else f"@{ref_id}"

                bot.send_message(GROUP_ID, f"🎉 تم إحالة {username_display} من طرف {ref_display}.")

                if len(referrals[ref_id]["refs"]) == 5:
                    bot.send_message(ref_id, "🎊 مبروك! لقد حصلت على 5 إحالات مباشرة!")

                bot.send_message(ref_id, f"🎉 لديك إحالة جديدة من {username_display}!")

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔗 دخول المجموعة", url="https://t.me/+cVAKJyQd-e84ZDk0"),
        InlineKeyboardButton("📞 الدعم الفني", url="https://t.me/prohacker41"),
        InlineKeyboardButton("📜 قوانين المجموعة", callback_data="show_rules"),
        InlineKeyboardButton("ℹ️ تعريف الشركة", callback_data="show_company"),
        InlineKeyboardButton("👥 إحالاتي", callback_data="show_refs"),
        InlineKeyboardButton("🏆 أفضل3 الأعضاء", callback_data="show_top"),
        InlineKeyboardButton("🔗 رابط إحالة", callback_data="show_myref")
    )

    welcome_text = f"""\
مرحبًا بك {username_display} 👋

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

import json
import psycopg2

# بيانات الاتصال (مثل اللي أعطيتني إياها)
conn = psycopg2.connect(
    host="postgres.railway.internal",
    database="railway",
    user="postgres",
    password="YKIeNosoIwfHQpLuWnVfuqwrWgXhnB",
    port="5432"
)
conn.autocommit = True
cursor = conn.cursor()

# إنشاء الجدول لو مش موجود
cursor.execute("""
CREATE TABLE IF NOT EXISTS referrals (
    user_id VARCHAR PRIMARY KEY,
    username VARCHAR,
    refs TEXT[]
);
""")

# قراءة ملف JSON
with open("referrals.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# إدخال البيانات في قاعدة البيانات
for user_id, info in data.items():
    cursor.execute("""
        INSERT INTO referrals (user_id, username, refs) VALUES (%s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username, refs = EXCLUDED.refs;
    """, (user_id, info.get("username"), info.get("refs", [])))

print("تم رفع كل بيانات الإحالات بنجاح!")
cursor.close()
conn.close()

import os
import sqlite3
import libsql_client
from flask import Flask, jsonify, request, send_from_directory

import import_data
from common import norm

TURSO_URL = os.environ.get("TURSO_DATABASE_URL")

# تحويل الرابط لاستخدام HTTPS بدلاً من WebSocket
if TURSO_URL and TURSO_URL.startswith("libsql://"):
    TURSO_URL = TURSO_URL.replace("libsql://", "https://", 1)
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("DB_PATH", os.path.join(BASE, "gharib.db"))

app = Flask(__name__, static_folder=os.path.join(BASE, "static"), static_url_path="")
app.config["JSON_AS_ASCII"] = False
app.json.ensure_ascii = False

def ensure_db():
    """لو gharib.db غير موجودة، تُبنى من ملف data/words.* تلقائيًا."""
    if os.path.exists(DB):
        return
    for name in ("words.csv", "words.tsv", "words.json", "words.txt", "words.sqlite", "words.db"):
        src = os.path.join(BASE, "data", name)
        if os.path.exists(src):
            n = import_data.build(import_data.load(src), DB)
            print(f"تم بناء القاعدة من {name}: {n} كلمة")
            return
    # لا نوقف السيرفر إذا لم توجد قاعدة بيانات، بل نتركه يعمل ليقوم بالاتصال بـ Turso
    print("تحذير: لا توجد قاعدة بيانات محلية، سيتم الاعتماد على Turso إذا كانت متوفرة.")

# لا نستدعي ensure_db إذا كنا نستخدم Turso
if not (TURSO_URL and TURSO_TOKEN):
    ensure_db()

def query(sql, args=()):
    if TURSO_URL and TURSO_TOKEN:
        # الاتصال بـ Turso
        with libsql_client.create_client_sync(url=TURSO_URL, auth_token=TURSO_TOKEN) as client:
            result = client.execute(sql, args)
            return [dict(row) for row in result.rows]
    else:
        # إذا لم يجد المتغيرات، اطبعها في السجل لنتأكد
        print("!!! خطأ: متغيرات Turso غير موجودة أو غير مقروءة !!!")
        print(f"TURSO_DATABASE_URL: {TURSO_URL}")
        print(f"TURSO_AUTH_TOKEN: {TURSO_TOKEN}")
        # لا نعود للملف المحلي، بل نتوقف هنا لنجبر Render على إظهار المشكلة
        raise ValueError("Turso variables are missing. Please check Render Environment settings.")

def has_asfahany_column():
    """نتحقق مرة واحدة عند بدء التشغيل إذا كان العمود موجوداً"""
    try:
        if TURSO_URL and TURSO_TOKEN:
            with libsql_client.create_client_sync(url=TURSO_URL, auth_token=TURSO_TOKEN) as client:
                result = client.execute("PRAGMA table_info(words)")
                return any(row['name'] == 'Asfahany' for row in result.rows)
        else:
            con = sqlite3.connect(DB)
            cols = con.execute("PRAGMA table_info(words)").fetchall()
            con.close()
            return any(c[1] == 'Asfahany' for c in cols)
    except Exception:
        return False

HAS_ASFAHANY = has_asfahany_column()

def cols():
    """أعمدة الإخراج. حقل Asfahany (a) لا يُرسل إلا عند طلبه بـ ?full=1 أو إذا كان موجوداً."""
    base = "id AS i, word AS w, meaning AS m, ref AS r"
    if HAS_ASFAHANY and request.args.get("full") in ("1", "true"):
        base += ", Asfahany AS a"
    return base

@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route('/sw.js')
def service_worker():
    return send_from_directory(app.static_folder, 'sw.js')

@app.get("/health")
def health():
    return {"ok": True, "words": query("SELECT COUNT(*) AS n FROM words")[0]["n"]}

@app.get("/api/words")
def all_words():
    rows = query(f"SELECT {cols()} FROM words ORDER BY id")
    resp = jsonify(rows)
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp

@app.get("/api/search")
def search():
    q = norm(request.args.get("q", ""))
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = max(int(request.args.get("offset", 0)), 0)
    like = "%" + q.replace("%", "").replace("_", "") + "%"
    
    if HAS_ASFAHANY:
        sql = f"SELECT {cols()} FROM words WHERE word_clean LIKE ? OR COALESCE(NULLIF(asfahany_clean, ''), meaning_clean) LIKE ? ORDER BY id LIMIT ? OFFSET ?"
    else:
        sql = f"SELECT {cols()} FROM words WHERE word_clean LIKE ? OR meaning_clean LIKE ? ORDER BY id LIMIT ? OFFSET ?"
        
    rows = query(sql, (like, like, limit, offset))
    return jsonify(rows)

@app.get("/api/random")
def random_words():
    n = min(int(request.args.get("n", 1)), 20)
    return jsonify(query(f"SELECT {cols()} FROM words ORDER BY RANDOM() LIMIT ?", (n,)))

@app.get("/api/asfahany/<int:word_id>")
def asfahany(word_id):
    """الشرح الأصلي للأصفهاني لكلمة واحدة"""
    if not HAS_ASFAHANY:
        return jsonify({"error": "Asfahany column not found"}), 404
    rows = query("SELECT Asfahany AS a FROM words WHERE id = ?", (word_id,))
    if not rows:
        return jsonify({"error": "not found"}), 404
    resp = jsonify(rows[0])
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return resp

@app.get("/api/debug")
def debug():
    if TURSO_URL and TURSO_TOKEN:
        return {"status": "connected_to_turso", "url_starts_with": TURSO_URL[:10]}
    else:
        return {"status": "connected_to_local_sqlite", "db_path": DB}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

import os
import sqlite3

from flask import Flask, jsonify, request, send_from_directory

import import_data
from common import norm

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
    raise SystemExit("لا توجد قاعدة بيانات ولا ملف data/words.csv")


ensure_db()


def query(sql, args=()):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(sql, args)]
    finally:
        con.close()


def cols():
    """أعمدة الإخراج. حقل Asfahany (a) لا يُرسل إلا عند طلبه بـ ?full=1."""
    base = "id AS i, word AS w, meaning AS m, ref AS r"
    if request.args.get("full") in ("1", "true"):
        base += ", Asfahany AS a"
    return base


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


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
    rows = query(
        f"SELECT {cols()} FROM words "
        "WHERE word_clean LIKE ? OR COALESCE(NULLIF(asfahany_clean, ''), meaning_clean) LIKE ? "
        "ORDER BY id LIMIT ? OFFSET ?",
        (like, like, limit, offset),
    )
    return jsonify(rows)


@app.get("/api/random")
def random_words():
    n = min(int(request.args.get("n", 1)), 20)
    return jsonify(query(f"SELECT {cols()} FROM words ORDER BY RANDOM() LIMIT ?", (n,)))


@app.get("/api/asfahany/<int:word_id>")
def asfahany(word_id):
    """الشرح الأصلي للأصفهاني لكلمة واحدة (يُطلب عند الضغط على «عرض الشرح الكامل»)."""
    rows = query("SELECT Asfahany AS a FROM words WHERE id = ?", (word_id,))
    if not rows:
        return jsonify({"error": "not found"}), 404
    resp = jsonify(rows[0])
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

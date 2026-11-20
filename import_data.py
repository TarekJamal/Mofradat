"""يبني قاعدة gharib.db من ملف بيانات.

أمثلة:
    python import_data.py data/words.csv
    python import_data.py mydb.sqlite --table words --word-col word --meaning-col text
"""
import argparse
import csv
import io
import json
import os
import sqlite3

from common import norm

HEAD = {"word", "الكلمة", "كلمة", "w"}
WORD_NAMES = ["word", "الكلمة", "كلمة", "name", "w"]
MEAN_NAMES = ["meaning", "text", "الشرح", "النص", "المعنى", "explanation", "definition", "m"]
REF_NAMES = ["ref", "السورة", "surah", "r"]


def read_text(path):
    for enc in ("utf-8-sig", "utf-8", "cp1256"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise SystemExit("تعذرت قراءة الملف، احفظه بترميز UTF-8")


def pick(d, names):
    for n in names:
        if d.get(n):
            return d[n]
    return ""


def from_json(text):
    data = json.loads(text)
    if isinstance(data, dict):
        data = data.get("data") or data.get("words") or [[k, v] for k, v in data.items()]
    rows = []
    for r in data:
        if isinstance(r, (list, tuple)):
            rows.append((r[0], r[1] if len(r) > 1 else "", r[2] if len(r) > 2 else ""))
        elif isinstance(r, dict):
            rows.append((pick(r, WORD_NAMES), pick(r, MEAN_NAMES), pick(r, REF_NAMES)))
    return rows


def from_delimited(text):
    first = text.splitlines()[0] if text.strip() else ""
    delim = "\t" if "\t" in first else ","
    rows = []
    for row in csv.reader(io.StringIO(text), delimiter=delim):
        if len(row) < 2:
            continue
        if len(row) == 3:
            rows.append((row[0], row[1], row[2]))
        else:  # فواصل غير مقتبسة داخل الشرح
            rows.append((row[0], delim.join(row[1:]), ""))
    return rows


def from_sqlite(path, table=None, wcol=None, mcol=None, rcol=None):
    con = sqlite3.connect(path)
    if not table:
        t = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()
        if not t:
            raise SystemExit("لا توجد جداول في القاعدة")
        table = t[0]
    cols = [c[1] for c in con.execute(f'PRAGMA table_info("{table}")')]
    data_cols = [c for c in cols if c.lower() not in ("id", "rowid")]
    wcol = wcol or next((c for c in cols if c.lower() in WORD_NAMES or c in WORD_NAMES), data_cols[0])
    mcol = mcol or next((c for c in cols if c.lower() in MEAN_NAMES or c in MEAN_NAMES), data_cols[1])
    rcol = rcol or next((c for c in cols if c.lower() in REF_NAMES or c in REF_NAMES), None)
    print(f"الجدول: {table} | الكلمة: {wcol} | الشرح: {mcol} | السورة: {rcol}")
    q = f'SELECT "{wcol}", "{mcol}", ' + (f'"{rcol}"' if rcol else "''") + f' FROM "{table}"'
    rows = con.execute(q).fetchall()
    con.close()
    return rows


def load(path, **kw):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".db", ".sqlite", ".sqlite3"):
        return from_sqlite(path, **kw)
    text = read_text(path)
    if ext == ".json":
        return from_json(text)
    return from_delimited(text)


def build(rows, out):
    clean, seen = [], set()
    for w, m, r in rows:
        w, m, r = str(w or "").strip(), str(m or "").strip(), str(r or "").strip()
        if not w or not m or w.lower() in HEAD or (w, m) in seen:
            continue
        seen.add((w, m))
        clean.append((w, norm(w), m, norm(m), r))
    if os.path.exists(out):
        os.remove(out)
    con = sqlite3.connect(out)
    con.executescript(
        """
        CREATE TABLE words(
          id INTEGER PRIMARY KEY,
          word TEXT NOT NULL, word_clean TEXT NOT NULL,
          meaning TEXT NOT NULL, meaning_clean TEXT NOT NULL,
          ref TEXT DEFAULT ''
        );
        CREATE INDEX idx_word_clean ON words(word_clean);
        """
    )
    con.executemany("INSERT INTO words(word,word_clean,meaning,meaning_clean,ref) VALUES(?,?,?,?,?)", clean)
    con.commit()
    con.close()
    return len(clean)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--out", default="gharib.db")
    ap.add_argument("--table")
    ap.add_argument("--word-col")
    ap.add_argument("--meaning-col")
    ap.add_argument("--ref-col")
    a = ap.parse_args()
    extra = {}
    if a.src.lower().endswith((".db", ".sqlite", ".sqlite3")):
        extra = dict(table=a.table, wcol=a.word_col, mcol=a.meaning_col, rcol=a.ref_col)
    n = build(load(a.src, **extra), a.out)
    print(f"تم: {n} كلمة في {a.out}")

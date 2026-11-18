"""طبقة الوصول إلى قاعدة بيانات SQLite. كل الاستعلامات بصيغة Parameterized Queries."""
import sqlite3
from flask import g
import config


def connect(read_only=False):
    """يفتح اتصالاً جديداً، ويفعّل المفاتيح الأجنبية."""
    if read_only:
        conn = sqlite3.connect(f"file:{config.DATABASE_PATH}?mode=ro", uri=True, timeout=10)
    else:
        conn = sqlite3.connect(config.DATABASE_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    """اتصال واحد لكل طلب HTTP يُحفظ في كائن g."""
    if "db" not in g:
        g.db = connect()
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, params=(), one=False):
    cur = get_db().execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    if one:
        return dict(rows[0]) if rows else None
    return [dict(r) for r in rows]


def execute(sql, params=(), commit=True):
    db = get_db()
    cur = db.execute(sql, params)
    if commit:
        db.commit()
    return cur.lastrowid

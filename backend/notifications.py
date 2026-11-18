"""الإشعارات داخل النظام. الروابط مسارات داخلية نسبية فقط."""
from backend.db import execute, query
from backend.dates import now_iso


def safe_link(link):
    if not link or not isinstance(link, str) or not link.startswith("/") or link.startswith("//"):
        return None
    return link


def notify(user_id, title, body, link=None, dedupe=False, commit=True):
    if user_id is None:
        return
    link = safe_link(link)
    if dedupe and query("SELECT id FROM notifications WHERE user_id = ? AND title = ? AND body = ?",
                        (user_id, title, body), one=True):
        return
    execute("INSERT INTO notifications (user_id, title, body, link, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, title, body, link, now_iso()), commit=commit)


def notify_role(role, title, body, link=None):
    for u in query("SELECT id FROM users WHERE role = ? AND is_active = 1", (role,)):
        notify(u["id"], title, body, link, commit=False)

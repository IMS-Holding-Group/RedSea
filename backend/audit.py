"""سجل التدقيق. يُمنع تمرير أي بيانات حساسة في details."""
from flask import request, g
from backend.db import execute
from backend.dates import now_iso


def log_action(action, entity=None, entity_id=None, details=None, user_id=None, commit=True):
    uid = user_id if user_id is not None else (g.user["id"] if getattr(g, "user", None) else None)
    ip = request.remote_addr if request else None
    execute("INSERT INTO audit_log (user_id, action, entity, entity_id, details, ip_address, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)", (uid, action, entity, entity_id, details, ip, now_iso()), commit=commit)

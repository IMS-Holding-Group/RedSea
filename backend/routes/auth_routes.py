import secrets
from flask import Blueprint, g, request, make_response, jsonify

from backend.db import query, execute
from backend.dates import now_iso
from backend.routes import body
from backend.security import (ok, fail, login_required, create_session, set_session_cookie, revoke_session,
                              check_password, hash_password, login_locked, record_attempt, v_email, v_password,
                              v_text, v_phone, ANON_CSRF_COOKIE, SESSION_COOKIE)
from backend.audit import log_action
import config

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.get("/csrf")
def csrf():
    token = secrets.token_urlsafe(32)
    resp = make_response(jsonify({"ok": True, "data": {"csrf": token, "demo": not config.IS_PRODUCTION}}))
    resp.set_cookie(ANON_CSRF_COOKIE, token, httponly=True, secure=config.IS_PRODUCTION, samesite="Strict", max_age=3600)
    return resp


@bp.post("/login")
def login():
    data = body()
    email = (data.get("email") or "").strip().lower()[:120]
    password = data.get("password") or ""
    if not email or not password:
        return fail("يرجى إدخال البريد الإلكتروني وكلمة السر.")
    identifier = f"{email}|{request.remote_addr}"
    if login_locked(identifier):
        return fail("تم إيقاف محاولات الدخول مؤقتاً بسبب كثرة المحاولات الفاشلة. حاول بعد 15 دقيقة.", 429)
    user = query("SELECT * FROM users WHERE email = ?", (email,), one=True)
    if not user or not user["is_active"] or not check_password(password, user["password_hash"]):
        record_attempt(identifier, False)
        return fail("البريد الإلكتروني أو كلمة السر غير صحيحة.", 401)
    record_attempt(identifier, True)
    sid, csrf_token = create_session(user["id"])
    execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now_iso(), user["id"]))
    log_action("login", "users", user["id"], user_id=user["id"])
    resp = make_response(jsonify({"ok": True, "data": {"role": user["role"], "csrf": csrf_token}}))
    set_session_cookie(resp, sid)
    resp.delete_cookie(ANON_CSRF_COOKIE)
    return resp


@bp.post("/register")
def register():
    data = body()
    name = v_text(data, "full_name", "الاسم الكامل", 3, 80)
    email = v_email(data)
    phone = v_phone(data, required=True)
    password = v_password(data)
    if query("SELECT id FROM users WHERE email = ?", (email,), one=True):
        return fail("البريد الإلكتروني مسجل مسبقاً.", 409)
    uid = execute("INSERT INTO users (full_name, email, phone, password_hash, role, created_at) VALUES (?, ?, ?, ?, 'tourist', ?)",
                  (name, email, phone, hash_password(password), now_iso()))
    log_action("register", "users", uid, user_id=uid)
    return ok({"id": uid}, 201)


@bp.post("/logout")
def logout():
    if g.get("user"):
        log_action("logout", "users", g.user["id"])
    revoke_session()
    resp = make_response(jsonify({"ok": True, "data": None}))
    resp.delete_cookie(SESSION_COOKIE, path="/")
    return resp


@bp.get("/me")
def me():
    if not g.get("user"):
        return ok(None)
    return ok({**g.user, "csrf": g.session["csrf_token"], "dev": not config.IS_PRODUCTION})


@bp.put("/profile")
@login_required
def update_profile():
    data = body()
    name = v_text(data, "full_name", "الاسم الكامل", 3, 80)
    phone = v_phone(data)
    execute("UPDATE users SET full_name = ?, phone = ? WHERE id = ?", (name, phone, g.user["id"]))
    log_action("update_profile", "users", g.user["id"])
    return ok()


@bp.put("/password")
@login_required
def change_password():
    data = body()
    user = query("SELECT password_hash FROM users WHERE id = ?", (g.user["id"],), one=True)
    if not check_password(data.get("current_password") or "", user["password_hash"]):
        return fail("كلمة السر الحالية غير صحيحة.")
    new = v_password(data, "new_password")
    execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(new), g.user["id"]))
    execute("UPDATE sessions SET revoked = 1 WHERE user_id = ? AND id != ?", (g.user["id"], g.session["id"]))
    log_action("change_password", "users", g.user["id"])
    return ok()

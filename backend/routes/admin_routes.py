from flask import Blueprint, g, request, abort
from backend.db import query, execute
from backend.dates import now_iso
from backend.routes import body
from backend.security import ok, fail, role_required, v_text, v_email, v_phone, v_password, v_choice, hash_password
from backend.audit import log_action

bp = Blueprint("admin", __name__, url_prefix="/api/admin")
ROLES = ("admin", "marina_manager", "owner", "tourist", "provider")


@bp.get("/users")
@role_required("admin")
def users():
    sql = "SELECT id, full_name, email, phone, role, is_active, created_at, last_login_at FROM users"
    params = []
    if request.args.get("role") in ROLES:
        sql += " WHERE role = ?"
        params.append(request.args["role"])
    return ok(query(sql + " ORDER BY id", params))


@bp.post("/users")
@role_required("admin")
def create_user():
    d = body()
    name = v_text(d, "full_name", "الاسم", 3, 80)
    email = v_email(d)
    phone = v_phone(d)
    role = v_choice(d, "role", "الدور", ROLES)
    pwd = v_password(d)
    if query("SELECT id FROM users WHERE email = ?", (email,), one=True):
        return fail("البريد الإلكتروني مسجل مسبقاً.", 409)
    uid = execute("INSERT INTO users (full_name, email, phone, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                  (name, email, phone, hash_password(pwd), role, now_iso()))
    if role == "provider":
        services = v_text(d, "services", "الخدمات", 0, 200, required=False) or "maintenance,cleaning"
        execute("INSERT INTO provider_profiles (user_id, company_name, services) VALUES (?, ?, ?)", (uid, name, services))
    log_action("create_user", "users", uid, f"role={role}")
    return ok({"id": uid}, 201)


@bp.put("/users/<int:uid>")
@role_required("admin")
def update_user(uid):
    if not query("SELECT id FROM users WHERE id = ?", (uid,), one=True):
        abort(404)
    d = body()
    role = v_choice(d, "role", "الدور", ROLES)
    if uid == g.user["id"] and role != "admin":
        return fail("لا يمكنك تغيير دورك الإداري.")
    execute("UPDATE users SET full_name = ?, phone = ?, role = ? WHERE id = ?",
            (v_text(d, "full_name", "الاسم", 3, 80), v_phone(d), role, uid))
    log_action("update_user", "users", uid)
    return ok()


@bp.post("/users/<int:uid>/toggle")
@role_required("admin")
def toggle(uid):
    if uid == g.user["id"]:
        return fail("لا يمكنك تعطيل حسابك.")
    u = query("SELECT is_active FROM users WHERE id = ?", (uid,), one=True)
    if not u:
        abort(404)
    new = 0 if u["is_active"] else 1
    execute("UPDATE users SET is_active = ? WHERE id = ?", (new, uid))
    if not new:
        execute("UPDATE sessions SET revoked = 1 WHERE user_id = ?", (uid,))
    log_action("toggle_user", "users", uid, f"active={new}")
    return ok({"is_active": new})


@bp.get("/audit")
@role_required("admin")
def audit():
    sql = ("SELECT a.*, u.full_name, u.email FROM audit_log a LEFT JOIN users u ON u.id = a.user_id WHERE 1 = 1")
    params = []
    action = (request.args.get("action") or "").strip()[:50]
    if action:
        sql += " AND a.action LIKE ?"
        params.append(f"%{action}%")
    if request.args.get("user_id", "").isdigit():
        sql += " AND a.user_id = ?"
        params.append(int(request.args["user_id"]))
    return ok(query(sql + " ORDER BY a.id DESC LIMIT 300", params))

"""الأمان: تجزئة كلمات السر، الجلسات، CSRF، الصلاحيات، تحديد المحاولات، التحقق من المدخلات والملفات."""
import hashlib
import hmac
import re
import secrets
import time
from datetime import timedelta
from functools import wraps

import bcrypt
from flask import g, request, jsonify, redirect

import config
from backend.db import query, execute
from backend.dates import now_utc, now_iso, parse_iso, to_iso

SESSION_COOKIE = "ry_sid"
ANON_CSRF_COOKIE = "ry_acsrf"


class ValidationError(Exception):
    """خطأ تحقق تُعرض رسالته العربية للمستخدم كما هي."""


# ---------- الاستجابات الموحدة ----------
def ok(data=None, status=200):
    return jsonify({"ok": True, "data": data}), status


def fail(message, status=400):
    return jsonify({"ok": False, "error": message}), status


# ---------- كلمات السر والمفاتيح ----------
def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def check_password(password, hashed):
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def hash_key(key):
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


# ---------- الجلسات ----------
def create_session(user_id):
    sid = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    now = now_iso()
    execute("INSERT INTO sessions (id, user_id, csrf_token, created_at, last_seen_at, ip_address, user_agent) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (hash_key(sid), user_id, csrf, now, now, request.remote_addr, (request.user_agent.string or "")[:200]))
    return sid, csrf


def load_session():
    """يحمل المستخدم من كوكي الجلسة ويطبق انتهاء الصلاحية بعد مدة الخمول."""
    g.user = None
    g.session = None
    sid = request.cookies.get(SESSION_COOKIE)
    if not sid:
        return
    row = query("SELECT s.*, u.full_name, u.email, u.role, u.is_active, u.phone FROM sessions s "
                "JOIN users u ON u.id = s.user_id WHERE s.id = ? AND s.revoked = 0", (hash_key(sid),), one=True)
    if not row or not row["is_active"]:
        return
    last = parse_iso(row["last_seen_at"])
    if last is None or now_utc() - last > timedelta(minutes=config.SESSION_IDLE_MINUTES):
        execute("UPDATE sessions SET revoked = 1 WHERE id = ?", (row["id"],))
        return
    execute("UPDATE sessions SET last_seen_at = ? WHERE id = ?", (now_iso(), row["id"]))
    g.session = row
    g.user = {"id": row["user_id"], "full_name": row["full_name"], "email": row["email"],
              "role": row["role"], "phone": row["phone"]}


def revoke_session():
    if g.get("session"):
        execute("UPDATE sessions SET revoked = 1 WHERE id = ?", (g.session["id"],))


def set_session_cookie(resp, sid):
    resp.set_cookie(SESSION_COOKIE, sid, httponly=True, secure=config.IS_PRODUCTION, samesite="Lax",
                    max_age=12 * 3600, path="/")


# ---------- CSRF ----------
def verify_csrf():
    """يتحقق من رمز CSRF لكل طلب يغير البيانات."""
    token = request.headers.get("X-CSRF-Token", "")
    if g.get("session"):
        return bool(token) and hmac.compare_digest(token, g.session["csrf_token"])
    cookie = request.cookies.get(ANON_CSRF_COOKIE, "")
    return bool(token) and bool(cookie) and hmac.compare_digest(token, cookie)


# ---------- الصلاحيات ----------
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not g.get("user"):
            return fail("يجب تسجيل الدخول أولاً.", 401)
        return fn(*args, **kwargs)
    return wrapper


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not g.get("user"):
                return fail("يجب تسجيل الدخول أولاً.", 401)
            if g.user["role"] not in roles:
                return fail("ليست لديك صلاحية لتنفيذ هذا الإجراء.", 403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ---------- تحديد محاولات الدخول ----------
MAX_ATTEMPTS = 5
LOCK_MINUTES = 15


def login_locked(identifier):
    since = to_iso(now_utc() - timedelta(minutes=LOCK_MINUTES))
    row = query("SELECT COUNT(*) AS c FROM login_attempts WHERE identifier = ? AND success = 0 AND attempted_at >= ?",
                (identifier, since), one=True)
    return row["c"] >= MAX_ATTEMPTS


def record_attempt(identifier, success):
    execute("INSERT INTO login_attempts (identifier, attempted_at, success) VALUES (?, ?, ?)",
            (identifier, now_iso(), 1 if success else 0))
    if success:
        execute("DELETE FROM login_attempts WHERE identifier = ? AND success = 0", (identifier,))


_rate_buckets = {}


def rate_limited(key, limit, window_seconds):
    """تحديد معدل بسيط في الذاكرة (مثل طلبات أجهزة GPS)."""
    now = time.time()
    bucket = [t for t in _rate_buckets.get(key, []) if now - t < window_seconds]
    if len(bucket) >= limit:
        _rate_buckets[key] = bucket
        return True
    bucket.append(now)
    _rate_buckets[key] = bucket
    return False


# ---------- التحقق من المدخلات ----------
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^05\d{8}$")


def v_text(data, key, label, min_len=1, max_len=200, required=True):
    val = data.get(key)
    if val is None or (isinstance(val, str) and not val.strip()):
        if required:
            raise ValidationError(f"حقل {label} مطلوب.")
        return None
    if not isinstance(val, str):
        raise ValidationError(f"قيمة {label} غير صالحة.")
    val = val.strip()
    if len(val) < min_len or len(val) > max_len:
        raise ValidationError(f"طول {label} يجب أن يكون بين {min_len} و{max_len} حرفاً.")
    return val


def v_email(data, key="email"):
    val = v_text(data, key, "البريد الإلكتروني", 5, 120).lower()
    if not EMAIL_RE.match(val):
        raise ValidationError("صيغة البريد الإلكتروني غير صحيحة.")
    return val


def v_phone(data, key="phone", required=False):
    val = v_text(data, key, "رقم الجوال", 10, 10, required)
    if val is not None and not PHONE_RE.match(val):
        raise ValidationError("رقم الجوال يجب أن يبدأ بـ 05 ويتكون من 10 أرقام.")
    return val


def v_int(data, key, label, min_v, max_v, required=True):
    val = data.get(key)
    if val is None or val == "":
        if required:
            raise ValidationError(f"حقل {label} مطلوب.")
        return None
    try:
        num = int(val)
    except (TypeError, ValueError):
        raise ValidationError(f"قيمة {label} يجب أن تكون رقماً صحيحاً.")
    if isinstance(val, float) and val != num:
        raise ValidationError(f"قيمة {label} يجب أن تكون رقماً صحيحاً.")
    if num < min_v or num > max_v:
        raise ValidationError(f"قيمة {label} يجب أن تكون بين {min_v} و{max_v}.")
    return num


def v_float(data, key, label, min_v, max_v, required=True):
    val = data.get(key)
    if val is None or val == "":
        if required:
            raise ValidationError(f"حقل {label} مطلوب.")
        return None
    try:
        num = float(val)
    except (TypeError, ValueError):
        raise ValidationError(f"قيمة {label} يجب أن تكون رقماً.")
    if num != num or num < min_v or num > max_v:
        raise ValidationError(f"قيمة {label} يجب أن تكون بين {min_v} و{max_v}.")
    return num


def v_choice(data, key, label, choices, required=True):
    val = data.get(key)
    if val in (None, ""):
        if required:
            raise ValidationError(f"حقل {label} مطلوب.")
        return None
    if val not in choices:
        raise ValidationError(f"قيمة {label} غير مسموحة.")
    return val


def v_datetime(data, key, label, required=True):
    val = data.get(key)
    if val in (None, ""):
        if required:
            raise ValidationError(f"حقل {label} مطلوب.")
        return None
    dt = parse_iso(val)
    if dt is None:
        raise ValidationError(f"صيغة {label} غير صحيحة.")
    return dt


def v_password(data, key="password"):
    val = data.get(key)
    if not isinstance(val, str) or len(val) < 8 or len(val) > 128:
        raise ValidationError("كلمة السر يجب أن تتكون من 8 إلى 128 حرفاً.")
    if not re.search(r"[A-Za-z]", val) or not re.search(r"\d", val):
        raise ValidationError("كلمة السر يجب أن تحتوي على حروف وأرقام.")
    return val


RED_SEA_BOUNDS = {"lat": (12.0, 30.0), "lng": (32.0, 44.0)}


def in_red_sea(lat, lng):
    return RED_SEA_BOUNDS["lat"][0] <= lat <= RED_SEA_BOUNDS["lat"][1] and \
        RED_SEA_BOUNDS["lng"][0] <= lng <= RED_SEA_BOUNDS["lng"][1]


def v_polygon(points):
    if not isinstance(points, list) or len(points) < 3 or len(points) > 100:
        raise ValidationError("المضلع يجب أن يحتوي من 3 إلى 100 نقطة.")
    clean = []
    for p in points:
        if not isinstance(p, (list, tuple)) or len(p) != 2:
            raise ValidationError("نقاط المضلع غير صالحة.")
        try:
            lat, lng = float(p[0]), float(p[1])
        except (TypeError, ValueError):
            raise ValidationError("نقاط المضلع غير صالحة.")
        if not in_red_sea(lat, lng):
            raise ValidationError("نقاط المضلع يجب أن تكون ضمن نطاق البحر الأحمر.")
        clean.append([round(lat, 6), round(lng, 6)])
    return clean


def safe_next(value):
    """يمنع إعادة التوجيه المفتوح: يُقبل المسار الداخلي فقط."""
    if isinstance(value, str) and value.startswith("/") and not value.startswith("//") and "\\" not in value:
        return value
    return "/"


# ---------- فحص الملفات المرفوعة ----------
MAGIC = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/webp": [b"RIFF"],
    "application/pdf": [b"%PDF-"],
}
EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "application/pdf": ".pdf"}


def detect_mime(head):
    for mime, sigs in MAGIC.items():
        for s in sigs:
            if head.startswith(s):
                if mime == "image/webp" and head[8:12] != b"WEBP":
                    continue
                return mime
    return None


def read_upload(file_storage, allowed, max_bytes):
    """يقرأ الملف ويتحقق من نوعه الحقيقي وحجمه، ويعيد (البايتات، النوع)."""
    if file_storage is None or not file_storage.filename:
        raise ValidationError("لم يتم اختيار ملف.")
    data = file_storage.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValidationError(f"حجم الملف يتجاوز الحد المسموح ({max_bytes // (1024 * 1024)} ميجابايت).")
    mime = detect_mime(data[:16])
    if mime not in allowed:
        raise ValidationError("نوع الملف غير مسموح.")
    return data, mime


def random_filename(mime):
    return secrets.token_hex(16) + EXT[mime]


def login_redirect():
    return redirect("/login?next=" + safe_next(request.full_path.rstrip("?")))

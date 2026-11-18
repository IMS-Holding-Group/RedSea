import os
import secrets
from datetime import timedelta

from flask import Blueprint, g, request, send_file, abort

import config
from backend.db import query, execute, get_db
from backend.dates import now_iso, now_utc, parse_iso
from backend.routes import body, money
from backend.security import (ok, fail, role_required, login_required, v_text, v_float, v_int, v_choice, read_upload,
                              random_filename, hash_key, ValidationError)
from backend.services import booking_service, maintenance_service, compliance_service
from backend.audit import log_action

bp = Blueprint("yachts", __name__)
TYPES = {"motor": "يخت بمحرك", "sailing": "شراعي", "catamaran": "مزدوج البدن"}
IMAGE_TYPES = ("image/jpeg", "image/png", "image/webp")


def size_class(length):
    return "small" if length < 12 else ("medium" if length <= 24 else "large")


def yacht_public(y):
    photos = query("SELECT id FROM yacht_photos WHERE yacht_id = ? ORDER BY id", (y["id"],))
    return {"id": y["id"], "name": y["name"], "type": y["type"], "type_label": TYPES.get(y["type"], y["type"]),
            "length_m": y["length_m"], "beam_m": y["beam_m"], "draft_m": y["draft_m"], "capacity": y["capacity"],
            "cabins": y["cabins"], "size_class": y["size_class"], "hourly_rate": money(y["hourly_rate_halalas"]),
            "description": y["description"], "status": y["status"], "marina_id": y["home_marina_id"],
            "marina_name": y.get("marina_name"), "marina_city": y.get("marina_city"),
            "photos": [f"/media/yachts/{p['id']}" for p in photos]}


def own_yacht(yid):
    y = query("SELECT * FROM yachts WHERE id = ? AND owner_id = ?", (yid, g.user["id"]), one=True)
    if not y:
        abort(404)
    return y


@bp.get("/api/yachts")
def search():
    args = request.args
    sql = ("SELECT y.*, m.name AS marina_name, m.city AS marina_city FROM yachts y JOIN marinas m ON m.id = y.home_marina_id "
           "WHERE y.status = 'active'")
    params = []
    if args.get("marina_id", "").isdigit():
        sql += " AND y.home_marina_id = ?"
        params.append(int(args["marina_id"]))
    if args.get("type") in TYPES:
        sql += " AND y.type = ?"
        params.append(args["type"])
    if args.get("guests", "").isdigit():
        sql += " AND y.capacity >= ?"
        params.append(int(args["guests"]))
    if args.get("max_price", "").isdigit():
        sql += " AND y.hourly_rate_halalas <= ?"
        params.append(int(args["max_price"]) * 100)
    sql += " ORDER BY y.hourly_rate_halalas"
    start = parse_iso(args.get("start", ""))
    hours = int(args["hours"]) if args.get("hours", "").isdigit() else 4
    result = []
    for y in query(sql, params):
        item = yacht_public(y)
        if start:
            end = start + timedelta(hours=max(2, min(12, hours)))
            reasons, weather = booking_service.availability_check(y, start, end, None)
            item["weather"] = weather["status"]
            item["weather_source"] = weather["source"]
            item["available"] = not reasons
            item["reasons"] = reasons
        result.append(item)
    return ok(result)


@bp.get("/api/yachts/<int:yid>")
def details(yid):
    y = query("SELECT y.*, m.name AS marina_name, m.city AS marina_city, m.latitude, m.longitude FROM yachts y "
              "JOIN marinas m ON m.id = y.home_marina_id WHERE y.id = ? AND y.status IN ('active','maintenance')", (yid,), one=True)
    if not y:
        return fail("اليخت غير موجود.", 404)
    item = yacht_public(y)
    item["marina_lat"], item["marina_lng"] = y["latitude"], y["longitude"]
    item["cruising_zones"] = query("SELECT id, name FROM zones WHERE zone_type = 'cruising_area' AND is_active = 1")
    return ok(item)


def read_yacht_form(data):
    out = {
        "name": v_text(data, "name", "اسم اليخت", 2, 60),
        "registration_no": v_text(data, "registration_no", "رقم التسجيل", 4, 30),
        "type": v_choice(data, "type", "النوع", TYPES),
        "length_m": v_float(data, "length_m", "الطول", 4, 120),
        "beam_m": v_float(data, "beam_m", "العرض", 1.5, 30),
        "draft_m": v_float(data, "draft_m", "الغاطس", 0.3, 8),
        "capacity": v_int(data, "capacity", "السعة", 1, 200),
        "cabins": v_int(data, "cabins", "الكبائن", 0, 30),
        "home_marina_id": v_int(data, "home_marina_id", "المرسى", 1, 10 ** 9),
        "hourly_rate_halalas": int(round(v_float(data, "hourly_rate", "السعر بالساعة", 50, 100000) * 100)),
        "description": v_text(data, "description", "الوصف", 0, 1000, required=False) or "",
        "status": v_choice(data, "status", "الحالة", ("active", "draft", "suspended"), required=False) or "active",
    }
    if not query("SELECT id FROM marinas WHERE id = ? AND is_active = 1", (out["home_marina_id"],), one=True):
        raise ValidationError("المرسى المختار غير موجود.")
    out["size_class"] = size_class(out["length_m"])
    return out


@bp.get("/api/owner/yachts")
@role_required("owner")
def owner_list():
    rows = query("SELECT y.*, m.name AS marina_name FROM yachts y JOIN marinas m ON m.id = y.home_marina_id "
                 "WHERE y.owner_id = ? ORDER BY y.id", (g.user["id"],))
    out = []
    for y in rows:
        item = yacht_public(y)
        item.update({"registration_no": y["registration_no"], "engine_hours": y["engine_hours"],
                     "compliance": compliance_service.compliance_score(y["id"]),
                     "device": query("SELECT device_code, last_seen_at FROM gps_devices WHERE yacht_id = ?", (y["id"],), one=True),
                     "photo_ids": [p["id"] for p in query("SELECT id FROM yacht_photos WHERE yacht_id = ?", (y["id"],))]})
        out.append(item)
    return ok(out)


@bp.post("/api/owner/yachts")
@role_required("owner")
def owner_create():
    f = read_yacht_form(body())
    if query("SELECT id FROM yachts WHERE registration_no = ?", (f["registration_no"],), one=True):
        return fail("رقم التسجيل مستخدم ليخت آخر.", 409)
    db = get_db()
    cur = db.execute("INSERT INTO yachts (owner_id, name, registration_no, type, length_m, beam_m, draft_m, capacity, cabins, "
                     "size_class, home_marina_id, hourly_rate_halalas, description, engine_hours, status, created_at) "
                     "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
                     (g.user["id"], f["name"], f["registration_no"], f["type"], f["length_m"], f["beam_m"], f["draft_m"],
                      f["capacity"], f["cabins"], f["size_class"], f["home_marina_id"], f["hourly_rate_halalas"],
                      f["description"], f["status"], now_iso()))
    yid = cur.lastrowid
    maintenance_service.create_default_plans(db, yid, 0, commit=False)
    db.commit()
    log_action("create_yacht", "yachts", yid)
    return ok({"id": yid}, 201)


@bp.put("/api/owner/yachts/<int:yid>")
@role_required("owner")
def owner_update(yid):
    y = own_yacht(yid)
    f = read_yacht_form(body())
    if query("SELECT id FROM yachts WHERE registration_no = ? AND id != ?", (f["registration_no"], yid), one=True):
        return fail("رقم التسجيل مستخدم ليخت آخر.", 409)
    if y["status"] == "maintenance":
        f["status"] = "maintenance"
    execute("UPDATE yachts SET name = ?, registration_no = ?, type = ?, length_m = ?, beam_m = ?, draft_m = ?, capacity = ?, "
            "cabins = ?, size_class = ?, home_marina_id = ?, hourly_rate_halalas = ?, description = ?, status = ? WHERE id = ?",
            (f["name"], f["registration_no"], f["type"], f["length_m"], f["beam_m"], f["draft_m"], f["capacity"], f["cabins"],
             f["size_class"], f["home_marina_id"], f["hourly_rate_halalas"], f["description"], f["status"], yid))
    log_action("update_yacht", "yachts", yid)
    return ok()


@bp.post("/api/owner/yachts/<int:yid>/photos")
@role_required("owner")
def upload_photo(yid):
    own_yacht(yid)
    if query("SELECT COUNT(*) AS c FROM yacht_photos WHERE yacht_id = ?", (yid,), one=True)["c"] >= 5:
        return fail("الحد الأقصى 5 صور لكل يخت.")
    f = request.files.get("photo")
    data, mime = read_upload(f, IMAGE_TYPES, 3 * 1024 * 1024)
    name = random_filename(mime)
    with open(os.path.join(config.UPLOAD_DIR, "yachts", name), "wb") as out:
        out.write(data)
    original = os.path.basename(f.filename)[:100]
    pid = execute("INSERT INTO yacht_photos (yacht_id, stored_name, original_name, mime_type, size_bytes, uploaded_at) "
                  "VALUES (?, ?, ?, ?, ?, ?)", (yid, name, original, mime, len(data), now_iso()))
    log_action("upload_photo", "yachts", yid)
    return ok({"id": pid}, 201)


@bp.delete("/api/owner/yachts/<int:yid>/photos/<int:pid>")
@role_required("owner")
def delete_photo(yid, pid):
    own_yacht(yid)
    p = query("SELECT * FROM yacht_photos WHERE id = ? AND yacht_id = ?", (pid, yid), one=True)
    if not p:
        return fail("الصورة غير موجودة.", 404)
    path = os.path.join(config.UPLOAD_DIR, "yachts", os.path.basename(p["stored_name"]))
    if os.path.exists(path):
        os.remove(path)
    execute("DELETE FROM yacht_photos WHERE id = ?", (pid,))
    return ok()


@bp.post("/api/owner/yachts/<int:yid>/device")
@role_required("owner")
def device(yid):
    """ينشئ أو يجدد مفتاح جهاز GPS. المفتاح يظهر مرة واحدة فقط ويخزن كتجزئة."""
    own_yacht(yid)
    key = secrets.token_urlsafe(24)
    existing = query("SELECT id FROM gps_devices WHERE yacht_id = ?", (yid,), one=True)
    if existing:
        execute("UPDATE gps_devices SET api_key_hash = ?, is_active = 1 WHERE id = ?", (hash_key(key), existing["id"]))
    else:
        execute("INSERT INTO gps_devices (yacht_id, device_code, api_key_hash, is_active) VALUES (?, ?, ?, 1)",
                (yid, f"GPS-{1000 + yid}", hash_key(key)))
    log_action("rotate_device_key", "yachts", yid)
    return ok({"device_code": f"GPS-{1000 + yid}", "api_key": key})


@bp.get("/media/yachts/<int:pid>")
def photo(pid):
    p = query("SELECT stored_name, mime_type FROM yacht_photos WHERE id = ?", (pid,), one=True)
    if not p:
        abort(404)
    path = os.path.join(config.UPLOAD_DIR, "yachts", os.path.basename(p["stored_name"]))
    if not os.path.exists(path):
        abort(404)
    return send_file(path, mimetype=p["mime_type"], max_age=86400)


@bp.get("/api/marinas")
def marinas():
    return ok(query("SELECT id, name, city, latitude, longitude FROM marinas WHERE is_active = 1 ORDER BY id"))

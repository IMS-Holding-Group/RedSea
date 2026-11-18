from flask import Blueprint, g, request, abort

from backend.db import query, execute
from backend.dates import now_iso, parse_iso, now_utc
from backend.routes import body
from backend.security import ok, fail, login_required, role_required, hash_key, rate_limited, in_red_sea, v_float, ValidationError
from backend.services import tracking_service
from backend.audit import log_action

bp = Blueprint("tracking", __name__, url_prefix="/api")


@bp.post("/telemetry")
def telemetry():
    """استقبال قراءات جهاز GPS. محمي بمفتاح الجهاز، ويقبل دفعة حتى 100 قراءة."""
    key = request.headers.get("X-Device-Key", "")
    if not key or len(key) > 100:
        return fail("غير مصرح.", 401)
    device = query("SELECT * FROM gps_devices WHERE api_key_hash = ? AND is_active = 1", (hash_key(key),), one=True)
    if not device:
        return fail("غير مصرح.", 401)
    if rate_limited(f"dev:{device['id']}", 60, 60):
        return fail("تم تجاوز معدل الطلبات المسموح.", 429)
    readings = body().get("readings")
    if not isinstance(readings, list) or not 1 <= len(readings) <= 100:
        return fail("يجب إرسال من 1 إلى 100 قراءة.")
    clean = []
    for r in readings:
        if not isinstance(r, dict):
            return fail("قراءة غير صالحة.")
        try:
            lat, lng = float(r["lat"]), float(r["lng"])
            speed = float(r.get("speed_knots", 0))
            heading = float(r.get("heading_deg", 0)) % 360
        except (KeyError, TypeError, ValueError):
            return fail("قراءة غير صالحة.")
        rec = parse_iso(r.get("recorded_at", ""))
        if not in_red_sea(lat, lng) or not 0 <= speed <= 80 or rec is None or rec > now_utc():
            return fail("قيم القراءة خارج النطاق المسموح.")
        clean.append({"lat": lat, "lng": lng, "speed_knots": speed, "heading_deg": heading, "recorded_at": rec})
    count = tracking_service.ingest(device, clean)
    return ok({"stored": count})


def visible_yacht_ids():
    role = g.user["role"]
    if role in ("admin", "marina_manager"):
        return [r["id"] for r in query("SELECT id FROM yachts")]
    if role == "owner":
        return [r["id"] for r in query("SELECT id FROM yachts WHERE owner_id = ?", (g.user["id"],))]
    if role == "tourist":
        return [r["yacht_id"] for r in query("SELECT yacht_id FROM bookings WHERE tourist_id = ? AND status = 'in_progress'",
                                             (g.user["id"],))]
    return []


@bp.get("/tracking/live")
@login_required
def live():
    tracking_service.check_signal_lost()
    return ok(tracking_service.live_positions(visible_yacht_ids()))


@bp.get("/tracking/trail/<int:bid>")
@login_required
def trail(bid):
    b = query("SELECT b.*, y.owner_id FROM bookings b JOIN yachts y ON y.id = b.yacht_id WHERE b.id = ?", (bid,), one=True)
    if not b:
        abort(404)
    role = g.user["role"]
    if (role == "tourist" and b["tourist_id"] != g.user["id"]) or (role == "owner" and b["owner_id"] != g.user["id"]) \
            or role == "provider":
        abort(404)
    pts = query("SELECT latitude AS lat, longitude AS lng, speed_knots AS speed, recorded_at FROM positions "
                "WHERE booking_id = ? ORDER BY recorded_at", (bid,))
    return ok({"points": pts, "status": b["status"], "reference": b["reference"], "yacht_id": b["yacht_id"],
               "route_zone_id": b["route_zone_id"]})


@bp.post("/tracking/sos")
@role_required("tourist")
def sos():
    data = body()
    b = query("SELECT b.*, y.name, y.owner_id FROM bookings b JOIN yachts y ON y.id = b.yacht_id "
              "WHERE b.tourist_id = ? AND b.status = 'in_progress' ORDER BY b.start_at DESC LIMIT 1", (g.user["id"],), one=True)
    if not b:
        return fail("لا توجد رحلة جارية لإرسال نداء الاستغاثة.")
    # نداء الاستغاثة لا يُرفض أبداً: إن كانت إحداثيات الجهاز غير صالحة يُستخدم آخر موقع GPS لليخت
    try:
        lat = v_float(data, "lat", "خط العرض", 12, 30, required=False)
        lng = v_float(data, "lng", "خط الطول", 32, 44, required=False)
    except ValidationError:
        lat = lng = None
    if lat is None or lng is None:
        last = query("SELECT latitude, longitude FROM positions WHERE yacht_id = ? ORDER BY recorded_at DESC LIMIT 1",
                     (b["yacht_id"],), one=True)
        lat, lng = (last["latitude"], last["longitude"]) if last else (None, None)
    yacht = {"id": b["yacht_id"], "name": b["name"], "owner_id": b["owner_id"]}
    aid = tracking_service.raise_alert(yacht, b["id"], "sos", "critical",
                                       f"نداء استغاثة من السائح {g.user['full_name']} على متن {b['name']} (الرحلة {b['reference']}).",
                                       lat, lng)
    from backend.db import get_db
    get_db().commit()
    log_action("sos", "alerts", aid)
    return ok({"alert_id": aid})


@bp.get("/alerts")
@role_required("admin", "marina_manager", "owner")
def alerts():
    ids = visible_yacht_ids()
    if not ids:
        return ok([])
    status = request.args.get("status", "open")
    marks = ",".join("?" * len(ids))
    sql = (f"SELECT a.*, y.name AS yacht_name FROM alerts a JOIN yachts y ON y.id = a.yacht_id WHERE a.yacht_id IN ({marks})")
    params = list(ids)
    if status in ("open", "acknowledged", "resolved"):
        sql += " AND a.status = ?"
        params.append(status)
    elif status == "active":
        sql += " AND a.status != 'resolved'"
    sql += " ORDER BY a.created_at DESC LIMIT 200"
    return ok(query(sql, params))


def own_alert(aid):
    a = query("SELECT * FROM alerts WHERE id = ?", (aid,), one=True)
    if not a or a["yacht_id"] not in visible_yacht_ids():
        abort(404)
    return a


@bp.post("/alerts/<int:aid>/acknowledge")
@role_required("admin", "marina_manager", "owner")
def acknowledge(aid):
    own_alert(aid)
    execute("UPDATE alerts SET status = 'acknowledged' WHERE id = ? AND status = 'open'", (aid,))
    log_action("acknowledge_alert", "alerts", aid)
    return ok()


@bp.post("/alerts/<int:aid>/resolve")
@role_required("admin", "marina_manager", "owner")
def resolve(aid):
    own_alert(aid)
    execute("UPDATE alerts SET status = 'resolved', resolved_by = ?, resolved_at = ? WHERE id = ?", (g.user["id"], now_iso(), aid))
    log_action("resolve_alert", "alerts", aid)
    return ok()

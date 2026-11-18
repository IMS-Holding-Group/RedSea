"""التتبع الحي: استقبال القراءات، كشف مخالفات المناطق، وفقدان الإشارة."""
import json
from datetime import timedelta

from backend.db import query, get_db
from backend.dates import now_utc, now_iso, parse_iso, to_iso
from backend.services.geo import point_in_polygon
from backend.notifications import notify

STOP_SPEED = 1.0          # أقل من 1 عقدة يعني أن اليخت متوقف
STOP_READINGS = 3         # عدد القراءات المتتالية للحكم بالرسو
SIGNAL_LOST_MIN = 10
DEDUPE_MIN = 15

ZONE_ALERTS = {
    "protected": ("protected_zone_entry", "warning", "دخل اليخت منطقة محمية: {name}."),
    "restricted": ("restricted_zone_entry", "critical", "دخل اليخت منطقة مقيدة: {name}."),
}
ALERT_LABELS = {"no_anchor_violation": "رسو في منطقة محظورة", "protected_zone_entry": "دخول منطقة محمية",
                "restricted_zone_entry": "دخول منطقة مقيدة", "outside_cruising_area": "خروج عن منطقة الإبحار",
                "signal_lost": "فقدان الإشارة", "sos": "نداء استغاثة", "weather_warning": "تحذير طقس"}


def active_zones():
    rows = query("SELECT * FROM zones WHERE is_active = 1")
    for z in rows:
        z["polygon"] = json.loads(z["polygon_json"])
    return rows


def current_trip(yacht_id):
    return query("SELECT * FROM bookings WHERE yacht_id = ? AND status = 'in_progress' ORDER BY start_at DESC LIMIT 1",
                 (yacht_id,), one=True)


def raise_alert(yacht, booking_id, alert_type, severity, message, lat, lng):
    """ينشئ تنبيهاً ما لم يوجد تنبيه مفتوح من نفس النوع لنفس اليخت خلال 15 دقيقة."""
    since = to_iso(now_utc() - timedelta(minutes=DEDUPE_MIN))
    if alert_type != "sos" and query("SELECT id FROM alerts WHERE yacht_id = ? AND alert_type = ? AND status = 'open' "
                                     "AND created_at >= ?", (yacht["id"], alert_type, since), one=True):
        return None
    db = get_db()
    cur = db.execute("INSERT INTO alerts (yacht_id, booking_id, alert_type, severity, message, latitude, longitude, "
                     "status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?)",
                     (yacht["id"], booking_id, alert_type, severity, message, lat, lng, now_iso()))
    title = f"{ALERT_LABELS[alert_type]}: {yacht['name']}"
    notify(yacht["owner_id"], title, message, "/fleet-map", commit=False)
    if severity == "critical":
        for u in query("SELECT id FROM users WHERE role IN ('admin','marina_manager') AND is_active = 1"):
            notify(u["id"], title, message, "/admin-dashboard" if alert_type != "sos" else "/fleet-map", commit=False)
    return cur.lastrowid


def evaluate_position(yacht, booking, lat, lng, speed):
    zones = active_zones()
    for z in zones:
        if not point_in_polygon(lat, lng, z["polygon"]):
            continue
        if z["zone_type"] == "no_anchor" and speed < STOP_SPEED:
            last = query("SELECT latitude, longitude, speed_knots FROM positions WHERE yacht_id = ? "
                         "ORDER BY recorded_at DESC, id DESC LIMIT ?", (yacht["id"], STOP_READINGS))
            if len(last) >= STOP_READINGS and all(p["speed_knots"] < STOP_SPEED and
                                                  point_in_polygon(p["latitude"], p["longitude"], z["polygon"])
                                                  for p in last):
                raise_alert(yacht, booking["id"] if booking else None, "no_anchor_violation", "critical",
                            f"اليخت متوقف داخل منطقة يُحظر فيها الرسو: {z['name']}.", lat, lng)
        elif z["zone_type"] in ZONE_ALERTS:
            atype, sev, msg = ZONE_ALERTS[z["zone_type"]]
            raise_alert(yacht, booking["id"] if booking else None, atype, sev, msg.format(name=z["name"]), lat, lng)
    if booking and booking["route_zone_id"]:
        area = next((z for z in zones if z["id"] == booking["route_zone_id"]), None)
        if area and not point_in_polygon(lat, lng, area["polygon"]):
            raise_alert(yacht, booking["id"], "outside_cruising_area", "warning",
                        f"اليخت خارج منطقة الإبحار المصرح بها للرحلة {booking['reference']}.", lat, lng)


def ingest(device, readings):
    """يحفظ دفعة قراءات مرتبة زمنياً ويقيّم كل قراءة (يدعم الإرسال المؤجل بعد انقطاع الاتصال)."""
    yacht = query("SELECT * FROM yachts WHERE id = ?", (device["yacht_id"],), one=True)
    booking = current_trip(yacht["id"])
    db = get_db()
    received = now_iso()
    readings.sort(key=lambda r: r["recorded_at"])
    for r in readings:
        db.execute("INSERT INTO positions (yacht_id, booking_id, latitude, longitude, speed_knots, heading_deg, "
                   "recorded_at, received_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                   (yacht["id"], booking["id"] if booking else None, r["lat"], r["lng"], r["speed_knots"],
                    r["heading_deg"], to_iso(r["recorded_at"]), received))
        evaluate_position(yacht, booking, r["lat"], r["lng"], r["speed_knots"])
    db.execute("UPDATE gps_devices SET last_seen_at = ? WHERE id = ?", (received, device["id"]))
    db.commit()
    return len(readings)


def check_signal_lost():
    limit = now_utc() - timedelta(minutes=SIGNAL_LOST_MIN)
    trips = query("SELECT b.id, b.reference, y.id AS yid, y.name, y.owner_id FROM bookings b JOIN yachts y ON y.id = b.yacht_id "
                  "WHERE b.status = 'in_progress'")
    for t in trips:
        last = query("SELECT recorded_at, latitude, longitude FROM positions WHERE yacht_id = ? ORDER BY recorded_at DESC LIMIT 1",
                     (t["yid"],), one=True)
        if last is None or parse_iso(last["recorded_at"]) < limit:
            yacht = {"id": t["yid"], "name": t["name"], "owner_id": t["owner_id"]}
            raise_alert(yacht, t["id"], "signal_lost", "warning",
                        f"لم تصل أي قراءة GPS من اليخت خلال {SIGNAL_LOST_MIN} دقائق أثناء الرحلة {t['reference']}.",
                        last["latitude"] if last else None, last["longitude"] if last else None)
    get_db().commit()


def live_positions(yacht_ids):
    out = []
    limit = now_utc() - timedelta(minutes=SIGNAL_LOST_MIN)
    for yid in yacht_ids:
        y = query("SELECT id, name, status, owner_id, length_m FROM yachts WHERE id = ?", (yid,), one=True)
        last = query("SELECT latitude, longitude, speed_knots, heading_deg, recorded_at FROM positions WHERE yacht_id = ? "
                     "ORDER BY recorded_at DESC, id DESC LIMIT 1", (yid,), one=True)
        if not last:
            continue
        trip = current_trip(yid)
        alerts = query("SELECT id, alert_type, severity, message, created_at FROM alerts WHERE yacht_id = ? AND status = 'open' "
                       "ORDER BY created_at DESC", (yid,))
        out.append({"yacht_id": yid, "name": y["name"], "lat": last["latitude"], "lng": last["longitude"],
                    "speed": last["speed_knots"], "heading": last["heading_deg"], "recorded_at": last["recorded_at"],
                    "stale": bool(trip) and parse_iso(last["recorded_at"]) < limit, "trip": trip["reference"] if trip else None,
                    "booking_id": trip["id"] if trip else None, "alerts": alerts})
    return out

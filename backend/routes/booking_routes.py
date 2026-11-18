from datetime import timedelta
from flask import Blueprint, g, abort

from backend.db import query, execute, get_db
from backend.dates import now_iso, now_utc, parse_iso, to_iso, format_datetime
from backend.routes import body, money
from backend.security import ok, fail, role_required, login_required, v_int, v_choice, v_datetime, v_text, ValidationError
from backend.services import booking_service, weather_service, maintenance_service
from backend.notifications import notify
from backend.audit import log_action

bp = Blueprint("bookings", __name__)
PURPOSES = ("leisure", "business", "fishing", "diving")


def booking_view(b):
    permit = query("SELECT status FROM trip_permits WHERE booking_id = ?", (b["id"],), one=True)
    return {"id": b["id"], "reference": b["reference"], "yacht_id": b["yacht_id"], "yacht_name": b.get("yacht_name"),
            "marina_name": b.get("marina_name"), "tourist_name": b.get("tourist_name"), "start_at": b["start_at"],
            "end_at": b["end_at"], "guests": b["guests"], "purpose": b["purpose"], "total": money(b["total_halalas"]),
            "status": b["status"], "weather_status_at_booking": b["weather_status_at_booking"],
            "cancel_reason": b["cancel_reason"], "permit": permit["status"] if permit else None,
            "route_zone_id": b["route_zone_id"], "created_at": b["created_at"]}


BASE = ("SELECT b.*, y.name AS yacht_name, y.owner_id, y.size_class, y.home_marina_id, m.name AS marina_name, "
        "u.full_name AS tourist_name FROM bookings b JOIN yachts y ON y.id = b.yacht_id "
        "JOIN marinas m ON m.id = y.home_marina_id JOIN users u ON u.id = b.tourist_id ")


def load(bid):
    b = query(BASE + "WHERE b.id = ?", (bid,), one=True)
    if not b:
        abort(404)
    return b


@bp.post("/api/bookings")
@role_required("tourist")
def create():
    data = body()
    yid = v_int(data, "yacht_id", "اليخت", 1, 10 ** 9)
    start = v_datetime(data, "start_at", "وقت البداية")
    end = v_datetime(data, "end_at", "وقت النهاية")
    if end <= start:
        raise ValidationError("وقت النهاية يجب أن يكون بعد وقت البداية.")
    guests = v_int(data, "guests", "عدد الضيوف", 1, 200)
    purpose = v_choice(data, "purpose", "الغرض", PURPOSES)
    zone = v_int(data, "route_zone_id", "منطقة الإبحار", 1, 10 ** 9, required=False)
    if zone and not query("SELECT id FROM zones WHERE id = ? AND zone_type = 'cruising_area' AND is_active = 1", (zone,), one=True):
        raise ValidationError("منطقة الإبحار غير صالحة.")
    v_text(data, "payer_name", "اسم حامل البطاقة", 3, 80)
    yacht = query("SELECT * FROM yachts WHERE id = ?", (yid,), one=True)
    if not yacht:
        return fail("اليخت غير موجود.", 404)
    bid, ref = booking_service.create_booking(g.user["id"], yacht, start, end, guests, purpose, zone,
                                              bool(data.get("ack_caution")), data.get("payer_name"))
    log_action("create_booking", "bookings", bid)
    return ok({"id": bid, "reference": ref}, 201)


@bp.get("/api/bookings/mine")
@role_required("tourist")
def mine():
    rows = query(BASE + "WHERE b.tourist_id = ? ORDER BY b.start_at DESC", (g.user["id"],))
    return ok([booking_view(b) for b in rows])


@bp.get("/api/bookings/<int:bid>")
@login_required
def one(bid):
    b = load(bid)
    if g.user["role"] == "tourist" and b["tourist_id"] != g.user["id"]:
        abort(404)
    if g.user["role"] == "owner" and b["owner_id"] != g.user["id"]:
        abort(404)
    if g.user["role"] == "provider":
        abort(404)
    return ok(booking_view(b))


@bp.post("/api/bookings/<int:bid>/cancel")
@role_required("tourist")
def cancel(bid):
    b = load(bid)
    if b["tourist_id"] != g.user["id"]:
        abort(404)
    if b["status"] not in ("pending", "confirmed", "weather_hold"):
        return fail("لا يمكن إلغاء هذا الحجز في حالته الحالية.")
    weather = b["status"] == "weather_hold"
    refund = booking_service.cancel_booking(b, "إلغاء بسبب الطقس" if weather else "إلغاء من السائح", weather)
    notify(b["owner_id"], "إلغاء حجز", f"ألغى السائح الحجز {b['reference']}.", "/owner-bookings")
    log_action("cancel_booking", "bookings", bid)
    return ok({"refund": money(refund)})


@bp.get("/api/bookings/<int:bid>/slots")
@role_required("tourist")
def slots(bid):
    b = load(bid)
    if b["tourist_id"] != g.user["id"]:
        abort(404)
    y = query("SELECT * FROM yachts WHERE id = ?", (b["yacht_id"],), one=True)
    lat, lng = booking_service.yacht_location(y)
    duration = int(round((parse_iso(b["end_at"]) - parse_iso(b["start_at"])).total_seconds() / 3600))
    candidates = weather_service.suggest_safe_slots(y["size_class"], lat, lng, duration, now_utc() + timedelta(hours=2), 8)
    result = []
    for s in candidates:
        if not booking_service.has_conflict(y["id"], parse_iso(s["start_at"]), parse_iso(s["end_at"]), bid):
            result.append(s)
        if len(result) == 3:
            break
    return ok(result)


@bp.post("/api/bookings/<int:bid>/reschedule")
@role_required("tourist")
def reschedule(bid):
    b = load(bid)
    if b["tourist_id"] != g.user["id"]:
        abort(404)
    if b["status"] not in ("weather_hold", "pending", "confirmed"):
        return fail("لا يمكن إعادة جدولة هذا الحجز.")
    data = body()
    start = v_datetime(data, "start_at", "وقت البداية")
    end = v_datetime(data, "end_at", "وقت النهاية")
    old_hours = (parse_iso(b["end_at"]) - parse_iso(b["start_at"])).total_seconds()
    if abs((end - start).total_seconds() - old_hours) > 60:
        raise ValidationError("يجب أن تكون المدة الجديدة مساوية لمدة الحجز الأصلي.")
    y = query("SELECT * FROM yachts WHERE id = ?", (b["yacht_id"],), one=True)
    reasons, weather = booking_service.availability_check(y, start, end, b["guests"], exclude_id=bid)
    if reasons:
        raise ValidationError(" ".join(reasons))
    new_status = "confirmed" if b["status"] in ("weather_hold", "confirmed") else "pending"
    execute("UPDATE bookings SET start_at = ?, end_at = ?, status = ?, weather_status_at_booking = ?, updated_at = ? WHERE id = ?",
            (to_iso(start), to_iso(end), new_status, weather["status"], now_iso(), bid))
    notify(b["owner_id"], "إعادة جدولة حجز", f"أعيدت جدولة الحجز {b['reference']} إلى {format_datetime(start)}.", "/owner-bookings")
    log_action("reschedule_booking", "bookings", bid)
    return ok()


@bp.get("/api/owner/bookings")
@role_required("owner")
def owner_bookings():
    rows = query(BASE + "WHERE y.owner_id = ? ORDER BY b.start_at DESC", (g.user["id"],))
    return ok([booking_view(b) for b in rows])


def owned(bid):
    b = load(bid)
    if b["owner_id"] != g.user["id"]:
        abort(404)
    return b


@bp.post("/api/owner/bookings/<int:bid>/decision")
@role_required("owner")
def decision(bid):
    b = owned(bid)
    if b["status"] != "pending":
        return fail("تم اتخاذ قرار بشأن هذا الحجز مسبقاً.")
    d = v_choice(body(), "decision", "القرار", ("approve", "reject"))
    db = get_db()
    if d == "approve":
        if booking_service.has_conflict(b["yacht_id"], parse_iso(b["start_at"]), parse_iso(b["end_at"]), bid):
            return fail("يوجد حجز آخر متعارض مع هذه الفترة.")
        db.execute("UPDATE bookings SET status = 'confirmed', updated_at = ? WHERE id = ?", (now_iso(), bid))
        db.execute("INSERT OR IGNORE INTO trip_permits (booking_id, status, requested_at) VALUES (?, 'requested', ?)", (bid, now_iso()))
        db.commit()
        notify(b["tourist_id"], "تم تأكيد حجزك", f"وافق المالك على الحجز {b['reference']}. تصريح الإبحار قيد الاعتماد.", "/my-bookings")
        for u in query("SELECT id FROM users WHERE role = 'admin' AND is_active = 1"):
            notify(u["id"], "تصريح إبحار جديد", f"طلب تصريح للرحلة {b['reference']}.", "/admin-compliance")
    else:
        booking_service.cancel_booking(b, "رفض من المالك", weather_reason=True)
        execute("UPDATE bookings SET status = 'rejected' WHERE id = ?", (bid,))
        notify(b["tourist_id"], "تم رفض الحجز", f"اعتذر المالك عن الحجز {b['reference']} وتم استرداد المبلغ كاملاً.", "/my-bookings")
    log_action("booking_" + d, "bookings", bid)
    return ok()


@bp.post("/api/owner/bookings/<int:bid>/start")
@role_required("owner")
def start_trip(bid):
    b = owned(bid)
    if b["status"] != "confirmed":
        return fail("يجب أن يكون الحجز مؤكداً لبدء الرحلة.")
    permit = query("SELECT status FROM trip_permits WHERE booking_id = ?", (bid,), one=True)
    if not permit or permit["status"] != "approved":
        return fail("لا يمكن بدء الرحلة قبل اعتماد تصريح الإبحار.")
    if parse_iso(b["start_at"]) - now_utc() > timedelta(hours=1):
        return fail("لا يمكن بدء الرحلة قبل موعدها بأكثر من ساعة.")
    if query("SELECT id FROM bookings WHERE yacht_id = ? AND status = 'in_progress'", (b["yacht_id"],), one=True):
        return fail("لليخت رحلة جارية حالياً.")
    execute("UPDATE bookings SET status = 'in_progress', updated_at = ? WHERE id = ?", (now_iso(), bid))
    notify(b["tourist_id"], "بدأت رحلتك", f"بدأت الرحلة {b['reference']}. تابعها على الخريطة الحية.", f"/trip-live?id={bid}")
    log_action("start_trip", "bookings", bid)
    return ok()


@bp.post("/api/owner/bookings/<int:bid>/complete")
@role_required("owner")
def complete_trip(bid):
    b = owned(bid)
    if b["status"] != "in_progress":
        return fail("الرحلة ليست جارية.")
    engine = v_int(body(), "engine_hours", "ساعات تشغيل المحرك", 0, 48)
    db = get_db()
    db.execute("UPDATE bookings SET status = 'completed', updated_at = ? WHERE id = ?", (now_iso(), bid))
    db.execute("UPDATE yachts SET engine_hours = engine_hours + ? WHERE id = ?", (engine, b["yacht_id"]))
    db.execute("UPDATE alerts SET status = 'resolved', resolved_by = ?, resolved_at = ? WHERE booking_id = ? AND status != 'resolved'",
               (g.user["id"], now_iso(), bid))
    db.commit()
    created = maintenance_service.generate_due_work_orders(b["yacht_id"])
    notify(b["tourist_id"], "انتهت رحلتك", f"شكراً لاختيارك اليخت {b['yacht_name']}.", "/my-bookings")
    log_action("complete_trip", "bookings", bid, f"engine_hours={engine}")
    return ok({"work_orders_created": created})

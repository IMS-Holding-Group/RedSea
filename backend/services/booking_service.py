"""منطق الحجز المرتبط بالطقس والامتثال والصيانة."""
import secrets
from datetime import timedelta

from backend.db import query, get_db
from backend.dates import now_utc, now_iso, to_iso, parse_iso, format_datetime
from backend.security import ValidationError
from backend.services import weather_service, compliance_service
from backend.notifications import notify

MIN_HOURS, MAX_HOURS = 2, 12
_last_reeval = {"at": None}


def yacht_location(yacht):
    m = query("SELECT latitude, longitude FROM marinas WHERE id = ?", (yacht["home_marina_id"],), one=True)
    return (m["latitude"], m["longitude"]) if m else (21.72, 39.10)


def has_conflict(yacht_id, start, end, exclude_id=None):
    """كشف التعارض الزمني: فترتان تتقاطعان إذا بدأت كل منهما قبل انتهاء الأخرى."""
    sql = ("SELECT id FROM bookings WHERE yacht_id = ? AND status NOT IN ('cancelled','rejected','completed') "
           "AND start_at < ? AND end_at > ?")
    params = [yacht_id, to_iso(end), to_iso(start)]
    if exclude_id:
        sql += " AND id != ?"
        params.append(exclude_id)
    return query(sql, params, one=True) is not None


def maintenance_conflict(yacht_id, start, end):
    return query("SELECT id FROM work_orders WHERE yacht_id = ? AND status IN ('assigned','in_progress') "
                 "AND due_at IS NOT NULL AND due_at < ? AND due_at > ?",
                 (yacht_id, to_iso(end), to_iso(start - timedelta(days=1))), one=True) is not None


def availability_check(yacht, start, end, guests, exclude_id=None):
    """يعيد قائمة الأسباب التي تمنع الحجز، وتقييم الطقس."""
    reasons = []
    if yacht["status"] != "active":
        reasons.append("اليخت غير متاح حالياً.")
    if guests is not None and guests > yacht["capacity"]:
        reasons.append(f"عدد الضيوف يتجاوز سعة اليخت ({yacht['capacity']}).")
    hours = (end - start).total_seconds() / 3600
    if hours < MIN_HOURS or hours > MAX_HOURS:
        reasons.append(f"مدة الرحلة يجب أن تكون بين {MIN_HOURS} و{MAX_HOURS} ساعة.")
    if start < now_utc() + timedelta(hours=2):
        reasons.append("يجب أن تبدأ الرحلة بعد ساعتين على الأقل من الآن.")
    if has_conflict(yacht["id"], start, end, exclude_id):
        reasons.append("اليخت محجوز في هذه الفترة.")
    if maintenance_conflict(yacht["id"], start, end):
        reasons.append("اليخت لديه صيانة مجدولة في هذه الفترة.")
    missing = compliance_service.missing_documents(yacht["id"], end)
    if missing:
        reasons.append("وثائق اليخت غير مكتملة في تاريخ الرحلة: " + "، ".join(missing) + ".")
    lat, lng = yacht_location(yacht)
    weather = weather_service.assess(yacht["size_class"], lat, lng, start, end)
    if weather["status"] == "unsafe":
        reasons.append("الطقس البحري المتوقع غير آمن لفئة هذا اليخت في الفترة المختارة.")
    return reasons, weather


def new_reference():
    year = now_utc().year
    while True:
        ref = f"RY-{year}-{secrets.randbelow(900000) + 100000}"
        if not query("SELECT id FROM bookings WHERE reference = ?", (ref,), one=True):
            return ref


def create_booking(tourist_id, yacht, start, end, guests, purpose, route_zone_id, ack_caution, payer_name):
    reasons, weather = availability_check(yacht, start, end, guests)
    if reasons:
        raise ValidationError(" ".join(reasons))
    if weather["status"] == "caution" and not ack_caution:
        raise ValidationError("الطقس المتوقع يستدعي الحذر. يجب تأكيد الاطلاع على التحذير قبل الحجز.")
    hours = (end - start).total_seconds() / 3600
    total = int(round(hours * yacht["hourly_rate_halalas"]))
    now = now_iso()
    db = get_db()
    try:
        db.execute("BEGIN IMMEDIATE")
        if has_conflict(yacht["id"], start, end):
            raise ValidationError("تم حجز هذه الفترة للتو من مستخدم آخر.")
        ref = new_reference()
        cur = db.execute("INSERT INTO bookings (reference, yacht_id, tourist_id, start_at, end_at, guests, purpose, "
                         "route_zone_id, total_halalas, status, weather_status_at_booking, created_at, updated_at) "
                         "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)",
                         (ref, yacht["id"], tourist_id, to_iso(start), to_iso(end), guests, purpose, route_zone_id,
                          total, weather["status"], now, now))
        bid = cur.lastrowid
        db.execute("INSERT INTO payments (booking_id, amount_halalas, method, status, transaction_ref, created_at) "
                   "VALUES (?, ?, 'card_simulated', 'paid', ?, ?)", (bid, total, "SIM-" + secrets.token_hex(6).upper(), now))
        notify(yacht["owner_id"], "طلب حجز جديد", f"طلب حجز {ref} لليخت {yacht['name']} يبدأ {format_datetime(start)}.",
               "/owner-bookings", commit=False)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return bid, ref


def refund_ratio(booking, weather_reason=False):
    """سياسة الاسترداد: 48 ساعة أو أكثر كامل، 24 إلى 48 نصف، أقل من 24 لا شيء، والطقس كامل دائماً."""
    if weather_reason:
        return 1.0
    hours_left = (parse_iso(booking["start_at"]) - now_utc()).total_seconds() / 3600
    if hours_left >= 48:
        return 1.0
    if hours_left >= 24:
        return 0.5
    return 0.0


def cancel_booking(booking, reason, weather_reason=False):
    ratio = refund_ratio(booking, weather_reason)
    db = get_db()
    now = now_iso()
    db.execute("UPDATE bookings SET status = 'cancelled', cancel_reason = ?, updated_at = ? WHERE id = ?",
               (reason, now, booking["id"]))
    refund = int(round(booking["total_halalas"] * ratio))
    if refund > 0:
        db.execute("INSERT INTO payments (booking_id, amount_halalas, method, status, transaction_ref, created_at) "
                   "VALUES (?, ?, 'card_simulated', 'refunded', ?, ?)",
                   (booking["id"], refund, "REF-" + secrets.token_hex(6).upper(), now))
    db.commit()
    return refund


def reevaluate_upcoming_bookings(force=False):
    """يعيد تقييم طقس الحجوزات المؤكدة خلال 48 ساعة، بحد أدنى 30 دقيقة بين كل تنفيذين."""
    last = _last_reeval["at"]
    if not force and last and now_utc() - last < timedelta(minutes=30):
        return 0
    _last_reeval["at"] = now_utc()
    rows = query("SELECT b.*, y.name AS yacht_name, y.size_class, y.home_marina_id, y.owner_id FROM bookings b "
                 "JOIN yachts y ON y.id = b.yacht_id WHERE b.status = 'confirmed' AND b.start_at > ? AND b.start_at <= ?",
                 (now_iso(), to_iso(now_utc() + timedelta(hours=48))))
    changed = 0
    for b in rows:
        lat, lng = yacht_location(b)
        w = weather_service.assess(b["size_class"], lat, lng, parse_iso(b["start_at"]), parse_iso(b["end_at"]))
        if w["status"] == "unsafe":
            get_db().execute("UPDATE bookings SET status = 'weather_hold', updated_at = ? WHERE id = ?", (now_iso(), b["id"]))
            msg = f"تم تعليق الحجز {b['reference']} لليخت {b['yacht_name']} بسبب توقع طقس غير آمن."
            notify(b["tourist_id"], "تعليق حجز بسبب الطقس", msg + " يمكنك إعادة الجدولة أو الإلغاء باسترداد كامل.",
                   "/my-bookings", commit=False)
            notify(b["owner_id"], "تعليق حجز بسبب الطقس", msg, "/owner-bookings", commit=False)
            changed += 1
    get_db().commit()
    return changed

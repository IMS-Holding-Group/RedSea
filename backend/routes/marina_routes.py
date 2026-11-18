from flask import Blueprint, g, request, abort
from backend.db import query, execute
from backend.dates import now_iso, parse_iso, format_datetime, to_iso
from backend.routes import body, money
from backend.security import ok, fail, role_required, login_required, v_int, v_datetime, v_text, v_float, v_choice, ValidationError
from backend.services import berthing_service
from backend.notifications import notify
from backend.audit import log_action

bp = Blueprint("marina", __name__, url_prefix="/api")


def berth_out(b):
    return {**{k: b[k] for k in ("id", "marina_id", "code", "max_length_m", "max_beam_m", "max_draft_m", "has_power",
                                 "has_water", "status")}, "daily_rate": money(b["daily_rate_halalas"]),
            "marina_name": b.get("marina_name")}


@bp.get("/marinas/<int:mid>/berths")
@login_required
def berths(mid):
    rows = query("SELECT * FROM berths WHERE marina_id = ? ORDER BY id", (mid,))
    now = now_iso()
    out = []
    for b in rows:
        item = berth_out(b)
        occ = query("SELECT r.id, y.name AS yacht_name, r.end_at FROM berth_reservations r JOIN yachts y ON y.id = r.yacht_id "
                    "WHERE r.berth_id = ? AND r.status = 'approved' AND r.start_at <= ? AND r.end_at > ?", (b["id"], now, now), one=True)
        item["occupied_by"] = occ
        out.append(item)
    return ok(out)


@bp.get("/berths/match")
@role_required("owner")
def match():
    a = request.args
    if not a.get("yacht_id", "").isdigit():
        return fail("اليخت غير محدد.")
    y = query("SELECT * FROM yachts WHERE id = ? AND owner_id = ?", (int(a["yacht_id"]), g.user["id"]), one=True)
    start, end = parse_iso(a.get("start", "")), parse_iso(a.get("end", ""))
    if not y or not start or not end or end <= start:
        return fail("بيانات الطلب غير صحيحة.")
    mid = int(a["marina_id"]) if a.get("marina_id", "").isdigit() else None
    days = max(1, round((end - start).total_seconds() / 86400))
    res = berthing_service.match_berths(y, start, end, mid)
    return ok([{**berth_out(b), "waste_m": b["waste_m"], "days": days, "total": money(b["daily_rate_halalas"] * days)} for b in res])


@bp.post("/berth-reservations")
@role_required("owner")
def reserve():
    d = body()
    yid = v_int(d, "yacht_id", "اليخت", 1, 10 ** 9)
    bid = v_int(d, "berth_id", "المربط", 1, 10 ** 9)
    start, end = v_datetime(d, "start_at", "تاريخ البداية"), v_datetime(d, "end_at", "تاريخ النهاية")
    if end <= start:
        raise ValidationError("تاريخ النهاية يجب أن يكون بعد البداية.")
    y = query("SELECT * FROM yachts WHERE id = ? AND owner_id = ?", (yid, g.user["id"]), one=True)
    if not y:
        abort(404)
    options = {b["id"]: b for b in berthing_service.match_berths(y, start, end)}
    if bid not in options:
        return fail("المربط غير مناسب لأبعاد اليخت أو محجوز في هذه الفترة.")
    days = max(1, round((end - start).total_seconds() / 86400))
    b = options[bid]
    rid = execute("INSERT INTO berth_reservations (berth_id, yacht_id, requested_by, start_at, end_at, status, total_halalas, notes, created_at) "
                  "VALUES (?, ?, ?, ?, ?, 'requested', ?, ?, ?)",
                  (bid, yid, g.user["id"], to_iso(start), to_iso(end), b["daily_rate_halalas"] * days,
                   v_text(d, "notes", "الملاحظات", 0, 300, required=False), now_iso()))
    m = query("SELECT manager_id FROM marinas WHERE id = ?", (b["marina_id"],), one=True)
    notify(m["manager_id"], "طلب مربط جديد", f"طلب المالك المربط {b['code']} لليخت {y['name']} من {format_datetime(start)}.",
           "/marina-berths")
    log_action("request_berth", "berth_reservations", rid)
    return ok({"id": rid}, 201)


@bp.get("/owner/berth-reservations")
@role_required("owner")
def owner_reservations():
    return ok(query("SELECT r.*, b.code, m.name AS marina_name, y.name AS yacht_name FROM berth_reservations r "
                    "JOIN berths b ON b.id = r.berth_id JOIN marinas m ON m.id = b.marina_id JOIN yachts y ON y.id = r.yacht_id "
                    "WHERE y.owner_id = ? ORDER BY r.start_at DESC", (g.user["id"],)))


def managed_marinas():
    if g.user["role"] == "admin":
        return [m["id"] for m in query("SELECT id FROM marinas")]
    return [m["id"] for m in query("SELECT id FROM marinas WHERE manager_id = ?", (g.user["id"],))]


@bp.get("/marina/mine")
@role_required("marina_manager", "admin")
def my_marinas():
    ids = managed_marinas()
    if not ids:
        return ok([])
    return ok(query(f"SELECT * FROM marinas WHERE id IN ({','.join('?' * len(ids))})", ids))


@bp.get("/marina/reservations")
@role_required("marina_manager", "admin")
def reservations():
    ids = managed_marinas()
    if not ids:
        return ok([])
    rows = query("SELECT r.*, b.code, b.marina_id, m.name AS marina_name, y.name AS yacht_name, y.length_m, u.full_name AS owner_name "
                 "FROM berth_reservations r JOIN berths b ON b.id = r.berth_id JOIN marinas m ON m.id = b.marina_id "
                 f"JOIN yachts y ON y.id = r.yacht_id JOIN users u ON u.id = r.requested_by WHERE b.marina_id IN ({','.join('?' * len(ids))}) "
                 "ORDER BY r.status = 'requested' DESC, r.start_at DESC", ids)
    for r in rows:
        r["total"] = money(r["total_halalas"])
    return ok(rows)


@bp.post("/marina/reservations/<int:rid>/decision")
@role_required("marina_manager", "admin")
def decide(rid):
    r = query("SELECT r.*, b.marina_id, b.code, y.name AS yacht_name FROM berth_reservations r JOIN berths b ON b.id = r.berth_id "
              "JOIN yachts y ON y.id = r.yacht_id WHERE r.id = ?", (rid,), one=True)
    if not r or r["marina_id"] not in managed_marinas():
        abort(404)
    if r["status"] != "requested":
        return fail("تم اتخاذ قرار بشأن هذا الطلب مسبقاً.")
    d = body()
    dec = v_choice(d, "decision", "القرار", ("approve", "reject"))
    if dec == "approve" and query("SELECT id FROM berth_reservations WHERE berth_id = ? AND status = 'approved' AND id != ? AND start_at < ? AND end_at > ?",
                  (r["berth_id"], rid, r["end_at"], r["start_at"]), one=True):
        return fail("المربط محجوز بطلب معتمد آخر في هذه الفترة.")
    status = "approved" if dec == "approve" else "rejected"
    note = v_text(d, "notes", "الملاحظة", 0, 300, required=False)
    execute("UPDATE berth_reservations SET status = ?, notes = COALESCE(?, notes) WHERE id = ?", (status, note, rid))
    notify(r["requested_by"], "قرار طلب المربط",
           f"تم {'اعتماد' if status == 'approved' else 'رفض'} طلب المربط {r['code']} لليخت {r['yacht_name']}.", "/owner-yachts")
    log_action("berth_" + dec, "berth_reservations", rid)
    return ok()


@bp.post("/marina/berths")
@role_required("marina_manager", "admin")
def add_berth():
    d = body()
    mid = v_int(d, "marina_id", "المرسى", 1, 10 ** 9)
    if mid not in managed_marinas():
        abort(404)
    code = v_text(d, "code", "رمز المربط", 1, 10)
    if query("SELECT id FROM berths WHERE marina_id = ? AND code = ?", (mid, code), one=True):
        return fail("رمز المربط مستخدم في هذا المرسى.", 409)
    bid = execute("INSERT INTO berths (marina_id, code, max_length_m, max_beam_m, max_draft_m, has_power, has_water, "
                  "daily_rate_halalas, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (mid, code, v_float(d, "max_length_m", "الطول", 4, 150), v_float(d, "max_beam_m", "العرض", 1.5, 40),
                   v_float(d, "max_draft_m", "الغاطس", 0.5, 12), 1 if d.get("has_power") else 0, 1 if d.get("has_water") else 0,
                   int(v_float(d, "daily_rate", "السعر اليومي", 10, 100000) * 100),
                   v_choice(d, "status", "الحالة", ("available", "maintenance", "closed"))))
    log_action("create_berth", "berths", bid)
    return ok({"id": bid}, 201)


@bp.put("/marina/berths/<int:bid>")
@role_required("marina_manager", "admin")
def update_berth(bid):
    b = query("SELECT * FROM berths WHERE id = ?", (bid,), one=True)
    if not b or b["marina_id"] not in managed_marinas():
        abort(404)
    d = body()
    execute("UPDATE berths SET max_length_m = ?, max_beam_m = ?, max_draft_m = ?, has_power = ?, has_water = ?, "
            "daily_rate_halalas = ?, status = ? WHERE id = ?",
            (v_float(d, "max_length_m", "الطول", 4, 150), v_float(d, "max_beam_m", "العرض", 1.5, 40),
             v_float(d, "max_draft_m", "الغاطس", 0.5, 12), 1 if d.get("has_power") else 0, 1 if d.get("has_water") else 0,
             int(v_float(d, "daily_rate", "السعر اليومي", 10, 100000) * 100),
             v_choice(d, "status", "الحالة", ("available", "maintenance", "closed")), bid))
    log_action("update_berth", "berths", bid)
    return ok()

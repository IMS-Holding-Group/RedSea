import time
from datetime import timedelta
from flask import Blueprint, g, request

from backend.db import query, execute
from backend.dates import now_iso, now_utc, to_iso
from backend.routes import money
from backend.security import ok, login_required, role_required
from backend.services import booking_service, maintenance_service, compliance_service

bp = Blueprint("dashboard", __name__, url_prefix="/api")


def background_jobs():
    """المهام الدورية تُنفذ عند فتح اللوحات بدلاً من جدولة خارجية."""
    booking_service.reevaluate_upcoming_bookings()
    compliance_service.refresh_expired_documents()


@bp.get("/dashboard/tourist")
@role_required("tourist")
def tourist():
    background_jobs()
    now = now_iso()
    upcoming = query("SELECT b.id, b.reference, b.start_at, b.end_at, b.status, y.name AS yacht_name, y.size_class, y.home_marina_id, "
                     "y.id AS yacht_id FROM bookings b JOIN yachts y ON y.id = b.yacht_id WHERE b.tourist_id = ? "
                     "AND b.status IN ('pending','confirmed','weather_hold','in_progress') AND b.end_at >= ? ORDER BY b.start_at",
                     (g.user["id"], now))
    from backend.services import weather_service
    from backend.dates import parse_iso
    for b in upcoming:
        lat, lng = booking_service.yacht_location(b)
        w = weather_service.assess(b["size_class"], lat, lng, parse_iso(b["start_at"]), parse_iso(b["end_at"]))
        b["weather"] = w["status"]
    past = query("SELECT COUNT(*) AS c FROM bookings WHERE tourist_id = ? AND status = 'completed'", (g.user["id"],), one=True)["c"]
    return ok({"upcoming": upcoming, "completed_count": past})


@bp.get("/dashboard/owner")
@role_required("owner")
def owner():
    background_jobs()
    maintenance_service.generate_due_work_orders()
    uid = g.user["id"]
    yachts = query("SELECT id, name, status, engine_hours FROM yachts WHERE owner_id = ?", (uid,))
    for y in yachts:
        y["compliance"] = compliance_service.compliance_score(y["id"])
    pending = query("SELECT b.id, b.reference, b.start_at, y.name AS yacht_name FROM bookings b JOIN yachts y ON y.id = b.yacht_id "
                    "WHERE y.owner_id = ? AND b.status = 'pending' ORDER BY b.start_at", (uid,))
    months = []
    now = now_utc()
    for i in range(5, -1, -1):
        y, m = now.year, now.month - i
        while m <= 0:
            m += 12
            y -= 1
        start = f"{y:04d}-{m:02d}-01T00:00:00"
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        end = f"{ny:04d}-{nm:02d}-01T00:00:00"
        r = query("SELECT COALESCE(SUM(b.total_halalas), 0) AS s FROM bookings b JOIN yachts yy ON yy.id = b.yacht_id "
                  "WHERE yy.owner_id = ? AND b.status IN ('completed','confirmed','in_progress') AND b.start_at >= ? AND b.start_at < ?",
                  (uid, start, end), one=True)
        months.append({"label": f"{y}/{m}", "value": money(r["s"])})
    orders = query("SELECT w.id, w.title, w.priority, w.status, w.due_at, y.name AS yacht_name FROM work_orders w JOIN yachts y ON y.id = w.yacht_id "
                   "WHERE y.owner_id = ? AND w.status NOT IN ('completed','cancelled') ORDER BY w.due_at LIMIT 8", (uid,))
    alerts = query("SELECT a.id, a.alert_type, a.severity, a.message, a.created_at, y.name AS yacht_name FROM alerts a "
                   "JOIN yachts y ON y.id = a.yacht_id WHERE y.owner_id = ? AND a.status != 'resolved' ORDER BY a.created_at DESC LIMIT 8", (uid,))
    live = query("SELECT COUNT(*) AS c FROM bookings b JOIN yachts y ON y.id = b.yacht_id WHERE y.owner_id = ? AND b.status = 'in_progress'",
                 (uid,), one=True)["c"]
    return ok({"yachts": yachts, "pending": pending, "revenue": months, "orders": orders, "alerts": alerts, "live_trips": live})


@bp.get("/dashboard/marina")
@role_required("marina_manager", "admin")
def marina():
    background_jobs()
    if g.user["role"] == "admin":
        marinas = query("SELECT id, name, city FROM marinas")
    else:
        marinas = query("SELECT id, name, city FROM marinas WHERE manager_id = ?", (g.user["id"],))
    now = now_utc()
    for m in marinas:
        total = query("SELECT COUNT(*) AS c FROM berths WHERE marina_id = ? AND status != 'closed'", (m["id"],), one=True)["c"] or 1
        m["berths"] = total
        series = []
        for i in range(29, -1, -1):
            day = (now - timedelta(days=i)).replace(hour=12, minute=0, second=0)
            occ = query("SELECT COUNT(DISTINCT r.berth_id) AS c FROM berth_reservations r JOIN berths b ON b.id = r.berth_id "
                        "WHERE b.marina_id = ? AND r.status IN ('approved','completed') AND r.start_at <= ? AND r.end_at > ?",
                        (m["id"], to_iso(day), to_iso(day)), one=True)["c"]
            home = query("SELECT COUNT(*) AS c FROM yachts WHERE home_marina_id = ?", (m["id"],), one=True)["c"]
            series.append({"label": f"{day.month}/{day.day}", "value": round(min(100, (occ + home) * 100 / total), 1)})
        m["occupancy"] = series
        m["today"] = series[-1]["value"]
        m["pending"] = query("SELECT COUNT(*) AS c FROM berth_reservations r JOIN berths b ON b.id = r.berth_id "
                             "WHERE b.marina_id = ? AND r.status = 'requested'", (m["id"],), one=True)["c"]
        m["yachts"] = query("SELECT id, name, length_m, status FROM yachts WHERE home_marina_id = ?", (m["id"],))
    return ok(marinas)


@bp.get("/dashboard/provider")
@role_required("provider")
def provider():
    uid = g.user["id"]
    c = lambda status: query("SELECT COUNT(*) AS c FROM work_orders WHERE provider_id = ? AND status = ?", (uid, status), one=True)["c"]
    total = query("SELECT COALESCE(SUM(quote_halalas), 0) AS s FROM work_orders WHERE provider_id = ? AND status = 'completed'",
                  (uid,), one=True)["s"]
    prof = query("SELECT * FROM provider_profiles WHERE user_id = ?", (uid,), one=True)
    services = [s for s in (prof["services"] if prof else "").split(",") if s] or ["none"]
    available = query(f"SELECT COUNT(*) AS c FROM work_orders WHERE status IN ('open','quoted') AND service_type IN ({','.join('?' * len(services))})",
                      services, one=True)["c"]
    return ok({"available": available, "assigned": c("assigned"), "in_progress": c("in_progress"), "completed": c("completed"),
               "revenue": money(total), "profile": prof})


@bp.get("/dashboard/admin")
@role_required("admin")
def admin():
    background_jobs()
    cnt = lambda sql, p=(): query(sql, p, one=True)["c"]
    by_role = query("SELECT role, COUNT(*) AS c FROM users GROUP BY role")
    stats = {
        "users": cnt("SELECT COUNT(*) AS c FROM users"),
        "yachts": cnt("SELECT COUNT(*) AS c FROM yachts"),
        "active_trips": cnt("SELECT COUNT(*) AS c FROM bookings WHERE status = 'in_progress'"),
        "bookings_month": cnt("SELECT COUNT(*) AS c FROM bookings WHERE created_at >= ?", (to_iso(now_utc() - timedelta(days=30)),)),
        "pending_docs": cnt("SELECT COUNT(*) AS c FROM compliance_documents WHERE status = 'pending_review'"),
        "pending_permits": cnt("SELECT COUNT(*) AS c FROM trip_permits WHERE status = 'requested'"),
        "critical_alerts": cnt("SELECT COUNT(*) AS c FROM alerts WHERE severity = 'critical' AND status != 'resolved'"),
        "weather_holds": cnt("SELECT COUNT(*) AS c FROM bookings WHERE status = 'weather_hold'"),
    }
    alerts = query("SELECT a.*, y.name AS yacht_name FROM alerts a JOIN yachts y ON y.id = a.yacht_id WHERE a.status != 'resolved' "
                   "ORDER BY a.severity = 'critical' DESC, a.created_at DESC LIMIT 10")
    return ok({"stats": stats, "by_role": by_role, "alerts": alerts})


@bp.get("/notifications")
@login_required
def notifications():
    return ok(query("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT 100", (g.user["id"],)))


@bp.get("/notifications/unread-count")
@login_required
def unread():
    return ok(query("SELECT COUNT(*) AS c FROM notifications WHERE user_id = ? AND is_read = 0", (g.user["id"],), one=True)["c"])


@bp.post("/notifications/<int:nid>/read")
@login_required
def read(nid):
    execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (nid, g.user["id"]))
    return ok()


@bp.post("/notifications/read-all")
@login_required
def read_all():
    execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (g.user["id"],))
    return ok()


@bp.get("/health")
def health():
    t0 = time.perf_counter()
    try:
        query("SELECT 1 AS x", one=True)
        db_ok = True
    except Exception:
        db_ok = False
    return ok({"status": "ok" if db_ok else "degraded", "database": db_ok,
               "response_ms": round((time.perf_counter() - t0) * 1000, 2), "checked_at": now_iso()})

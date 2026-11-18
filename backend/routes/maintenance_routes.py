from flask import Blueprint, g, abort
from backend.db import query, execute, get_db
from backend.dates import now_iso, to_iso, parse_iso
from backend.routes import body, money
from backend.security import ok, fail, role_required, v_int, v_text, v_choice, v_float, v_datetime, ValidationError
from backend.services import maintenance_service
from backend.notifications import notify
from backend.audit import log_action

bp = Blueprint("maintenance", __name__, url_prefix="/api")
SERVICES = ("maintenance", "cleaning", "fueling", "electrical", "diving_inspection")
PRIORITIES = ("low", "normal", "high", "urgent")


def own_yacht(yid):
    y = query("SELECT * FROM yachts WHERE id = ? AND owner_id = ?", (yid, g.user["id"]), one=True)
    if not y:
        abort(404)
    return y


@bp.get("/owner/maintenance/plans")
@role_required("owner")
def plans():
    rows = query("SELECT p.*, y.name AS yacht_name, y.engine_hours FROM maintenance_plans p JOIN yachts y ON y.id = p.yacht_id "
                 "WHERE y.owner_id = ? ORDER BY y.id, p.id", (g.user["id"],))
    for p in rows:
        ratio, days_left, due = maintenance_service.plan_progress(p, p["engine_hours"])
        p["hours_ratio"] = round(ratio, 2) if ratio is not None else None
        p["days_left"] = round(days_left) if days_left is not None else None
        p["due_at"] = to_iso(due) if due else None
    return ok(rows)


def plan_form(d):
    hrs = v_float(d, "interval_engine_hours", "فاصل ساعات التشغيل", 1, 10000, required=False)
    days = v_int(d, "interval_days", "فاصل الأيام", 1, 3650, required=False)
    if hrs is None and days is None:
        raise ValidationError("يجب تحديد فاصل بالساعات أو بالأيام على الأقل.")
    return v_text(d, "task_name", "اسم المهمة", 3, 80), hrs, days, v_choice(d, "service_type", "نوع الخدمة", SERVICES)


@bp.post("/owner/maintenance/plans")
@role_required("owner")
def add_plan():
    d = body()
    y = own_yacht(v_int(d, "yacht_id", "اليخت", 1, 10 ** 9))
    name, hrs, days, stype = plan_form(d)
    pid = execute("INSERT INTO maintenance_plans (yacht_id, task_name, interval_engine_hours, interval_days, last_done_engine_hours, "
                  "last_done_at, service_type) VALUES (?, ?, ?, ?, ?, ?, ?)", (y["id"], name, hrs, days, y["engine_hours"], now_iso(), stype))
    log_action("create_plan", "maintenance_plans", pid)
    return ok({"id": pid}, 201)


@bp.put("/owner/maintenance/plans/<int:pid>")
@role_required("owner")
def update_plan(pid):
    p = query("SELECT p.id FROM maintenance_plans p JOIN yachts y ON y.id = p.yacht_id WHERE p.id = ? AND y.owner_id = ?",
              (pid, g.user["id"]), one=True)
    if not p:
        abort(404)
    name, hrs, days, stype = plan_form(body())
    execute("UPDATE maintenance_plans SET task_name = ?, interval_engine_hours = ?, interval_days = ?, service_type = ? WHERE id = ?",
            (name, hrs, days, stype, pid))
    log_action("update_plan", "maintenance_plans", pid)
    return ok()


@bp.delete("/owner/maintenance/plans/<int:pid>")
@role_required("owner")
def delete_plan(pid):
    p = query("SELECT p.id FROM maintenance_plans p JOIN yachts y ON y.id = p.yacht_id WHERE p.id = ? AND y.owner_id = ?",
              (pid, g.user["id"]), one=True)
    if not p:
        abort(404)
    execute("DELETE FROM maintenance_plans WHERE id = ?", (pid,))
    return ok()


def wo_out(w):
    w["quote"] = money(w["quote_halalas"]) if w.get("quote_halalas") else None
    return w


@bp.get("/owner/work-orders")
@role_required("owner")
def owner_orders():
    maintenance_service.generate_due_work_orders()
    rows = query("SELECT w.*, y.name AS yacht_name, u.full_name AS provider_name FROM work_orders w JOIN yachts y ON y.id = w.yacht_id "
                 "LEFT JOIN users u ON u.id = w.provider_id WHERE y.owner_id = ? ORDER BY w.status IN ('completed','cancelled'), "
                 "CASE w.priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END, w.due_at", (g.user["id"],))
    for w in rows:
        wo_out(w)
        w["quotes"] = query("SELECT q.*, u.full_name AS provider_name FROM work_order_quotes q JOIN users u ON u.id = q.provider_id "
                            "WHERE q.work_order_id = ? ORDER BY q.amount_halalas", (w["id"],))
        for q in w["quotes"]:
            q["amount"] = money(q["amount_halalas"])
    return ok(rows)


@bp.post("/owner/work-orders")
@role_required("owner")
def create_order():
    d = body()
    y = own_yacht(v_int(d, "yacht_id", "اليخت", 1, 10 ** 9))
    due = v_datetime(d, "due_at", "تاريخ الاستحقاق")
    wid = execute("INSERT INTO work_orders (yacht_id, title, description, service_type, priority, status, due_at, created_at) "
                  "VALUES (?, ?, ?, ?, ?, 'open', ?, ?)",
                  (y["id"], v_text(d, "title", "العنوان", 3, 100), v_text(d, "description", "الوصف", 0, 1000, required=False) or "",
                   v_choice(d, "service_type", "نوع الخدمة", SERVICES), v_choice(d, "priority", "الأولوية", PRIORITIES),
                   to_iso(due), now_iso()))
    for p in query("SELECT user_id FROM provider_profiles"):
        notify(p["user_id"], "أمر عمل جديد متاح", f"أمر عمل جديد لليخت {y['name']} متاح لتقديم عرض سعر.", "/provider-orders")
    log_action("create_work_order", "work_orders", wid)
    return ok({"id": wid}, 201)


@bp.post("/owner/work-orders/<int:wid>/accept-quote")
@role_required("owner")
def accept_quote(wid):
    w = query("SELECT w.*, y.name AS yacht_name FROM work_orders w JOIN yachts y ON y.id = w.yacht_id WHERE w.id = ? AND y.owner_id = ?",
              (wid, g.user["id"]), one=True)
    if not w:
        abort(404)
    if w["status"] not in ("open", "quoted"):
        return fail("لا يمكن قبول عرض لهذا الأمر في حالته الحالية.")
    qid = v_int(body(), "quote_id", "العرض", 1, 10 ** 9)
    q = query("SELECT * FROM work_order_quotes WHERE id = ? AND work_order_id = ? AND status = 'submitted'", (qid, wid), one=True)
    if not q:
        return fail("العرض غير موجود.", 404)
    db = get_db()
    db.execute("UPDATE work_order_quotes SET status = CASE WHEN id = ? THEN 'accepted' ELSE 'declined' END WHERE work_order_id = ?", (qid, wid))
    db.execute("UPDATE work_orders SET status = 'assigned', provider_id = ?, quote_halalas = ? WHERE id = ?",
               (q["provider_id"], q["amount_halalas"], wid))
    db.commit()
    maintenance_service.sync_yacht_status(w["yacht_id"])
    notify(q["provider_id"], "تم قبول عرضك", f"تم إسناد أمر العمل ({w['title']}) لليخت {w['yacht_name']} إليك.", "/provider-orders")
    log_action("accept_quote", "work_orders", wid)
    return ok()


@bp.post("/owner/work-orders/<int:wid>/cancel")
@role_required("owner")
def cancel_order(wid):
    w = query("SELECT w.* FROM work_orders w JOIN yachts y ON y.id = w.yacht_id WHERE w.id = ? AND y.owner_id = ?",
              (wid, g.user["id"]), one=True)
    if not w:
        abort(404)
    if w["status"] in ("completed", "cancelled", "in_progress"):
        return fail("لا يمكن إلغاء هذا الأمر.")
    execute("UPDATE work_orders SET status = 'cancelled' WHERE id = ?", (wid,))
    maintenance_service.sync_yacht_status(w["yacht_id"])
    log_action("cancel_work_order", "work_orders", wid)
    return ok()


def provider_services():
    p = query("SELECT services FROM provider_profiles WHERE user_id = ?", (g.user["id"],), one=True)
    return [s for s in (p["services"] if p else "").split(",") if s]


@bp.get("/provider/work-orders")
@role_required("provider")
def provider_orders():
    services = provider_services() or ["none"]
    marks = ",".join("?" * len(services))
    base = ("SELECT w.*, y.name AS yacht_name, y.length_m, m.name AS marina_name FROM work_orders w JOIN yachts y ON y.id = w.yacht_id "
            "JOIN marinas m ON m.id = y.home_marina_id ")
    available = query(base + f"WHERE w.status IN ('open','quoted') AND w.service_type IN ({marks}) ORDER BY w.due_at", services)
    for w in available:
        mine = query("SELECT * FROM work_order_quotes WHERE work_order_id = ? AND provider_id = ?", (w["id"], g.user["id"]), one=True)
        w["my_quote"] = {**mine, "amount": money(mine["amount_halalas"])} if mine else None
    assigned = query(base + "WHERE w.provider_id = ? ORDER BY w.status = 'completed', w.due_at DESC", (g.user["id"],))
    return ok({"available": [wo_out(w) for w in available], "assigned": [wo_out(w) for w in assigned]})


def provider_order(wid, statuses):
    w = query("SELECT w.*, y.name AS yacht_name, y.owner_id FROM work_orders w JOIN yachts y ON y.id = w.yacht_id WHERE w.id = ?",
              (wid,), one=True)
    if not w:
        abort(404)
    if w["status"] not in statuses:
        raise ValidationError("لا يمكن تنفيذ هذا الإجراء على الأمر في حالته الحالية.")
    return w


@bp.post("/provider/work-orders/<int:wid>/quote")
@role_required("provider")
def quote(wid):
    w = provider_order(wid, ("open", "quoted"))
    if w["service_type"] not in provider_services():
        abort(404)
    d = body()
    amount = int(v_float(d, "amount", "المبلغ", 10, 1000000) * 100)
    eta = v_int(d, "eta_days", "مدة التنفيذ", 1, 90)
    notes = v_text(d, "notes", "الملاحظات", 0, 300, required=False) or ""
    existing = query("SELECT id FROM work_order_quotes WHERE work_order_id = ? AND provider_id = ?", (wid, g.user["id"]), one=True)
    if existing:
        execute("UPDATE work_order_quotes SET amount_halalas = ?, eta_days = ?, notes = ? WHERE id = ?", (amount, eta, notes, existing["id"]))
    else:
        execute("INSERT INTO work_order_quotes (work_order_id, provider_id, amount_halalas, eta_days, notes, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, 'submitted', ?)", (wid, g.user["id"], amount, eta, notes, now_iso()))
    execute("UPDATE work_orders SET status = 'quoted' WHERE id = ?", (wid,))
    notify(w["owner_id"], "عرض سعر جديد", f"وصل عرض سعر لأمر العمل ({w['title']}) لليخت {w['yacht_name']}.", "/owner-maintenance")
    log_action("submit_quote", "work_orders", wid)
    return ok()


@bp.post("/provider/work-orders/<int:wid>/start")
@role_required("provider")
def start(wid):
    w = provider_order(wid, ("assigned",))
    if w["provider_id"] != g.user["id"]:
        abort(404)
    execute("UPDATE work_orders SET status = 'in_progress' WHERE id = ?", (wid,))
    notify(w["owner_id"], "بدء تنفيذ الصيانة", f"بدأ تنفيذ أمر العمل ({w['title']}) لليخت {w['yacht_name']}.", "/owner-maintenance")
    log_action("start_work_order", "work_orders", wid)
    return ok()


@bp.post("/provider/work-orders/<int:wid>/complete")
@role_required("provider")
def complete(wid):
    w = provider_order(wid, ("in_progress",))
    if w["provider_id"] != g.user["id"]:
        abort(404)
    notes = v_text(body(), "completion_notes", "ملاحظات الإنجاز", 3, 1000)
    db = get_db()
    now = now_iso()
    db.execute("UPDATE work_orders SET status = 'completed', completed_at = ?, completion_notes = ? WHERE id = ?", (now, notes, wid))
    if w["plan_id"]:
        db.execute("UPDATE maintenance_plans SET last_done_at = ?, last_done_engine_hours = (SELECT engine_hours FROM yachts WHERE id = ?) "
                   "WHERE id = ?", (now, w["yacht_id"], w["plan_id"]))
    db.commit()
    maintenance_service.sync_yacht_status(w["yacht_id"])
    notify(w["owner_id"], "اكتملت الصيانة", f"اكتمل أمر العمل ({w['title']}) لليخت {w['yacht_name']}.", "/owner-maintenance")
    log_action("complete_work_order", "work_orders", wid)
    return ok()

"""الصيانة المبنية على الاستخدام: توليد أوامر العمل المستحقة تلقائياً."""
from datetime import timedelta
from backend.db import query, get_db
from backend.dates import now_utc, now_iso, parse_iso, to_iso
from backend.notifications import notify

DEFAULT_PLANS = [
    ("تغيير زيت المحرك", 100, None, "maintenance"),
    ("فحص المراوح والدفة", 250, None, "maintenance"),
    ("تنظيف قاع البدن", None, 90, "cleaning"),
    ("فحص معدات السلامة", None, 180, "maintenance"),
    ("فحص البطاريات والكهرباء", None, 120, "electrical"),
]


def create_default_plans(db, yacht_id, engine_hours, commit=True):
    now = now_iso()
    for name, hrs, days, stype in DEFAULT_PLANS:
        db.execute("INSERT INTO maintenance_plans (yacht_id, task_name, interval_engine_hours, interval_days, "
                   "last_done_engine_hours, last_done_at, service_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (yacht_id, name, hrs, days, engine_hours, now, stype))
    if commit:
        db.commit()


def plan_progress(plan, engine_hours):
    """يعيد (نسبة الاستهلاك بالساعات، الأيام المتبقية، تاريخ الاستحقاق)."""
    hours_ratio, days_left, due = None, None, None
    if plan["interval_engine_hours"]:
        used = engine_hours - (plan["last_done_engine_hours"] or 0)
        hours_ratio = used / plan["interval_engine_hours"]
    if plan["interval_days"]:
        last = parse_iso(plan["last_done_at"]) or now_utc()
        due = last + timedelta(days=plan["interval_days"])
        days_left = (due - now_utc()).total_seconds() / 86400
    return hours_ratio, days_left, due


def generate_due_work_orders(yacht_id=None):
    sql = ("SELECT p.*, y.engine_hours, y.name AS yacht_name, y.owner_id FROM maintenance_plans p "
           "JOIN yachts y ON y.id = p.yacht_id")
    params = ()
    if yacht_id:
        sql += " WHERE p.yacht_id = ?"
        params = (yacht_id,)
    db = get_db()
    created = 0
    for p in query(sql, params):
        hours_ratio, days_left, due = plan_progress(p, p["engine_hours"])
        is_due = (hours_ratio is not None and hours_ratio >= 0.9) or (days_left is not None and days_left <= 7)
        if not is_due:
            continue
        if query("SELECT id FROM work_orders WHERE plan_id = ? AND status NOT IN ('completed','cancelled')",
                 (p["id"],), one=True):
            continue
        if (days_left is not None and days_left < 0) or (hours_ratio is not None and hours_ratio >= 1.2):
            priority = "urgent"
        elif hours_ratio is not None and hours_ratio >= 1.0:
            priority = "high"
        else:
            priority = "normal"
        due_at = to_iso(due) if due else to_iso(now_utc() + timedelta(days=7))
        details = []
        if hours_ratio is not None:
            details.append(f"ساعات التشغيل منذ آخر صيانة بلغت {round(hours_ratio * 100)} بالمئة من الفاصل")
        if days_left is not None:
            details.append(f"الأيام المتبقية على الموعد {max(0, round(days_left))}")
        db.execute("INSERT INTO work_orders (yacht_id, plan_id, title, description, service_type, priority, status, "
                   "due_at, auto_generated, created_at) VALUES (?, ?, ?, ?, ?, ?, 'open', ?, 1, ?)",
                   (p["yacht_id"], p["id"], p["task_name"], "، ".join(details) + ".", p["service_type"], priority,
                    due_at, now_iso()))
        notify(p["owner_id"], "أمر صيانة جديد", f"تم إنشاء أمر عمل تلقائي ({p['task_name']}) لليخت {p['yacht_name']}.",
               "/owner-maintenance", commit=False)
        created += 1
    db.commit()
    return created


def sync_yacht_status(yacht_id):
    """يضع اليخت في حالة صيانة أثناء أمر عاجل مسند أو قيد التنفيذ، ويعيده نشطاً بعد انتهائه."""
    db = get_db()
    urgent = query("SELECT id FROM work_orders WHERE yacht_id = ? AND priority = 'urgent' "
                   "AND status IN ('assigned','in_progress')", (yacht_id,), one=True)
    y = query("SELECT status FROM yachts WHERE id = ?", (yacht_id,), one=True)
    if urgent and y["status"] == "active":
        db.execute("UPDATE yachts SET status = 'maintenance' WHERE id = ?", (yacht_id,))
    elif not urgent and y["status"] == "maintenance":
        db.execute("UPDATE yachts SET status = 'active' WHERE id = ?", (yacht_id,))
    db.commit()

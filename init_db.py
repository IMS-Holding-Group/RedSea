"""إنشاء قاعدة البيانات وزرع البيانات التجريبية.
الاستخدام: python init_db.py  أو  python init_db.py --reset"""
import json
import os
import re
import secrets
import sys
from datetime import timedelta

import config
from backend.db import connect
from backend.dates import now_utc, to_iso
from backend.security import hash_password, hash_key
from backend.services.maintenance_service import create_default_plans

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, phone TEXT,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('admin','marina_manager','owner','tourist','provider')),
  is_active INTEGER DEFAULT 1, created_at TEXT, last_login_at TEXT);
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, csrf_token TEXT,
  created_at TEXT, last_seen_at TEXT, ip_address TEXT, user_agent TEXT, revoked INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS login_attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, identifier TEXT, attempted_at TEXT, success INTEGER);
CREATE TABLE IF NOT EXISTS provider_profiles (
  user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, company_name TEXT, services TEXT,
  coverage_marinas TEXT, rating_avg REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS marinas (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, city TEXT, latitude REAL, longitude REAL,
  manager_id INTEGER REFERENCES users(id), contact_phone TEXT, is_active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS berths (
  id INTEGER PRIMARY KEY AUTOINCREMENT, marina_id INTEGER NOT NULL REFERENCES marinas(id), code TEXT,
  max_length_m REAL, max_beam_m REAL, max_draft_m REAL, has_power INTEGER, has_water INTEGER,
  daily_rate_halalas INTEGER, status TEXT CHECK(status IN ('available','maintenance','closed')),
  UNIQUE(marina_id, code));
CREATE TABLE IF NOT EXISTS yachts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER NOT NULL REFERENCES users(id), name TEXT,
  registration_no TEXT UNIQUE, type TEXT, length_m REAL, beam_m REAL, draft_m REAL, capacity INTEGER,
  cabins INTEGER, size_class TEXT CHECK(size_class IN ('small','medium','large')),
  home_marina_id INTEGER REFERENCES marinas(id), hourly_rate_halalas INTEGER, description TEXT,
  engine_hours REAL DEFAULT 0, status TEXT CHECK(status IN ('active','maintenance','suspended','draft')), created_at TEXT);
CREATE TABLE IF NOT EXISTS yacht_photos (
  id INTEGER PRIMARY KEY AUTOINCREMENT, yacht_id INTEGER NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  stored_name TEXT, original_name TEXT, mime_type TEXT, size_bytes INTEGER, uploaded_at TEXT);
CREATE TABLE IF NOT EXISTS gps_devices (
  id INTEGER PRIMARY KEY AUTOINCREMENT, yacht_id INTEGER UNIQUE REFERENCES yachts(id) ON DELETE CASCADE,
  device_code TEXT UNIQUE, api_key_hash TEXT, last_seen_at TEXT, is_active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS zones (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT,
  zone_type TEXT CHECK(zone_type IN ('no_anchor','protected','restricted','cruising_area')),
  polygon_json TEXT, description TEXT, is_active INTEGER DEFAULT 1, created_by INTEGER REFERENCES users(id), created_at TEXT);
CREATE TABLE IF NOT EXISTS bookings (
  id INTEGER PRIMARY KEY AUTOINCREMENT, reference TEXT UNIQUE, yacht_id INTEGER NOT NULL REFERENCES yachts(id),
  tourist_id INTEGER NOT NULL REFERENCES users(id), start_at TEXT, end_at TEXT, guests INTEGER, purpose TEXT,
  route_zone_id INTEGER REFERENCES zones(id), total_halalas INTEGER,
  status TEXT CHECK(status IN ('pending','confirmed','weather_hold','in_progress','completed','cancelled','rejected')),
  weather_status_at_booking TEXT, cancel_reason TEXT, created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS payments (
  id INTEGER PRIMARY KEY AUTOINCREMENT, booking_id INTEGER NOT NULL REFERENCES bookings(id), amount_halalas INTEGER,
  method TEXT, status TEXT, transaction_ref TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS berth_reservations (
  id INTEGER PRIMARY KEY AUTOINCREMENT, berth_id INTEGER NOT NULL REFERENCES berths(id),
  yacht_id INTEGER NOT NULL REFERENCES yachts(id), requested_by INTEGER REFERENCES users(id), start_at TEXT, end_at TEXT,
  status TEXT, total_halalas INTEGER, notes TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS positions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, yacht_id INTEGER NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  booking_id INTEGER REFERENCES bookings(id), latitude REAL, longitude REAL, speed_knots REAL, heading_deg REAL,
  recorded_at TEXT, received_at TEXT);
CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, yacht_id INTEGER REFERENCES yachts(id) ON DELETE CASCADE,
  booking_id INTEGER REFERENCES bookings(id), alert_type TEXT, severity TEXT, message TEXT, latitude REAL, longitude REAL,
  status TEXT, created_at TEXT, resolved_by INTEGER REFERENCES users(id), resolved_at TEXT);
CREATE TABLE IF NOT EXISTS weather_cache (
  id INTEGER PRIMARY KEY AUTOINCREMENT, grid_key TEXT, forecast_time TEXT, wind_speed_knots REAL, wind_gust_knots REAL,
  wave_height_m REAL, source TEXT, fetched_at TEXT, UNIQUE(grid_key, forecast_time));
CREATE TABLE IF NOT EXISTS maintenance_plans (
  id INTEGER PRIMARY KEY AUTOINCREMENT, yacht_id INTEGER NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  task_name TEXT, interval_engine_hours REAL, interval_days INTEGER, last_done_engine_hours REAL, last_done_at TEXT,
  service_type TEXT);
CREATE TABLE IF NOT EXISTS work_orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT, yacht_id INTEGER NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  plan_id INTEGER REFERENCES maintenance_plans(id) ON DELETE SET NULL, title TEXT, description TEXT, service_type TEXT,
  priority TEXT, status TEXT CHECK(status IN ('open','quoted','assigned','in_progress','completed','cancelled')),
  provider_id INTEGER REFERENCES users(id), quote_halalas INTEGER, due_at TEXT, completed_at TEXT,
  completion_notes TEXT, auto_generated INTEGER DEFAULT 0, created_at TEXT);
CREATE TABLE IF NOT EXISTS work_order_quotes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, work_order_id INTEGER NOT NULL REFERENCES work_orders(id) ON DELETE CASCADE,
  provider_id INTEGER REFERENCES users(id), amount_halalas INTEGER, eta_days INTEGER, notes TEXT, status TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS compliance_documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT, yacht_id INTEGER NOT NULL REFERENCES yachts(id) ON DELETE CASCADE,
  doc_type TEXT CHECK(doc_type IN ('registration','insurance','safety_inspection','navigation_license','crew_certificate')),
  doc_number TEXT, issued_at TEXT, expires_at TEXT, stored_name TEXT, status TEXT, reviewed_by INTEGER REFERENCES users(id),
  review_notes TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS trip_permits (
  id INTEGER PRIMARY KEY AUTOINCREMENT, booking_id INTEGER UNIQUE REFERENCES bookings(id) ON DELETE CASCADE,
  status TEXT, requested_at TEXT, decided_at TEXT, notes TEXT);
CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, title TEXT,
  body TEXT, link TEXT, is_read INTEGER DEFAULT 0, created_at TEXT);
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER REFERENCES users(id) ON DELETE SET NULL, action TEXT, entity TEXT,
  entity_id INTEGER, details TEXT, ip_address TEXT, created_at TEXT);
CREATE INDEX IF NOT EXISTS idx_bookings_yacht ON bookings(yacht_id, start_at);
CREATE INDEX IF NOT EXISTS idx_bookings_tourist ON bookings(tourist_id);
CREATE INDEX IF NOT EXISTS idx_positions_yacht ON positions(yacht_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_alerts_yacht ON alerts(yacht_id, status);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_login_attempts ON login_attempts(identifier, attempted_at);
CREATE INDEX IF NOT EXISTS idx_work_orders_yacht ON work_orders(yacht_id, status);
CREATE INDEX IF NOT EXISTS idx_docs_yacht ON compliance_documents(yacht_id, doc_type);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);
"""


def square(lat, lng, d_lat, d_lng):
    return [[lat - d_lat, lng - d_lng], [lat - d_lat, lng + d_lng], [lat + d_lat, lng + d_lng], [lat + d_lat, lng - d_lng]]


def size_class(length):
    return "small" if length < 12 else ("medium" if length <= 24 else "large")


def write_env_value(key, value):
    path = os.path.join(config.BASE_DIR, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if re.search(rf"^{key}=.*$", text, flags=re.M):
        text = re.sub(rf"^{key}=.*$", f"{key}={value}", text, flags=re.M)
    else:
        text += f"\n{key}={value}"
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


SEED_PHOTOS_DIR = os.path.join(config.BASE_DIR, "seed", "photos")


def attach_seed_photos(db, replace=False):
    """يربط صورة افتراضية بكل يخت من seed/photos، واسم الملف هو رقم تسجيل اليخت.
    يتجاوز اليخت الذي لديه صور مسبقاً، إلا عند replace=True فتُحذف صوره أولاً."""
    import shutil
    from backend.dates import now_iso
    added, skipped = [], []
    if not os.path.isdir(SEED_PHOTOS_DIR):
        return added, skipped
    for fname in sorted(os.listdir(SEED_PHOTOS_DIR)):
        reg, ext = os.path.splitext(fname)
        if ext.lower() not in (".jpg", ".jpeg"):
            continue
        y = db.execute("SELECT id, name FROM yachts WHERE registration_no = ?", (reg,)).fetchone()
        if not y:
            continue
        existing = db.execute("SELECT id, stored_name FROM yacht_photos WHERE yacht_id = ?", (y[0],)).fetchall()
        if existing and not replace:
            skipped.append(y[1])
            continue
        for pid, stored in existing:
            path = os.path.join(config.UPLOAD_DIR, "yachts", os.path.basename(stored))
            if os.path.exists(path):
                os.remove(path)
            db.execute("DELETE FROM yacht_photos WHERE id = ?", (pid,))
        src = os.path.join(SEED_PHOTOS_DIR, fname)
        stored = secrets.token_hex(16) + ".jpg"
        shutil.copyfile(src, os.path.join(config.UPLOAD_DIR, "yachts", stored))
        db.execute("INSERT INTO yacht_photos (yacht_id, stored_name, original_name, mime_type, size_bytes, uploaded_at) "
                   "VALUES (?, ?, ?, 'image/jpeg', ?, ?)", (y[0], stored, fname, os.path.getsize(src), now_iso()))
        added.append(y[1])
    db.commit()
    return added, skipped


def seed(db):
    pwd = os.getenv("SEED_DEMO_PASSWORD")
    if not pwd:
        print("تنبيه: المتغير SEED_DEMO_PASSWORD غير موجود في ملف .env، لم تُزرع البيانات.")
        return
    now = now_utc().replace(second=0)
    iso = to_iso
    ph = hash_password(pwd)
    users = [
        ("مدير المنصة", "admin@redyacht.sa", "0500000001", "admin"),
        ("خالد الحربي - مدير مرسى أبحر", "marina@redyacht.sa", "0500000002", "marina_manager"),
        ("عبدالرحمن اللحيدان", "owner@redyacht.sa", "0500000003", "owner"),
        ("باسم بادومان", "owner2@redyacht.sa", "0500000004", "owner"),
        ("سارة القحطاني", "tourist@redyacht.sa", "0500000005", "tourist"),
        ("شركة المرجان للخدمات البحرية", "provider@redyacht.sa", "0500000006", "provider"),
    ]
    ids = {}
    for name, email, phone, role in users:
        cur = db.execute("INSERT INTO users (full_name, email, phone, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                         (name, email, phone, ph, role, iso(now)))
        ids[email.split("@")[0]] = cur.lastrowid
    admin, manager, owner, owner2, tourist, provider = (ids[k] for k in ("admin", "marina", "owner", "owner2", "tourist", "provider"))
    db.execute("INSERT INTO provider_profiles (user_id, company_name, services, coverage_marinas, rating_avg) VALUES (?, ?, ?, ?, ?)",
               (provider, "شركة المرجان للخدمات البحرية", "maintenance,cleaning,fueling,electrical,diving_inspection", "1,2,3", 4.6))

    marinas = [("مرسى أبحر", "جدة", 21.7215, 39.0980, manager), ("مرسى ينبع", "ينبع", 24.0870, 38.0520, manager),
               ("مرسى أملج", "أملج", 25.0240, 37.2650, manager)]
    marina_ids = []
    for name, city, lat, lng, mgr in marinas:
        marina_ids.append(db.execute("INSERT INTO marinas (name, city, latitude, longitude, manager_id, contact_phone) "
                                     "VALUES (?, ?, ?, ?, ?, ?)", (name, city, lat, lng, mgr, "0126000000")).lastrowid)
    sizes = [(10, 4, 1.6), (12, 4.5, 1.8), (14, 5, 2.0), (16, 5.5, 2.2), (18, 6, 2.4), (20, 6.5, 2.6),
             (25, 7.5, 3.0), (30, 8.5, 3.4), (35, 9.5, 3.8), (45, 11, 4.2)]
    for mi, mid in enumerate(marina_ids):
        for i, (ln, bm, dr) in enumerate(sizes):
            db.execute("INSERT INTO berths (marina_id, code, max_length_m, max_beam_m, max_draft_m, has_power, has_water, "
                       "daily_rate_halalas, status) VALUES (?, ?, ?, ?, ?, 1, 1, ?, ?)",
                       (mid, f"{'ABC'[i // 4]}-{i + 1}", ln, bm, dr, int(ln * 2500), "maintenance" if (mi == 0 and i == 3) else "available"))

    zones = [
        ("شعاب أبحر الشمالية", "no_anchor", square(21.745, 39.035, 0.008, 0.009), "شعاب مرجانية حساسة، يمنع إنزال المرساة."),
        ("شعاب أبحر الجنوبية", "no_anchor", square(21.665, 39.030, 0.007, 0.008), "شعاب مرجانية، يمنع الرسو."),
        ("محمية الجزر المرجانية", "protected", square(21.800, 38.975, 0.015, 0.018), "منطقة محمية بيئياً، الدخول بحذر."),
        ("منطقة الموانئ المقيدة", "restricted", square(21.560, 39.050, 0.020, 0.020), "منطقة ملاحة تجارية مقيدة."),
        ("منطقة إبحار جدة - أبحر", "cruising_area", [[21.60, 38.90], [21.60, 39.115], [21.86, 39.115], [21.86, 38.90]],
         "المنطقة المصرح بها لرحلات مرسى أبحر."),
        ("منطقة إبحار أملج", "cruising_area", [[24.90, 37.05], [24.90, 37.25], [25.12, 37.25], [25.12, 37.05]],
         "المنطقة المصرح بها لرحلات مرسى أملج."),
    ]
    zone_ids = []
    for name, ztype, poly, desc in zones:
        zone_ids.append(db.execute("INSERT INTO zones (name, zone_type, polygon_json, description, created_by, created_at) "
                                   "VALUES (?, ?, ?, ?, ?, ?)", (name, ztype, json.dumps(poly), desc, admin, iso(now))).lastrowid)

    yachts = [
        (owner, "لؤلؤة البحر", "KSA-JED-1021", "motor", 14.5, 4.6, 1.3, 10, 2, marina_ids[0], 85000, 96,
         "يخت عائلي مريح مناسب للرحلات القصيرة والسباحة."),
        (owner, "نجمة أبحر", "KSA-JED-1022", "sailing", 11.0, 3.8, 1.8, 6, 1, marina_ids[0], 55000, 40,
         "قارب شراعي للتجارب الهادئة وهواة الإبحار."),
        (owner, "الأسطورة", "KSA-JED-1023", "motor", 28.0, 7.0, 2.3, 20, 5, marina_ids[0], 280000, 188,
         "يخت فاخر للمناسبات ورحلات الأعمال."),
        (owner2, "مرجان", "KSA-YNB-2031", "catamaran", 13.0, 6.2, 1.2, 12, 3, marina_ids[1], 95000, 60,
         "قارب مزدوج البدن ثابت ومناسب للغوص."),
        (owner2, "أمواج أملج", "KSA-UML-3041", "motor", 18.0, 5.2, 1.6, 14, 3, marina_ids[2], 130000, 245,
         "يخت متوسط لاستكشاف جزر أملج."),
        (owner2, "صقر البحر", "KSA-UML-3042", "motor", 9.5, 3.2, 0.9, 5, 0, marina_ids[2], 40000, 12,
         "قارب سريع لرحلات الصيد القصيرة."),
    ]
    yacht_ids = []
    sim_key = None
    for i, (oid, name, reg, typ, ln, bm, dr, cap, cab, mid, rate, hrs, desc) in enumerate(yachts):
        yid = db.execute("INSERT INTO yachts (owner_id, name, registration_no, type, length_m, beam_m, draft_m, capacity, cabins, "
                         "size_class, home_marina_id, hourly_rate_halalas, description, engine_hours, status, created_at) "
                         "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)",
                         (oid, name, reg, typ, ln, bm, dr, cap, cab, size_class(ln), mid, rate, desc, hrs, iso(now))).lastrowid
        yacht_ids.append(yid)
        create_default_plans(db, yid, max(0, hrs - 50), commit=False)
        key = secrets.token_urlsafe(24)
        if i == 0:
            sim_key = key
        db.execute("INSERT INTO gps_devices (yacht_id, device_code, api_key_hash, is_active) VALUES (?, ?, ?, 1)",
                   (yid, f"GPS-{1000 + yid}", hash_key(key)))
        for dt, days_valid in (("registration", 700), ("insurance", 300), ("safety_inspection", 200)):
            exp = now + timedelta(days=days_valid)
            status = "approved"
            if yid == yacht_ids[0] and dt == "insurance":
                exp = now + timedelta(days=20)
            if i == 5 and dt == "safety_inspection":
                exp, status = now - timedelta(days=5), "expired"
            db.execute("INSERT INTO compliance_documents (yacht_id, doc_type, doc_number, issued_at, expires_at, status, "
                       "reviewed_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (yid, dt, f"{dt[:3].upper()}-{secrets.randbelow(90000) + 10000}", iso(now - timedelta(days=60)),
                        iso(exp), status, admin, iso(now)))
    db.execute("INSERT INTO compliance_documents (yacht_id, doc_type, doc_number, issued_at, expires_at, status, created_at) "
               "VALUES (?, 'navigation_license', 'NAV-55120', ?, ?, 'pending_review', ?)",
               (yacht_ids[1], iso(now - timedelta(days=2)), iso(now + timedelta(days=365)), iso(now)))
    # أول يخت: خطة زيت المحرك قاربت الاستحقاق لإظهار التوليد التلقائي
    db.execute("UPDATE maintenance_plans SET last_done_engine_hours = ? WHERE yacht_id = ? AND task_name = 'تغيير زيت المحرك'",
               (0, yacht_ids[0]))
    db.execute("UPDATE maintenance_plans SET last_done_at = ? WHERE yacht_id = ? AND task_name = 'تنظيف قاع البدن'",
               (iso(now - timedelta(days=86)), yacht_ids[4]))

    def booking(yidx, start, hours, status, zone=None, guests=4, purpose="leisure"):
        y = yachts[yidx]
        s = now + timedelta(hours=start)
        e = s + timedelta(hours=hours)
        ref = f"RY-{now.year}-{100000 + secrets.randbelow(899999)}"
        total = y[10] * hours
        bid = db.execute("INSERT INTO bookings (reference, yacht_id, tourist_id, start_at, end_at, guests, purpose, route_zone_id, "
                         "total_halalas, status, weather_status_at_booking, created_at, updated_at) "
                         "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'safe', ?, ?)",
                         (ref, yacht_ids[yidx], tourist, iso(s), iso(e), guests, purpose, zone, total, status,
                          iso(now - timedelta(days=3)), iso(now))).lastrowid
        db.execute("INSERT INTO payments (booking_id, amount_halalas, method, status, transaction_ref, created_at) "
                   "VALUES (?, ?, 'card_simulated', 'paid', ?, ?)", (bid, total, "SIM-" + secrets.token_hex(6).upper(), iso(now)))
        if status in ("confirmed", "in_progress", "completed"):
            db.execute("INSERT INTO trip_permits (booking_id, status, requested_at, decided_at) VALUES (?, ?, ?, ?)",
                       (bid, "approved" if status != "confirmed" or start > 80 else "requested", iso(now), iso(now)))
        return bid

    live_bid = booking(0, -1, 4, "in_progress", zone_ids[4], 6)
    booking(0, 30, 3, "pending", zone_ids[4], 4)
    booking(2, 72, 5, "confirmed", zone_ids[4], 12, "business")
    booking(3, 100, 4, "confirmed", None, 8, "diving")
    for back in (20, 45, 80, 110, 140):
        booking(back % 3, -24 * back, 4, "completed", zone_ids[4], 5)
    track = [(21.7200, 39.0930), (21.7260, 39.0820), (21.7320, 39.0700), (21.7380, 39.0580)]
    for i, (lat, lng) in enumerate(track):
        db.execute("INSERT INTO positions (yacht_id, booking_id, latitude, longitude, speed_knots, heading_deg, recorded_at, "
                   "received_at) VALUES (?, ?, ?, ?, 8.5, 300, ?, ?)",
                   (yacht_ids[0], live_bid, lat, lng, iso(now - timedelta(minutes=8 - i * 2)), iso(now)))
    db.execute("UPDATE gps_devices SET last_seen_at = ? WHERE yacht_id = ?", (iso(now), yacht_ids[0]))
    for yi, (lat, lng) in ((2, (21.7212, 39.0975)), (3, (24.0865, 38.0515)), (4, (25.0235, 37.2640))):
        db.execute("INSERT INTO positions (yacht_id, latitude, longitude, speed_knots, heading_deg, recorded_at, received_at) "
                   "VALUES (?, ?, ?, 0, 0, ?, ?)", (yacht_ids[yi], lat, lng, iso(now - timedelta(minutes=30)), iso(now)))

    wo = db.execute("INSERT INTO work_orders (yacht_id, title, description, service_type, priority, status, due_at, created_at) "
                    "VALUES (?, 'تنظيف وتلميع السطح', 'تنظيف شامل قبل موسم الرحلات.', 'cleaning', 'normal', 'quoted', ?, ?)",
                    (yacht_ids[2], iso(now + timedelta(days=10)), iso(now))).lastrowid
    db.execute("INSERT INTO work_order_quotes (work_order_id, provider_id, amount_halalas, eta_days, notes, status, created_at) "
               "VALUES (?, ?, 180000, 2, 'يشمل مواد التنظيف والتلميع.', 'submitted', ?)", (wo, provider, iso(now)))
    db.execute("INSERT INTO work_orders (yacht_id, title, description, service_type, priority, status, provider_id, quote_halalas, "
               "due_at, completed_at, completion_notes, created_at) VALUES (?, 'فحص نظام الوقود', 'فحص دوري.', 'maintenance', "
               "'normal', 'completed', ?, 90000, ?, ?, 'تم الفحص ولا توجد تسربات.', ?)",
               (yacht_ids[3], provider, iso(now - timedelta(days=12)), iso(now - timedelta(days=12)), iso(now - timedelta(days=15))))
    db.execute("INSERT INTO berth_reservations (berth_id, yacht_id, requested_by, start_at, end_at, status, total_halalas, notes, created_at) "
               "VALUES (?, ?, ?, ?, ?, 'requested', ?, 'رسو لمدة 3 أيام للصيانة.', ?)",
               (6, yacht_ids[1], owner, iso(now + timedelta(days=5)), iso(now + timedelta(days=8)), 3 * 45000, iso(now)))
    for uid, title, body, link in ((owner, "مرحباً بك", "تم تفعيل حسابك كمالك يخوت في منصة اليخت الأحمر.", "/owner-dashboard"),
                                   (tourist, "رحلتك جارية", "يمكنك متابعة رحلتك الحالية على الخريطة الحية.", "/my-bookings"),
                                   (admin, "وثيقة بانتظار المراجعة", "رخصة ملاحة جديدة لليخت نجمة أبحر.", "/admin-compliance")):
        db.execute("INSERT INTO notifications (user_id, title, body, link, created_at) VALUES (?, ?, ?, ?, ?)",
                   (uid, title, body, link, iso(now)))
    db.commit()
    attach_seed_photos(db)
    write_env_value("SIM_DEVICE_KEY", sim_key)
    print("تم زرع البيانات التجريبية. كلمة السر لكل الحسابات التجريبية هي قيمة SEED_DEMO_PASSWORD في ملف .env")
    print("تم حفظ مفتاح جهاز GPS التجريبي في المتغير SIM_DEVICE_KEY داخل ملف .env")


def main():
    if "--reset" in sys.argv and os.path.exists(config.DATABASE_PATH):
        confirm = input("سيتم حذف قاعدة البيانات الحالية بالكامل. اكتب RESET للتأكيد: ").strip()
        if confirm != "RESET":
            print("تم إلغاء العملية.")
            return
        os.remove(config.DATABASE_PATH)
    db = connect()
    db.executescript(SCHEMA)
    db.commit()
    empty = db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
    if empty:
        seed(db)
    else:
        print("قاعدة البيانات موجودة وتحتوي بيانات، لم يتم الزرع.")
    db.close()
    print("قاعدة البيانات جاهزة: " + config.DATABASE_PATH)


if __name__ == "__main__":
    main()

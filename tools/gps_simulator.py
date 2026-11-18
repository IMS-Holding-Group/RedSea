"""محاكي جهاز GPS: يرسل موقع اليخت كل 5 ثوانٍ إلى الخادم كما يفعل الجهاز الحقيقي.

الاستخدام:
  python tools/gps_simulator.py                   رحلة عادية داخل منطقة إبحار أبحر
  python tools/gps_simulator.py --anchor-violation يتوقف اليخت داخل منطقة حظر رسو لإظهار التنبيه
  python tools/gps_simulator.py --offline-burst    يحاكي انقطاع الاتصال ثم يرسل القراءات المؤجلة دفعة واحدة
"""
import argparse
import math
import os
import sys
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE, ".env"))

SERVER = os.getenv("SIM_SERVER_URL", "http://127.0.0.1:5000").rstrip("/")
KEY = os.getenv("SIM_DEVICE_KEY", "")

# مسار دائري داخل منطقة الإبحار المصرح بها قرب مرسى أبحر
ROUTE = [(21.7200, 39.0930), (21.7320, 39.0700), (21.7480, 39.0550), (21.7700, 39.0450), (21.7850, 39.0200),
         (21.7650, 39.0000), (21.7300, 38.9950), (21.7000, 39.0150), (21.6900, 39.0500), (21.7050, 39.0800)]
ANCHOR_POINT = (21.7450, 39.0350)  # داخل منطقة "شعاب أبحر الشمالية"


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def heading(a, b):
    return (math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) + 360) % 360


def send(readings):
    try:
        r = requests.post(f"{SERVER}/api/telemetry", json={"readings": readings}, headers={"X-Device-Key": KEY}, timeout=8)
        body = r.json()
        if r.ok:
            print(f"[{now_iso()}] تم إرسال {len(readings)} قراءة، آخر موقع {readings[-1]['lat']:.5f}, {readings[-1]['lng']:.5f}")
            return True
        print(f"رفض الخادم القراءة ({r.status_code}): {body.get('error')}")
    except requests.RequestException:
        print("تعذر الاتصال بالخادم، سيعاد المحاولة.")
    return False


def points(steps_per_leg=6):
    """يولد نقاطاً متتابعة بالاستيفاء الخطي بين نقاط المسار."""
    while True:
        for i in range(len(ROUTE)):
            a, b = ROUTE[i], ROUTE[(i + 1) % len(ROUTE)]
            for s in range(steps_per_leg):
                t = s / steps_per_leg
                yield (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, heading(a, b))


def reading(lat, lng, hdg, speed):
    return {"lat": round(lat, 6), "lng": round(lng, 6), "speed_knots": speed, "heading_deg": round(hdg, 1), "recorded_at": now_iso()}


def main():
    parser = argparse.ArgumentParser(description="محاكي جهاز GPS لمنصة اليخت الأحمر")
    parser.add_argument("--anchor-violation", action="store_true", help="التوقف داخل منطقة حظر رسو")
    parser.add_argument("--offline-burst", action="store_true", help="محاكاة انقطاع الاتصال ثم إرسال القراءات المؤجلة")
    parser.add_argument("--interval", type=int, default=5, help="الفاصل بين القراءات بالثواني")
    args = parser.parse_args()
    if not KEY:
        print("المتغير SIM_DEVICE_KEY غير موجود في ملف .env. شغّل python init_db.py أولاً أو أنشئ مفتاحاً من صفحة يخوتي.")
        sys.exit(1)
    print(f"بدء المحاكاة على الخادم {SERVER}. اضغط Ctrl+C للإيقاف.")
    if args.anchor_violation:
        print("وضع مخالفة الرسو: سيتوقف اليخت داخل منطقة شعاب أبحر الشمالية.")
        while True:
            send([reading(ANCHOR_POINT[0], ANCHOR_POINT[1], 0, 0.2)])
            time.sleep(args.interval)
    buffer = []
    count = 0
    for lat, lng, hdg in points():
        count += 1
        r = reading(lat, lng, hdg, 8.5)
        if args.offline_burst and 6 <= count % 30 < 14:
            buffer.append(r)
            print(f"[{now_iso()}] لا يوجد اتصال، تم تخزين القراءة محلياً ({len(buffer)} قراءة مؤجلة)")
        else:
            batch = buffer + [r]
            if send(batch):
                buffer = []
            else:
                buffer = batch[-100:]
        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nتم إيقاف المحاكي.")

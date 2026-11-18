"""يضيف الصور الافتراضية لليخوت التجريبية إلى قاعدة بيانات موجودة دون مسح أي بيانات.

الاستخدام:
  python tools/add_demo_photos.py            يضيف الصورة لكل يخت ليس لديه صور
  python tools/add_demo_photos.py --replace  يحذف صور اليخوت التجريبية الحالية ويضع الصور الافتراضية مكانها
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from backend.db import connect
from init_db import attach_seed_photos


def main():
    if not os.path.exists(config.DATABASE_PATH):
        print("قاعدة البيانات غير موجودة. شغّل python init_db.py أولاً، وستُضاف الصور تلقائياً.")
        return
    db = connect()
    added, skipped = attach_seed_photos(db, replace="--replace" in sys.argv)
    db.close()
    for name in added:
        print(f"تمت إضافة الصورة الافتراضية لليخت: {name}")
    for name in skipped:
        print(f"تم التجاوز لأن لديه صوراً مسبقاً: {name} (استخدم --replace لاستبدالها)")
    if not added and not skipped:
        print("لم يتم العثور على يخوت تجريبية مطابقة لأسماء الصور.")


if __name__ == "__main__":
    main()

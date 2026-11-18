# منصة اليخت الأحمر (The Red Yacht)

منصة ويب متكاملة لإدارة عمليات اليخوت في البحر الأحمر: حجز الرحلات بحسب الطقس البحري الفعلي، والتتبع الحي بنظام GPS مع مناطق حظر الرسو، وإدارة مرابط المراسي، والصيانة المبنية على ساعات التشغيل، والامتثال للوثائق والتصاريح البحرية.

مشروع تخرج، قسم نظم المعلومات، كلية علوم الحاسب والمعلومات، جامعة الإمام محمد بن سعود الإسلامية (الشعبة 174، المجموعة 13).

## فهرس المحتويات

1. [نظرة عامة](#1-نظرة-عامة)
2. [أصحاب المصلحة وأدوار المستخدمين](#2-أصحاب-المصلحة-وأدوار-المستخدمين)
3. [التقنيات المستخدمة وسبب اختيارها](#3-التقنيات-المستخدمة-وسبب-اختيارها)
4. [هيكل المجلدات](#4-هيكل-المجلدات)
5. [بنية قاعدة البيانات](#5-بنية-قاعدة-البيانات)
6. [الخوارزميات](#6-الخوارزميات)
7. [آلية عمل المشروع](#7-آلية-عمل-المشروع)
8. [الأمان](#8-الأمان)
9. [التعامل مع ضعف الإنترنت](#9-التعامل-مع-ضعف-الإنترنت)
10. [نموذج الذكاء الاصطناعي](#10-نموذج-الذكاء-الاصطناعي)
11. [المتطلبات الأساسية](#11-المتطلبات-الأساسية)
12. [خطوات التركيب والتشغيل](#12-خطوات-التركيب-والتشغيل)
13. [الحسابات التجريبية وسيناريو الاختبار](#13-الحسابات-التجريبية-وسيناريو-الاختبار)
14. [مرجع واجهة API](#14-مرجع-واجهة-api)
15. [إعدادات النشر وCloudflare](#15-إعدادات-النشر-وcloudflare)
16. [القيود الحالية والتطويرات المستقبلية](#16-القيود-الحالية-والتطويرات-المستقبلية)

---

## 1. نظرة عامة

### 1.1 المشكلة

يعتمد قطاع اليخوت في البحر الأحمر اليوم على قنوات متفرقة: الحجز يتم عبر الهاتف أو وسائل التواصل، وحالة البحر تُقدَّر يدوياً، ولا يوجد سجل موحد لمواقع اليخوت أثناء الرحلات، وتُدار الصيانة بالذاكرة أو بالأوراق. ينتج عن ذلك رحلات تُلغى في آخر لحظة بسبب الرياح، ورسو عشوائي فوق الشعاب المرجانية الحساسة، ويخوت تبحر بوثائق منتهية أو بصيانة متأخرة.

### 1.2 الفكرة

منصة واحدة تربط السائح ومالك اليخت ومدير المرسى ومزود الخدمة البحرية ومدير المنصة، وتجعل القرار التشغيلي مبنياً على بيانات حقيقية بدلاً من التقدير.

### 1.3 الأهداف

1. **منصة حجز مركزية**: بحث عن اليخوت وحجزها ودفع محاكى وإدارة دورة الحجز كاملة.
2. **تتبع GPS حي**: عرض مواقع اليخوت على خريطة مع المناطق البحرية، وتنبيه فوري عند المخالفات أو الاستغاثة.
3. **إدارة الصيانة**: خطط دورية تولد أوامر العمل تلقائياً بحسب ساعات تشغيل المحرك أو التاريخ، مع عروض أسعار من المزودين.
4. **واجهة سهلة**: واجهة عربية بالكامل، متجاوبة مع الجوال، بخطوط كبيرة وألوان رسمية.

### 1.4 ما يميز المشروع عن أنظمة الحجز التقليدية

الفرق الجوهري أن اليخت ليس سيارة: البحر يفرض قيوداً لا توجد على الطريق. لذلك تُطبق المنصة أربع خصائص لا توجد في أنظمة تأجير السيارات:

| الخاصية | في أنظمة الحجز التقليدية | في منصة اليخت الأحمر |
|---|---|---|
| الإتاحة | اليخت متاح إذا لم يكن محجوزاً | متاح فقط إذا كان الطقس المتوقع آمناً لفئة حجمه، ووثائقه سارية، ولا صيانة مجدولة |
| الموقع | لا يُتابع | تتبع حي مع مضلعات حظر رسو فوق الشعاب المرجانية وتنبيه تلقائي |
| الرسو | خارج النظام | مطابقة آلية لأنسب مربط بحسب طول اليخت وعرضه وغاطسه |
| التركيز | العميل الفرد (B2C) | لوجستيات الأعمال (B2B): المراسي ومزودو الصيانة والامتثال |

---

## 2. أصحاب المصلحة وأدوار المستخدمين

| الدور | من يمثله | الصلاحيات الرئيسية |
|---|---|---|
| سائح `tourist` | العميل الذي يحجز الرحلة | البحث، رؤية تقييم الطقس، الحجز والدفع المحاكى، الإلغاء، إعادة الجدولة عند تعليق الطقس، متابعة الرحلة الحية، زر الاستغاثة |
| مالك يخت `owner` | صاحب اليخت أو شركة التأجير | إدارة اليخوت والصور ومفاتيح أجهزة GPS، الموافقة على الحجوزات ورفضها، بدء الرحلة وإنهاؤها، خطط الصيانة وأوامر العمل، رفع الوثائق، طلب المرابط، خريطة الأسطول والتنبيهات |
| مدير مرسى `marina_manager` | إدارة المرسى | إدارة المرابط وأبعادها وحالتها، اعتماد طلبات الرسو ورفضها، متابعة نسب الإشغال، الخريطة الحية والتنبيهات |
| مزود خدمة `provider` | شركات الصيانة والتنظيف والوقود | رؤية أوامر العمل المطابقة لخدماته، تقديم عروض الأسعار، تنفيذ الأوامر المسندة وإنهاؤها |
| مدير المنصة `admin` | الجهة المشغلة للمنصة | إدارة المستخدمين، رسم المناطق البحرية، مراجعة الوثائق، اعتماد تصاريح الإبحار، التنبيهات الحرجة، سجل التدقيق، مؤشر صحة الخادم |

تُفرض الصلاحيات في مكانين: الخادم يرفض فتح أي صفحة لا تخص دور المستخدم قبل إرسالها (ملف `backend/routes/page_routes.py`)، وكل مسار API محمي بمزخرف (Decorator، أي دالة تغلف دالة أخرى لتضيف لها سلوكاً) مثل `@role_required("owner")`. كما يتحقق كل مسار من ملكية المورد، فلا يستطيع مالك رؤية حجوزات يخت مالك آخر ولو عرف رقمه.

---

## 3. التقنيات المستخدمة وسبب اختيارها

| التقنية | الاستخدام | سبب الاختيار |
|---|---|---|
| Python 3 و Flask 3.1.3 | الطرف الخلفي (Backend، أي الجزء الذي يعمل على الخادم) وواجهة API | إطار خفيف وواضح، مناسب للمبتدئين، ويسمح ببناء كل شيء يدوياً دون سحر مخفي |
| SQLite | قاعدة البيانات | ملف واحد لا يحتاج خادماً منفصلاً، مدمج في Python، ويكفي لحجم مشروع تخرج مع دعم المعاملات (Transactions) |
| Vanilla JavaScript | الواجهة الأمامية | دون أي إطار عمل، مما يجعل كل سطر مفهوماً وقابلاً للشرح أمام لجنة المناقشة |
| SVG | الرسوم البيانية وطبقة الخريطة | رسومات متجهية تُبنى بالكود مباشرة دون مكتبات خارجية |
| OpenStreetMap | بلاطات الخريطة (Tiles، أي صور مربعة صغيرة تُركب معاً لتكوين الخريطة) | مجانية ومفتوحة ولا تحتاج مفتاح API |
| Open-Meteo | توقعات الرياح وارتفاع الموج | خدمة مجانية تقدم بيانات بحرية (Marine API) بدقة ساعية دون تسجيل |
| bcrypt 5.0.0 | تجزئة كلمات السر | خوارزمية بطيئة عمداً تجعل كسر كلمات السر المسروقة مكلفاً جداً |
| python-dotenv 1.2.2 | قراءة ملف `.env` | فصل الأسرار والإعدادات عن الكود |
| requests 2.33.1 | جلب بيانات الطقس، ومحاكي GPS | أبسط مكتبة HTTP في Python |
| IBM Plex Sans Arabic | الخط | خط عربي رسمي واضح، مستضاف محلياً في `assets/fonts/` |
| Font Awesome 6.5.2 | الأيقونات | مستضافة محلياً في `assets/vendor/fontawesome/` |

لا يستخدم المشروع أي إضافة لـ Flask (مثل Flask-Login أو Flask-WTF)، فالجلسات وحماية CSRF وتحديد المحاولات مكتوبة يدوياً في `backend/security.py` لتكون مفهومة بالكامل.

---

## 4. هيكل المجلدات

```
red-yacht/
├── app.py                  نقطة التشغيل: إنشاء التطبيق، الترويسات الأمنية، معالجات الأخطاء
├── config.py               قراءة الإعدادات من .env وإنشاء المجلدات اللازمة
├── init_db.py              إنشاء الجداول وزرع البيانات التجريبية
├── requirements.txt        المكتبات المطلوبة بإصدارات مثبتة
├── .env.example            قالب المتغيرات دون قيم
├── .env                    القيم الفعلية (لا يُرفع إلى أي مستودع)
├── .gitignore              الملفات المستبعدة من المستودع
├── .htaccess               حماية الملفات الحساسة عند النشر على Apache
├── robots.txt              تعليمات محركات البحث
├── backend/
│   ├── db.py               الاتصال بقاعدة البيانات ودوال الاستعلام
│   ├── security.py         كلمات السر، الجلسات، CSRF، الصلاحيات، التحقق من المدخلات والملفات
│   ├── dates.py            التحويل بين UTC وتوقيت السعودية وصيغة العرض
│   ├── audit.py            تسجيل الإجراءات الحساسة
│   ├── notifications.py    إنشاء الإشعارات داخل النظام
│   ├── services/           منطق العمل (Business Logic)
│   │   ├── geo.py              Haversine و Ray Casting
│   │   ├── weather_service.py  جلب الطقس وتخزينه مؤقتاً وتقييمه
│   │   ├── booking_service.py  الإتاحة والتعارض والحجز والاسترداد وإعادة التقييم
│   │   ├── berthing_service.py مطابقة المرابط
│   │   ├── maintenance_service.py خطط الصيانة وتوليد أوامر العمل
│   │   ├── compliance_service.py الوثائق الإلزامية وانتهاؤها
│   │   └── tracking_service.py استقبال القراءات وكشف المخالفات
│   └── routes/             مسارات API، كل ملف لمجال واحد
│       ├── auth_routes.py  booking_routes.py  yacht_routes.py  weather_routes.py
│       ├── tracking_routes.py  zone_routes.py  marina_routes.py
│       ├── maintenance_routes.py  compliance_routes.py
│       ├── dashboard_routes.py  admin_routes.py
│       └── page_routes.py  تقديم صفحات HTML مع فحص الصلاحية
├── pages/                  24 صفحة HTML (هياكل فارغة يملؤها JavaScript)
├── assets/
│   ├── css/main.css        نظام التصميم كاملاً
│   ├── js/                 الوحدات المشتركة
│   │   ├── dates.js  api.js  ui.js  auth.js  charts.js  map.js
│   │   └── pages/          ملف JavaScript لكل صفحة
│   ├── fonts/              خط IBM Plex Sans Arabic بأربعة أوزان
│   ├── vendor/fontawesome/ الأيقونات
│   ├── images/             الشعار وأيقونة الموقع (Favicon)
│   └── data/coastline.json خط الساحل التقريبي للخريطة دون اتصال
├── tools/gps_simulator.py  محاكي جهاز GPS
├── tools/add_demo_photos.py إضافة الصور الافتراضية لقاعدة بيانات موجودة
├── seed/photos/            الصور الافتراضية لليخوت التجريبية (اسم الملف = رقم تسجيل اليخت)
├── data/                   ملف قاعدة البيانات (يُنشأ تلقائياً)
├── uploads/                الصور والوثائق المرفوعة بأسماء عشوائية
└── logs/app.log            سجل الأخطاء الدوار
```

### 4.1 لماذا صفحات HTML فارغة؟

كل ملف في `pages/` يحتوي فقط على الترويسة وروابط CSS وJavaScript وعنصر `<main id="app">`. ملف JavaScript الخاص بالصفحة يطلب البيانات من API ثم يبني العناصر. هذا الفصل يعني أن الخادم لا يدمج بيانات داخل HTML أبداً، فيصبح منع ثغرات XSS أسهل، ويمكن تطبيق سياسة CSP صارمة تمنع أي كود مضمَّن.

---

## 5. بنية قاعدة البيانات

تحتوي القاعدة على 23 جدولاً. كل الأوقات تُخزن بتوقيت UTC بصيغة `YYYY-MM-DDTHH:MM:SS`، وكل المبالغ تُخزن بالهللة (عدد صحيح) لتجنب أخطاء الكسور العشرية، فمبلغ 850 ريالاً يُخزن `85000`.

### 5.1 الجداول

| الجدول | وظيفته | أهم الحقول |
|---|---|---|
| `users` | المستخدمون بكل أدوارهم | `email` فريد، `password_hash`، `role`، `is_active`، `last_login_at` |
| `sessions` | الجلسات النشطة | `id` (تجزئة معرف الجلسة وليس المعرف نفسه)، `csrf_token`، `last_seen_at`، `revoked` |
| `login_attempts` | محاولات الدخول لتحديدها | `identifier` (البريد مع عنوان IP)، `success`، `attempted_at` |
| `provider_profiles` | بيانات مزودي الخدمة | `company_name`، `services` (قائمة الخدمات)، `rating_avg` |
| `marinas` | المراسي | `name`، `city`، `latitude`، `longitude`، `manager_id` |
| `berths` | المرابط داخل كل مرسى | `code`، `max_length_m`، `max_beam_m`، `max_draft_m`، `daily_rate_halalas`، `status` |
| `yachts` | اليخوت | `length_m`، `beam_m`، `draft_m`، `capacity`، `size_class`، `hourly_rate_halalas`، `engine_hours`، `status` |
| `yacht_photos` | صور اليخوت | `stored_name` (اسم عشوائي)، `mime_type`، `size_bytes` |
| `gps_devices` | أجهزة التتبع | `device_code`، `api_key_hash` (تجزئة SHA-256)، `last_seen_at` |
| `zones` | المناطق البحرية | `zone_type` (no_anchor، protected، restricted، cruising_area)، `polygon_json` |
| `bookings` | الحجوزات | `reference`، `start_at`، `end_at`، `guests`، `total_halalas`، `status`، `weather_status_at_booking` |
| `payments` | المدفوعات والمبالغ المستردة | `amount_halalas`، `status` (paid أو refunded)، `transaction_ref` |
| `berth_reservations` | حجوزات المرابط | `berth_id`، `yacht_id`، `start_at`، `end_at`، `status` |
| `positions` | قراءات GPS | `latitude`، `longitude`، `speed_knots`، `heading_deg`، `recorded_at` (وقت الجهاز)، `received_at` (وقت الخادم) |
| `alerts` | التنبيهات | `alert_type`، `severity`، `message`، `status` (open، acknowledged، resolved) |
| `weather_cache` | التخزين المؤقت للطقس | `grid_key`، `forecast_time`، `wind_speed_knots`، `wind_gust_knots`، `wave_height_m`، `source` |
| `maintenance_plans` | خطط الصيانة الدورية | `interval_engine_hours`، `interval_days`، `last_done_engine_hours`، `last_done_at` |
| `work_orders` | أوامر العمل | `priority`، `status`، `provider_id`، `quote_halalas`، `due_at`، `auto_generated` |
| `work_order_quotes` | عروض الأسعار | `amount_halalas`، `eta_days`، `status` (submitted، accepted، declined) |
| `compliance_documents` | الوثائق البحرية | `doc_type`، `doc_number`، `expires_at`، `status`، `reviewed_by` |
| `trip_permits` | تصاريح الإبحار | `booking_id` فريد، `status` (requested، approved، rejected) |
| `notifications` | الإشعارات | `title`، `body`، `link` (مسار داخلي فقط)، `is_read` |
| `audit_log` | سجل التدقيق | `action`، `entity`، `entity_id`، `ip_address` |

### 5.2 مخطط العلاقات

```
users 1───* yachts 1───* bookings *───1 users (السائح)
  │           │  │          │  │
  │           │  │          │  └──1 trip_permits
  │           │  │          └───* payments
  │           │  ├──1 gps_devices
  │           │  ├───* positions
  │           │  ├───* alerts
  │           │  ├───* yacht_photos
  │           │  ├───* compliance_documents
  │           │  ├───* maintenance_plans 1───* work_orders 1───* work_order_quotes *───1 users (المزود)
  │           │  └───* berth_reservations *───1 berths *───1 marinas *───1 users (مدير المرسى)
  │           └──1 marinas (المرسى الأساسي)
  ├───* sessions
  ├───* notifications
  └───* audit_log
zones 1───* bookings (منطقة الإبحار المصرح بها)
```

الرمز `1───*` يعني علاقة واحد إلى متعدد: مثلاً المالك الواحد يملك عدة يخوت، واليخت الواحد له عدة حجوزات. المفاتيح الأجنبية (Foreign Keys، أي حقول تشير إلى صف في جدول آخر) مفعّلة بالأمر `PRAGMA foreign_keys = ON`، وحذف يخت يحذف صوره ومواقعه ووثائقه تلقائياً بخاصية `ON DELETE CASCADE`.

### 5.3 الفهارس

أُضيفت فهارس (Indexes، هياكل تسرّع البحث مثل فهرس الكتاب) على الحقول التي يُبحث بها كثيراً، مثل `idx_positions_yacht` على `(yacht_id, recorded_at)` لأن الخريطة تطلب آخر موقع لكل يخت كل 10 ثوانٍ، و`idx_bookings_yacht` على `(yacht_id, start_at)` لأن كشف التعارض يعمل عند كل محاولة حجز.

---

## 6. الخوارزميات

كل الخوارزميات مكتوبة يدوياً دون مكتبات جغرافية أو رياضية، والمقتطفات التالية منقولة من الكود الفعلي.

### 6.1 Haversine: المسافة بين نقطتين على سطح الأرض

**المشكلة**: الأرض كروية، فلا يصح حساب المسافة بقانون فيثاغورس بين خطي العرض والطول.

**الحل**: صيغة Haversine تحسب طول القوس على سطح الكرة بين نقطتين. ملف `backend/services/geo.py`:

```python
def haversine_nm(lat1, lng1, lat2, lng2):
    """Haversine: المسافة على سطح كرة بين نقطتين، بالميل البحري."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_NM * math.asin(math.sqrt(a))
```

**الشرح**: تُحوَّل الدرجات إلى راديان، ثم يُحسب `a` وهو مربع نصف طول الوتر بين النقطتين، ثم الزاوية المركزية `2 * asin(sqrt(a))`، وتُضرب في نصف قطر الأرض بالميل البحري (3440.065).

**مثال محسوب**: المسافة من مرسى أبحر (21.7215، 39.098) إلى مركز منطقة شعاب أبحر الشمالية (21.745، 39.035) تساوي **3.79 ميل بحري** أي **7.01 كم** تقريباً.

### 6.2 Ray Casting: هل اليخت داخل منطقة محظورة؟

**المشكلة**: المناطق البحرية مضلعات بأي شكل، ونحتاج معرفة إن كانت نقطة GPS داخلها.

**الحل**: نطلق شعاعاً وهمياً أفقياً من النقطة نحو الشرق ونعد مرات عبوره لأضلاع المضلع. العدد الفردي يعني أن النقطة داخله، والزوجي يعني أنها خارجه.

```python
def point_in_polygon(lat, lng, polygon):
    """Ray Casting: نطلق شعاعاً أفقياً من النقطة ونعد تقاطعاته مع أضلاع المضلع.
    العدد الفردي يعني أن النقطة داخل المضلع."""
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        yi, xi = polygon[i]
        yj, xj = polygon[j]
        if (yi > lat) != (yj > lat):
            x_cross = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lng < x_cross:
                inside = not inside
        j = i
    return inside
```

**الشرح**: لكل ضلع بين الرأسين `i` و `j`، الشرط `(yi > lat) != (yj > lat)` يعني أن الضلع يقطع خط عرض النقطة. عندها يُحسب خط الطول `x_cross` الذي يحدث فيه التقاطع، فإن كان شرق النقطة تُعكس قيمة `inside`.

**مثال محسوب**: منطقة شعاب أبحر الشمالية مربع رؤوسه `[21.737, 39.026]`، `[21.737, 39.044]`، `[21.753, 39.044]`، `[21.753, 39.026]`.
- النقطة (21.745، 39.035): الشعاع نحو الشرق يقطع الضلع الشرقي فقط عند 39.044، أي تقاطع واحد (فردي)، فالنتيجة **داخل المنطقة**.
- النقطة (21.745، 39.050): تقع شرق الضلع الشرقي، فلا تقاطعات (صفر، زوجي)، فالنتيجة **خارج المنطقة**.

### 6.3 تقييم الطقس بالنسب

**المشكلة**: قارب طوله 10 أمتار لا يتحمل رياحاً يتحملها يخت طوله 30 متراً.

**الحل**: لكل فئة حجم حدود أمان للرياح والهبات والموج. لكل ساعة من ساعات الرحلة تُحسب نسبة كل قيمة إلى حدها، وأعلى نسبة خلال الرحلة كلها تحدد الحالة: أقل من 0.8 آمن، ومن 0.8 إلى 1.0 حذر، وأكثر من 1.0 غير آمن.

| الفئة | الطول | الرياح (عقدة) | الهبات (عقدة) | الموج (م) |
|---|---|---|---|---|
| صغير `small` | أقل من 12 م | 15 | 20 | 1.0 |
| متوسط `medium` | 12 إلى 24 م | 20 | 27 | 1.5 |
| كبير `large` | أكثر من 24 م | 25 | 33 | 2.5 |

```python
def assess(size_class, lat, lng, start, end):
    """تقييم الفترة: أعلى نسبة (القيمة / الحد) خلال ساعات الرحلة تحدد الحالة."""
    limits = LIMITS[size_class]
    fc = get_forecast(lat, lng)
    s = start.replace(minute=0, second=0)
    hours = [h for h in fc["hours"] if s <= parse_iso(h["time"]) < end]
    if not hours:
        return {"status": "unknown", "source": fc["source"], "max_ratio": None, "hours": [], "limits": limits}
    worst, worst_hour = 0.0, None
    for h in hours:
        r = max(h["wind"] / limits["wind"], h["gust"] / limits["gust"], h["wave"] / limits["wave"])
        if r > worst:
            worst, worst_hour = r, h
    status = "safe" if worst < 0.8 else ("caution" if worst <= 1.0 else "unsafe")
    return {"status": status, "source": fc["source"], "max_ratio": round(worst, 2), "worst_hour": worst_hour,
            "hours": hours, "limits": limits}
```

**مثال محسوب**: قارب صغير، وأسوأ ساعة في الرحلة فيها رياح 12 عقدة وهبات 15.6 عقدة وموج 0.69 م:
- نسبة الرياح = 12 ÷ 15 = **0.80**
- نسبة الهبات = 15.6 ÷ 20 = 0.78
- نسبة الموج = 0.69 ÷ 1.0 = 0.69

أعلى نسبة 0.80، فالحالة **حذر**، ويُطلب من السائح تأكيد الاطلاع على التحذير قبل الحجز. نفس الظروف ليخت كبير تعطي 12 ÷ 25 = 0.48 فالحالة **آمن**.

### 6.4 كشف التعارض الزمني

**القاعدة**: فترتان تتقاطعان إذا بدأت كل منهما قبل انتهاء الأخرى.

```python
def has_conflict(yacht_id, start, end, exclude_id=None):
    """كشف التعارض الزمني: فترتان تتقاطعان إذا بدأت كل منهما قبل انتهاء الأخرى."""
    sql = ("SELECT id FROM bookings WHERE yacht_id = ? AND status NOT IN ('cancelled','rejected','completed') "
           "AND start_at < ? AND end_at > ?")
    params = [yacht_id, to_iso(end), to_iso(start)]
    if exclude_id:
        sql += " AND id != ?"
        params.append(exclude_id)
    return query(sql, params, one=True) is not None
```

**مثال محسوب**: حجز قائم من 9:00ص إلى 1:00م، وطلب جديد من 12:00م إلى 3:00م. الشرط الأول: بداية القائم (9:00) قبل نهاية الجديد (15:00)، صحيح. الشرط الثاني: نهاية القائم (13:00) بعد بداية الجديد (12:00)، صحيح. إذن **يوجد تعارض**. أما طلب من 1:00م إلى 4:00م فلا يتعارض لأن نهاية القائم (13:00) ليست بعد بدايته (13:00).

الحجوزات الملغاة والمرفوضة والمكتملة مستبعدة من الفحص. كما يُعاد الفحص داخل معاملة `BEGIN IMMEDIATE` لحظة الإدخال، حتى لا ينجح حجزان متزامنان لنفس الفترة (مشكلة تسمى Race Condition).

### 6.5 مطابقة المربط بأفضل ملاءمة (Best Fit)

**المشكلة**: وضع يخت طوله 14 متراً في مربط طوله 45 متراً يهدر مربطاً كبيراً قد يحتاجه يخت كبير.

**الحل**: تُصفّى المرابط المتاحة التي تتسع لأبعاد اليخت مع هوامش أمان (0.5 م للطول، و0.3 م للعرض والغاطس)، ثم تُرتب بحسب الفائض في الطول تصاعدياً، ثم بالسعر.

```python
def match_berths(yacht, start, end, marina_id=None):
    sql = "SELECT b.*, m.name AS marina_name FROM berths b JOIN marinas m ON m.id = b.marina_id WHERE b.status = 'available' AND m.is_active = 1"
    params = []
    if marina_id:
        sql += " AND b.marina_id = ?"
        params.append(marina_id)
    result = []
    for b in query(sql, params):
        fits = (b["max_length_m"] >= yacht["length_m"] + MARGIN["length"] and
                b["max_beam_m"] >= yacht["beam_m"] + MARGIN["beam"] and
                b["max_draft_m"] >= yacht["draft_m"] + MARGIN["draft"])
        if fits and not reserved(b["id"], start, end):
            b["waste_m"] = round(b["max_length_m"] - yacht["length_m"], 2)
            result.append(b)
    result.sort(key=lambda x: (x["waste_m"], x["daily_rate_halalas"]))
    return result
```

**مثال محسوب**: يخت "لؤلؤة البحر" أبعاده 14.5 × 4.6 × 1.3 م، فيحتاج مربطاً لا يقل عن 15.0 × 4.9 × 1.6 م.
- مربط 14 × 5 × 2.0: الطول 14 أقل من 15، **مرفوض**.
- مربط 16 × 5.5 × 2.2: يتسع، والفائض 16 - 14.5 = **1.5 م**.
- مربط 18 × 6 × 2.4: يتسع، والفائض 3.5 م.
- مربط 45 × 11 × 4.2: يتسع، والفائض 30.5 م.

النتيجة الأولى هي مربط 16 متراً لأنه الأقل هدراً، ويظهر في الواجهة بعلامة "الأنسب".

### 6.6 توليد أوامر الصيانة تلقائياً

لكل يخت خطط صيانة، وكل خطة لها فاصل بساعات تشغيل المحرك أو بالأيام أو كليهما. يُنشأ أمر عمل تلقائياً عندما يبلغ الاستهلاك 90 بالمئة من فاصل الساعات، أو يتبقى 7 أيام أو أقل على الموعد، بشرط ألا يوجد أمر مفتوح لنفس الخطة.

```python
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
```

وتحدد الأولوية هكذا: **عاجلة** إذا تجاوز الموعد أو بلغت الساعات 120 بالمئة، و**عالية** إذا بلغت 100 بالمئة، و**عادية** فيما عدا ذلك.

**مثال محسوب**: خطة "تغيير زيت المحرك" كل 100 ساعة، آخر تنفيذ عند 0 ساعة، وعداد اليخت الآن 96 ساعة. الاستهلاك = (96 - 0) ÷ 100 = **0.96** أي 96 بالمئة، وهو أكبر من 90 بالمئة، فيُنشأ أمر عمل بأولوية **عادية** ويُشعَر المالك. إذا أنهى المالك رحلة استغرقت 5 ساعات صار العداد 101 ساعة، أي 101 بالمئة، فتصبح الأولوية لأي أمر جديد **عالية**.

يُستدعى التوليد عند إنهاء كل رحلة (بعد إضافة ساعات المحرك) وعند فتح لوحة المالك. وعندما يُسند أمر عاجل لمزود، يتحول اليخت تلقائياً إلى حالة "في الصيانة" فلا يظهر في البحث، ويعود نشطاً عند الإنجاز.

### 6.7 إعادة تقييم الحجوزات قبل الرحلة

توقعات الطقس تتغير، فالرحلة التي كانت آمنة عند الحجز قبل أسبوع قد لا تكون آمنة غداً. لذلك تُعاد تقييم كل الحجوزات المؤكدة التي تبدأ خلال 48 ساعة، وإذا صار الطقس غير آمن يتحول الحجز إلى "معلق بسبب الطقس" ويُشعَر السائح والمالك.

```python
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
```

تعمل الدالة عند فتح أي لوحة تحكم، مع حد أدنى 30 دقيقة بين كل تنفيذين حتى لا تُثقل الخادم. هذا بديل بسيط عن المجدولات الخارجية (مثل cron) لأن المشروع يعمل بأمر واحد.

عند التعليق يطلب السائح من المسار `/api/bookings/<id>/slots` أقرب 3 فترات آمنة بنفس مدة رحلته خلال 7 أيام، تبدأ بين 6 صباحاً و5 مساءً، ولا تتعارض مع حجوزات أخرى، ثم يختار إحداها بضغطة.

### 6.8 سياسة الاسترداد

```python
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
```

**مثال محسوب**: حجز 4 ساعات بسعر 850 ريالاً للساعة، الإجمالي 3,400 ريال.
- الإلغاء قبل 60 ساعة: استرداد كامل **3,400 ريال**.
- الإلغاء قبل 30 ساعة: استرداد النصف **1,700 ريال**.
- الإلغاء قبل 10 ساعات: لا استرداد.
- الإلغاء أثناء تعليق الطقس، أو رفض المالك للحجز: استرداد كامل دائماً، لأن السبب ليس من السائح.

كل استرداد يُسجل كصف جديد في جدول `payments` بحالة `refunded` دون تعديل الدفعة الأصلية، ليبقى السجل المالي كاملاً.

### 6.9 كشف الرسو في المنطقة المحظورة

قراءة واحدة بسرعة منخفضة لا تعني رسواً، فقد يكون اليخت يبطئ للالتفاف. لذلك يُشترط أن تكون **آخر 3 قراءات متتالية** بسرعة أقل من عقدة واحدة وكلها داخل نفس منطقة حظر الرسو.

```python
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
```

ولمنع إغراق المالك بالتنبيهات، لا يُنشأ تنبيه جديد من نفس النوع لنفس اليخت إذا وُجد تنبيه مفتوح خلال آخر 15 دقيقة، باستثناء نداء الاستغاثة الذي لا يُحجب أبداً. والتنبيهات الحرجة تصل أيضاً إلى مديري المنصة والمراسي.

---

## 7. آلية عمل المشروع

### 7.1 المكونات الثلاثة وكيف تتصل

```
المتصفح (HTML + CSS + JavaScript)
    │  طلب HTTP بصيغة JSON مع رمز CSRF وكوكي الجلسة
    ▼
Flask (app.py)
    │  1. before_request: حجب المسارات الحساسة، تحميل الجلسة، فحص CSRF
    │  2. المسار (routes): التحقق من الصلاحية والمدخلات
    │  3. الخدمة (services): منطق العمل والخوارزميات
    ▼
SQLite (data/red_yacht.db)
    │  استعلامات بمعاملات (Parameterized Queries)
    ▲
Flask
    │  4. after_request: إضافة الترويسات الأمنية
    ▼
المتصفح: يبني العناصر من JSON ويعرضها
```

### 7.2 صيغة الاستجابة الموحدة

كل مسارات API تعيد نفس الشكل، فتتعامل الواجهة مع كل الردود بطريقة واحدة:

```json
{ "ok": true, "data": { "id": 10, "reference": "RY-2026-372006" } }
{ "ok": false, "error": "اليخت محجوز في هذه الفترة." }
```

تُنتج هاتان الدالتان في `backend/security.py`:

```python
def ok(data=None, status=200):
    return jsonify({"ok": True, "data": data}), status
```

```python
def fail(message, status=400):
    return jsonify({"ok": False, "error": message}), status
```

### 7.3 طبقة الاتصال في الواجهة

ملف `assets/js/api.js` هو المكان الوحيد الذي يتصل بالخادم. يضيف رمز CSRF تلقائياً لكل طلب يغير البيانات، ويحول أي خطأ إلى رسالة عربية مفهومة:

```javascript
async function request(method, url, data, isForm) {
  const opts = { method, credentials: 'same-origin', headers: { Accept: 'application/json' } };
  if (method !== 'GET') {
    opts.headers['X-CSRF-Token'] = await ensureCsrf();
    if (isForm) {
      opts.body = data;
    } else if (data !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(data);
    }
  }
  ...
  if (!res.ok || !json.ok) { throw new ApiError(json.error || 'حدث خطأ غير متوقع.', res.status); }
  return json.data;
}
```

### 7.4 بناء العناصر بأمان

الدالة `UI.el` في `assets/js/ui.js` تبني أي عنصر HTML، وتضع النصوص دائماً عبر `textContent` وليس `innerHTML`. معنى ذلك أنه لو كتب مستخدم اسم يخته `<script>...</script>` فسيظهر كنص عادي ولن يُنفذ:

```javascript
function el(tag, attrs, ...children) {
  const node = document.createElement(tag);
  Object.entries(attrs || {}).forEach(([k, v]) => {
    if (v === null || v === undefined || v === false) { return; }
    if (k === 'class') {
      node.className = v;
    } else if (k === 'text') {
      node.textContent = v;
    } else if (k.startsWith('on') && typeof v === 'function') {
      node.addEventListener(k.slice(2), v);
    ...
```

### 7.5 مثال كامل: إنشاء حجز

1. **في المتصفح**: السائح يختار التاريخ والوقت في صفحة `yacht-details`. يحول `Dates.fromInput` الوقت المدخل من توقيت السعودية إلى UTC، ثم يطلب `GET /api/weather/assess` لعرض تقييم الطقس والأسباب المانعة والإجمالي قبل الدفع.
2. **نافذة الدفع المحاكى**: يضغط "ادفع وأرسل الطلب"، فيُرسل:
   ```json
   POST /api/bookings
   { "yacht_id": 2, "start_at": "2026-10-01T06:00:00", "end_at": "2026-10-01T09:00:00",
     "guests": 4, "purpose": "leisure", "route_zone_id": 5, "payer_name": "سارة", "ack_caution": false }
   ```
3. **في Flask قبل المسار**: يُحمل المستخدم من كوكي الجلسة، ويُقارن رمز CSRF في الترويسة بالمخزن في جلسته.
4. **في المسار** `booking_routes.create`: `@role_required("tourist")` يتأكد أنه سائح، وتتحقق دوال `v_int` و `v_datetime` و `v_choice` من كل حقل، وأي قيمة خاطئة ترفع `ValidationError` تتحول إلى رد 400 برسالة عربية.
5. **في الخدمة** `create_booking`: تُستدعى `availability_check` التي تفحص حالة اليخت، والسعة، والمدة (2 إلى 12 ساعة)، والبدء بعد ساعتين على الأقل، والتعارض، والصيانة، والوثائق السارية حتى نهاية الرحلة، والطقس. ثم داخل معاملة واحدة: إعادة فحص التعارض، وإنشاء رقم مرجعي فريد، وإدخال الحجز بحالة `pending`، وإدخال الدفعة، وإشعار المالك.
6. **الرد**: `{"ok": true, "data": {"id": 10, "reference": "RY-2026-372006"}}`، فتعرض الواجهة رسالة نجاح وتنتقل إلى "حجوزاتي".
7. **بعد ذلك**: يوافق المالك فيصبح الحجز `confirmed` ويُطلب تصريح إبحار تلقائياً، ثم يعتمد مدير المنصة التصريح، ولا يستطيع المالك بدء الرحلة قبل الاعتماد ولا قبل موعدها بأكثر من ساعة.

### 7.6 دورة حياة الحجز

```
pending ──(موافقة المالك)──▶ confirmed ──(بدء الرحلة، يتطلب تصريحاً معتمداً)──▶ in_progress ──(إنهاء مع ساعات المحرك)──▶ completed
   │                            │   ▲
   │(رفض المالك)                 │   │(إعادة الجدولة إلى فترة آمنة)
   ▼                            ▼   │
rejected                     weather_hold
   (أي حالة قبل in_progress يمكن أن تصبح cancelled بإلغاء السائح)
```

### 7.7 التواريخ وتوقيت السعودية

كل الأوقات تُخزن UTC، وتُعرض بتوقيت السعودية (UTC+3) بالصيغة `2026/1/3م 5:50ص`. في الجداول العربية كان حرف "م" ينفصل عن التاريخ بسبب خوارزمية ثنائية الاتجاه في المتصفح (Bidi)، فصار كل جزء من التاريخ والوقت يوضع في عنصر `span` معزول الاتجاه:

```javascript
wrap.className = 'dt';
wrap.dir = 'rtl';
const d = document.createElement('span');
d.dir = 'rtl';
d.textContent = p.date;
```

### 7.8 الخريطة المبنية يدوياً

ملف `assets/js/map.js` يبني خريطة انزلاقية دون أي مكتبة. يحول الإسقاط (Web Mercator) خطي العرض والطول إلى إحداثيات بكسل عند كل مستوى تكبير، ثم تُرسم بلاطات OpenStreetMap الظاهرة فقط، وفوقها طبقة SVG للمناطق ومسار الرحلة واليخوت:

```javascript
function project(lat, lng, z) {
  const size = TILE * Math.pow(2, z);
  const rad = (lat * Math.PI) / 180;
  return [((lng + 180) / 360) * size, ((1 - Math.log(Math.tan(rad) + 1 / Math.cos(rad)) / Math.PI) / 2) * size];
}
```

تدعم الخريطة السحب والتكبير بعجلة الفأرة وأزرار + و -، والنقر لرسم المضلعات في صفحة المناطق، ويدور شكل اليخت بحسب اتجاه حركته، ويتحول لونه إلى الأحمر عند وجود تنبيه وإلى الرمادي عند انقطاع الإشارة.

---

## 8. الأمان

| الإجراء | أين | لماذا |
|---|---|---|
| تجزئة كلمات السر بـ bcrypt (12 جولة) | `security.hash_password` | لو سُرقت قاعدة البيانات لا يمكن معرفة كلمات السر |
| معرف الجلسة عشوائي 256 بت، ويُخزن كتجزئة SHA-256 | `security.create_session` | لو سُربت القاعدة لا يمكن استخدام الجلسات المخزنة |
| كوكي الجلسة `HttpOnly` و `SameSite=Lax` و `Secure` في الإنتاج | `set_session_cookie` | JavaScript لا يستطيع قراءته، فلا تسرقه ثغرة XSS |
| انتهاء الجلسة بعد 30 دقيقة خمول | `load_session` | الجهاز المتروك مفتوحاً لا يبقى مسجلاً |
| رمز CSRF لكل جلسة، ورمز مؤقت للزوار في كوكي منفصل | `verify_csrf` | يمنع مواقع أخرى من إرسال طلبات باسم المستخدم |
| إيقاف الدخول 15 دقيقة بعد 5 محاولات فاشلة | `login_locked` | يمنع تخمين كلمات السر |
| رسالة دخول واحدة لكل الأخطاء | `auth_routes.login` | لا يعرف المهاجم إن كان البريد مسجلاً |
| استعلامات بمعاملات `?` في كل مكان | كل الملفات | يمنع حقن SQL |
| تحقق من كل مدخل في الخادم | دوال `v_*` | لا يُعتمد على تحقق الواجهة وحده |
| فحص نوع الملف الحقيقي من أول بايتات | `detect_mime` | ملف exe بامتداد pdf يُرفض |
| أسماء عشوائية للملفات المرفوعة، وتقديمها عبر مسار يتحقق من الملكية | `random_filename`، `/media/...` | يمنع تخمين المسارات وقراءة وثائق الآخرين |
| سياسة CSP صارمة: لا كود مضمن ولا مصادر خارجية إلا بلاطات الخريطة | `app.py` | حتى لو وُجدت ثغرة XSS لا يُنفذ كود المهاجم |
| `X-Frame-Options: DENY` و `nosniff` و `Referrer-Policy` و HSTS في الإنتاج | `app.py` | يمنع التضمين في إطارات، والتخمين الخاطئ لنوع الملف |
| إخفاء ترويسة `Server` وإصدار الخادم | `HideServerHeader`، `QuietRequestHandler` | لا يعرف المهاجم البرنامج وإصداره للبحث عن ثغراته |
| حجب ملفات `.env` وقاعدة البيانات والكود المصدري والسجلات | `before_request`، `.htaccess` | حتى لو أخطأ إعداد الخادم |
| منع إعادة التوجيه المفتوح | `safe_next` | رابط `?next=` يقبل المسارات الداخلية فقط |
| أجهزة GPS بمفتاح مجزأ يظهر مرة واحدة، وحد 60 طلباً في الدقيقة | `telemetry` | لا يمكن إرسال مواقع مزيفة ليخت آخر |
| رسائل أخطاء عامة، والتفاصيل في `logs/app.log` فقط | معالجات الأخطاء | لا تظهر تفاصيل داخلية للمستخدم |
| سجل تدقيق للإجراءات الحساسة | `audit.log_action` | معرفة من فعل ماذا ومتى |
| CORS مقيد بالنطاقات في `ALLOWED_ORIGINS` | `after_request` | لا يستطيع موقع آخر قراءة ردود API |

مثال: فحص نوع الملف الحقيقي:

```python
def detect_mime(head):
    for mime, sigs in MAGIC.items():
        for s in sigs:
            if head.startswith(s):
                if mime == "image/webp" and head[8:12] != b"WEBP":
                    continue
                return mime
    return None
```

مثال: المزخرف الذي يحمي المسارات بحسب الدور:

```python
def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not g.get("user"):
                return fail("يجب تسجيل الدخول أولاً.", 401)
            if g.user["role"] not in roles:
                return fail("ليست لديك صلاحية لتنفيذ هذا الإجراء.", 403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
```

---

## 9. التعامل مع ضعف الإنترنت

أشار مقترح المشروع إلى أن الإنترنت في عرض البحر الأحمر غير مستقر. عالجت المنصة ذلك في ثلاث طبقات:

**1. التخزين المؤقت للطقس**: تُحفظ توقعات 7 أيام لكل خلية جغرافية (تقريب الإحداثيات إلى 0.1 درجة، أي نحو 11 كم) لمدة 3 ساعات. إذا فشل الاتصال بـ Open-Meteo يستخدم النظام آخر بيانات محفوظة، ولا يعيد المحاولة قبل 10 دقائق حتى لا تتأخر الصفحات. وإن لم توجد بيانات محفوظة إطلاقاً يُولد توقع تقديري ثابت، وتعرض الواجهة مصدر البيانات بوضوح (حية، أو آخر بيانات محفوظة، أو تقديرية).

```python
def get_forecast(lat, lng):
    """يعيد {'source': live|cached|simulated, 'hours': [...]} مع تفضيل البيانات الحية."""
    key = grid_key(lat, lng)
    lat_g, lng_g = [float(x) for x in key.split(",")]
    fresh_since = to_iso(now_utc() - timedelta(hours=CACHE_HOURS))
    source = None
    if config.WEATHER_MODE == "live":
        fresh = query("SELECT COUNT(*) AS c FROM weather_cache WHERE grid_key = ? AND source = 'live' AND fetched_at >= ?",
                      (key, fresh_since), one=True)
        recent_fail = _last_fail.get(key)
        if fresh["c"] > 0:
            source = "live"
        elif recent_fail and now_utc() - recent_fail < timedelta(minutes=RETRY_AFTER_FAIL_MIN):
            source = None
        else:
            try:
                _store(key, _fetch_live(lat_g, lng_g), "live")
                source = "live"
            except Exception as exc:  # انقطاع الإنترنت أو خطأ في الخدمة
                log.warning("weather fetch failed for %s: %s", key, exc)
                _last_fail[key] = now_utc()
                any_live = query("SELECT COUNT(*) AS c FROM weather_cache WHERE grid_key = ? AND source = 'live' "
                                 "AND forecast_time >= ?", (key, now_iso()), one=True)
                source = "cached" if any_live["c"] > 0 else None
    if source is None:
        has_sim = query("SELECT COUNT(*) AS c FROM weather_cache WHERE grid_key = ? AND fetched_at >= ?",
                        (key, fresh_since), one=True)
        if has_sim["c"] == 0:
            _store(key, _simulated(lat_g, lng_g), "simulated")
        source = "simulated"
    since = to_iso(now_utc() - timedelta(hours=2))
    rows = query("SELECT forecast_time AS time, wind_speed_knots AS wind, wind_gust_knots AS gust, wave_height_m AS wave "
                 "FROM weather_cache WHERE grid_key = ? AND forecast_time >= ? ORDER BY forecast_time", (key, since))
    return {"source": source, "hours": rows}
```

**2. الإرسال بالدفعات**: جهاز GPS يخزن القراءات محلياً عند انقطاع الاتصال، ثم يرسلها دفعة واحدة (حتى 100 قراءة) عند عودته. كل قراءة تحمل وقت تسجيلها في الجهاز `recorded_at`، فيرتبها الخادم زمنياً ويقيّم كل واحدة، فلا تضيع مخالفة حدثت أثناء الانقطاع. جرّب ذلك بالخيار `--offline-burst` في المحاكي.

**3. آخر موقع معروف**: إذا لم تصل قراءة من يخت في رحلة جارية لأكثر من 10 دقائق، يُنشأ تنبيه "فقدان الإشارة"، ويبقى اليخت على الخريطة بآخر موقع معروف بلون رمادي. ونداء الاستغاثة لا يفشل أبداً: إن لم تتوفر إحداثيات جوال السائح يُستخدم آخر موقع لليخت.

وفي الواجهة، إذا تعذر تحميل بلاطات الخريطة تتحول تلقائياً إلى وضع دون اتصال يعرض شبكة إحداثيات وخط الساحل السعودي التقريبي من `assets/data/coastline.json`، مع بقاء المناطق واليخوت ظاهرة.

---

## 10. نموذج الذكاء الاصطناعي

**لا يستخدم المشروع أي نموذج ذكاء اصطناعي أو تعلم آلي.** كل القرارات "الذكية" (تقييم الطقس، كشف المخالفات، اختيار المربط، توقيت الصيانة، اقتراح الفترات الآمنة) مبنية على قواعد وخوارزميات حتمية: نفس المدخلات تعطي دائماً نفس النتيجة. هذا اختيار مقصود لأن القرارات هنا تتعلق بالسلامة البحرية، فيجب أن يكون كل قرار قابلاً للتفسير والمراجعة: يمكن دائماً معرفة لماذا رُفض الحجز (مثلاً: نسبة الموج 1.12 من الحد المسموح)، وهو ما لا يوفره نموذج تعلم آلي.

---

## 11. المتطلبات الأساسية

- Python 3.10 أو أحدث (للتحقق: `python --version`).
- pip، مدير حزم Python، ويأتي معه عادة.
- متصفح حديث (Chrome أو Edge أو Firefox أو Safari).
- اتصال بالإنترنت لتثبيت المكتبات مرة واحدة، ولعرض الخريطة الحقيقية والطقس الحي. المنصة تعمل دون إنترنت بعد التثبيت، لكن بخريطة مبسطة وطقس تقديري.

---

## 12. خطوات التركيب والتشغيل

### 12.1 تجهيز الإعدادات

المشروع يأتي بملف `.env` جاهز بقيم تطوير. عند النشر أو إعادة الإعداد، انسخ القالب واملأ القيم:

```bash
cp .env.example .env
```

| المتغير | المعنى | مثال |
|---|---|---|
| `APP_ENV` | `development` للتطوير و `production` للنشر | `development` |
| `SECRET_KEY` | مفتاح سري عشوائي 64 حرفاً على الأقل | يُولد بالأمر أدناه |
| `DATABASE_PATH` | مسار قاعدة البيانات | `data/red_yacht.db` |
| `SESSION_IDLE_MINUTES` | مدة الخمول قبل انتهاء الجلسة | `30` |
| `SEED_DEMO_PASSWORD` | كلمة سر الحسابات التجريبية | `RedYacht@2026` |
| `WEATHER_MODE` | `live` للطقس الحي أو أي قيمة أخرى للتقديري | `live` |
| `WEATHER_MARINE_URL` | رابط خدمة الموج | `https://marine-api.open-meteo.com/v1/marine` |
| `WEATHER_FORECAST_URL` | رابط خدمة الرياح | `https://api.open-meteo.com/v1/forecast` |
| `ALLOWED_ORIGINS` | النطاقات المسموح لها باستدعاء API | `http://127.0.0.1:5000` |
| `SIM_SERVER_URL` | عنوان الخادم للمحاكي | `http://127.0.0.1:5000` |
| `SIM_DEVICE_KEY` | مفتاح جهاز GPS التجريبي، يكتبه `init_db.py` تلقائياً | يُملأ تلقائياً |
| `HOST` و `PORT` | عنوان التشغيل ومنفذه | `127.0.0.1` و `5000` |

لتوليد مفتاح سري:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 12.2 التثبيت والتشغيل

افتح الطرفية (Terminal) داخل مجلد المشروع ثم نفذ:

```bash
pip install -r requirements.txt
python init_db.py
python app.py
```

ثم افتح المتصفح على: `http://127.0.0.1:5000`

- `pip install` يثبت المكتبات الأربع المطلوبة.
- `python init_db.py` ينشئ قاعدة البيانات ويزرع البيانات التجريبية ويكتب مفتاح جهاز GPS في `.env`. تشغيله مرة ثانية لا يمسح البيانات.
- `python app.py` يشغل الخادم. لإيقافه اضغط `Ctrl+C`.

لإعادة القاعدة إلى حالتها الأولى (يطلب كتابة RESET للتأكيد):

```bash
python init_db.py --reset
```

### 12.3 محاكي جهاز GPS

في طرفية ثانية والخادم يعمل:

```bash
python tools/gps_simulator.py
python tools/gps_simulator.py --anchor-violation
python tools/gps_simulator.py --offline-burst
python tools/gps_simulator.py --interval 2
```

| الأمر | ما يحدث |
|---|---|
| دون خيارات | اليخت "لؤلؤة البحر" يبحر في مسار دائري داخل منطقة إبحار أبحر ويرسل موقعه كل 5 ثوانٍ |
| `--anchor-violation` | اليخت يتوقف داخل "شعاب أبحر الشمالية"، وبعد 3 قراءات يظهر تنبيه حرج وإشعار للمالك ومدير المنصة |
| `--offline-burst` | ينقطع الاتصال دورياً لـ 8 قراءات تُخزن محلياً ثم تُرسل دفعة واحدة |
| `--interval N` | تغيير الفاصل بين القراءات إلى N ثانية |

افتح "خريطة الأسطول" بحساب المالك أثناء تشغيل المحاكي لترى اليخت يتحرك كل 10 ثوانٍ.

ملاحظة: الرحلة الجارية في البيانات التجريبية تبدأ قبل ساعة من وقت تشغيل `init_db.py` وتستمر 4 ساعات. إذا جربت المحاكي بعد انتهائها يُسجل الموقع دون ربطه برحلة. أعد التهيئة بـ `python init_db.py --reset` للحصول على رحلة جارية جديدة.

---

## 13. الحسابات التجريبية وسيناريو الاختبار

كلمة السر لكل الحسابات هي قيمة `SEED_DEMO_PASSWORD` في ملف `.env`، وقيمتها الافتراضية `RedYacht@2026`. في وضع التطوير تظهر هذه الحسابات في صفحة الدخول، والضغط على أي منها يعبئ البريد تلقائياً.

| الدور | البريد | ملاحظات |
|---|---|---|
| مدير المنصة | `admin@redyacht.sa` | |
| مدير مرسى | `marina@redyacht.sa` | يدير المراسي الثلاثة |
| مالك يخت | `owner@redyacht.sa` | يملك لؤلؤة البحر ونجمة أبحر والأسطورة |
| مالك يخت ثانٍ | `owner2@redyacht.sa` | يملك مرجان وأمواج أملج وصقر البحر |
| سائح | `tourist@redyacht.sa` | لديه رحلة جارية وحجوزات قادمة ومكتملة |
| مزود خدمة | `provider@redyacht.sa` | يقدم كل أنواع الخدمات |

### 13.1 البيانات التجريبية

- 3 مراسٍ: أبحر (جدة)، وينبع، وأملج، في كل منها 10 مرابط بأحجام من 10 إلى 45 متراً.
- 6 يخوت بأنواع وأحجام مختلفة. "لؤلؤة البحر" في رحلة جارية الآن، و"صقر البحر" فحص سلامته منتهٍ فلا يمكن حجزه، وتأمين "لؤلؤة البحر" ينتهي خلال 20 يوماً.
- 6 مناطق بحرية قرب جدة وأملج: منطقتا حظر رسو، ومحمية، ومنطقة مقيدة، ومنطقتا إبحار.
- حجوزات بكل الحالات، وأوامر صيانة (أحدها بعرض سعر بانتظار القبول)، وطلب مربط، ووثيقة بانتظار المراجعة.

### 13.2 الصور الافتراضية لليخوت

لكل يخت تجريبي صورة افتراضية حقيقية في مجلد `seed/photos/`، واسم كل ملف هو رقم تسجيل اليخت (مثل `KSA-JED-1021.jpg`). يربط `python init_db.py` هذه الصور باليخوت تلقائياً عند إنشاء قاعدة البيانات، فتظهر مباشرة في صفحة السائح.

إذا كانت قاعدة البيانات موجودة مسبقاً ولا تريد مسحها، أضف الصور بالأمر:

```bash
python tools/add_demo_photos.py
```

يتجاوز الأمر أي يخت لديه صور مسبقاً. ولاستبدال صور اليخوت التجريبية بالصور الافتراضية:

```bash
python tools/add_demo_photos.py --replace
```

الصور من موقع Pexels، وترخيصه يسمح باستخدامها مجاناً دون الحاجة لذكر المصدر.

### 13.3 سيناريو اختبار مقترح

**السائح**
1. افتح "اليخوت"، واختر تاريخاً بعد يومين. لاحظ شارة الطقس لكل يخت، وأن "صقر البحر" غير متاح بسبب الوثائق.
2. افتح تفاصيل يخت صغير وجرب عدة أوقات، حتى تجد فترة "غير آمنة" تُرفض، وفترة "آمنة" تكمل حجزها بالدفع المحاكى.
3. من "حجوزاتي" افتح الرحلة الجارية، وجرب زر "نداء استغاثة SOS".
4. ألغِ حجزاً ولاحظ مبلغ الاسترداد بحسب الوقت المتبقي.

**المالك**
1. من "الحجوزات" وافق على الطلب الجديد. سيظهر "التصريح قيد الاعتماد".
2. شغّل المحاكي بالخيار `--anchor-violation`، وافتح "خريطة الأسطول" لترى التنبيه، ثم اضغط "اطلاع" ثم "حل".
3. من "الصيانة" لاحظ أمر "تغيير زيت المحرك" المولد تلقائياً، واقبل عرض السعر على أمر "تنظيف وتلميع السطح".
4. من "يخوتي" اضغط "طلب مربط" ليخت، ولاحظ ترتيب المرابط بحسب الأقل هدراً.
5. من "الامتثال" ارفع وثيقة PDF.
6. أنهِ الرحلة الجارية وأدخل ساعات المحرك، ولاحظ توليد أوامر صيانة جديدة.

**مدير المنصة**
1. من "الامتثال" اعتمد تصريح الإبحار والوثيقة المرفوعة.
2. من "المناطق" اضغط "رسم منطقة جديدة"، وانقر 3 نقاط أو أكثر على الخريطة، واختر النوع واحفظ.
3. لاحظ مؤشر صحة الخادم في لوحة التحكم.
4. افتح "التدقيق" لترى كل ما سبق مسجلاً.

**مدير المرسى**: من "المرابط" اعتمد طلب الرسو، واضغط على أي مربط لتعديل أبعاده أو تحويله إلى صيانة. ومن "لوحة المرسى" تابع منحنى الإشغال.

**مزود الخدمة**: من "أوامر العمل" قدم عرضاً على أمر متاح. بعد قبول المالك، ابدأ التنفيذ ثم أنهِه، ولاحظ أن خطة الصيانة المرتبطة تُصفَّر تلقائياً.

---

## 14. مرجع واجهة API

الأدوار: `public` متاح للجميع، و `any` لأي مستخدم مسجل، وإلا فالأدوار المذكورة فقط. كل طلبات POST و PUT و DELETE تتطلب ترويسة `X-CSRF-Token` باستثناء `/api/telemetry` الذي يُحمى بمفتاح الجهاز في الترويسة `X-Device-Key`.

| المسار | الطريقة | الدور | الوظيفة |
|---|---|---|---|
| `/api/admin/audit` | GET | admin | سجل التدقيق مع التصفية بالإجراء |
| `/api/admin/documents` | GET | admin | الوثائق بحسب الحالة |
| `/api/admin/documents/<int:did>/decision` | POST | admin | اعتماد وثيقة أو رفضها |
| `/api/admin/permits` | GET | admin | تصاريح الإبحار بحسب الحالة |
| `/api/admin/permits/<int:pid>/decision` | POST | admin | اعتماد تصريح إبحار أو رفضه |
| `/api/admin/users` | GET | admin | قائمة المستخدمين |
| `/api/admin/users` | POST | admin | إنشاء مستخدم بأي دور |
| `/api/admin/users/<int:uid>` | PUT | admin | تعديل الاسم والجوال والدور |
| `/api/admin/users/<int:uid>/toggle` | POST | admin | تفعيل حساب أو تعطيله وإنهاء جلساته |
| `/api/admin/zones` | GET | admin | كل المناطق بما فيها المعطلة |
| `/api/admin/zones` | POST | admin | إنشاء منطقة بمضلع |
| `/api/admin/zones/<int:zid>` | DELETE | admin | حذف منطقة، أو تعطيلها إن ارتبطت بحجوزات |
| `/api/admin/zones/<int:zid>` | PUT | admin | تعديل منطقة |
| `/api/alerts` | GET | admin, marina_manager, owner | التنبيهات لليخوت المسموح بها |
| `/api/alerts/<int:aid>/acknowledge` | POST | admin, marina_manager, owner | تسجيل الاطلاع على تنبيه |
| `/api/alerts/<int:aid>/resolve` | POST | admin, marina_manager, owner | حل تنبيه |
| `/api/auth/csrf` | GET | public | رمز CSRF للزائر، ومؤشر وضع التطوير |
| `/api/auth/login` | POST | public | تسجيل الدخول |
| `/api/auth/logout` | POST | public | تسجيل الخروج وإلغاء الجلسة |
| `/api/auth/me` | GET | public | المستخدم الحالي ورمز CSRF لجلسته |
| `/api/auth/password` | PUT | any | تغيير كلمة السر وإنهاء الجلسات الأخرى |
| `/api/auth/profile` | PUT | any | تعديل الاسم والجوال |
| `/api/auth/register` | POST | public | تسجيل حساب سائح جديد |
| `/api/berth-reservations` | POST | owner | طلب حجز مربط |
| `/api/berths/match` | GET | owner | المرابط المناسبة لأبعاد اليخت بترتيب أفضل ملاءمة |
| `/api/bookings` | POST | tourist | إنشاء حجز مع الدفع المحاكى |
| `/api/bookings/<int:bid>` | GET | any | تفاصيل حجز لصاحبه أو لمالك اليخت أو للإدارة |
| `/api/bookings/<int:bid>/cancel` | POST | tourist | إلغاء حجز مع حساب الاسترداد |
| `/api/bookings/<int:bid>/reschedule` | POST | tourist | نقل الحجز إلى فترة جديدة بنفس المدة |
| `/api/bookings/<int:bid>/slots` | GET | tourist | أقرب 3 فترات آمنة لحجز معلق |
| `/api/bookings/mine` | GET | tourist | حجوزات السائح |
| `/api/dashboard/admin` | GET | admin | إحصاءات لوحة مدير المنصة |
| `/api/dashboard/marina` | GET | marina_manager, admin | الإشغال والطلبات لكل مرسى |
| `/api/dashboard/owner` | GET | owner | إحصاءات لوحة المالك والإيرادات |
| `/api/dashboard/provider` | GET | provider | إحصاءات مزود الخدمة |
| `/api/dashboard/tourist` | GET | tourist | حجوزات السائح القادمة مع طقسها الحالي |
| `/api/health` | GET | public | صحة الخادم وقاعدة البيانات وزمن الاستجابة |
| `/api/marina/berths` | POST | marina_manager, admin | إضافة مربط |
| `/api/marina/berths/<int:bid>` | PUT | marina_manager, admin | تعديل أبعاد المربط وحالته |
| `/api/marina/mine` | GET | marina_manager, admin | المراسي التي يديرها المستخدم |
| `/api/marina/reservations` | GET | marina_manager, admin | طلبات حجز المرابط |
| `/api/marina/reservations/<int:rid>/decision` | POST | marina_manager, admin | اعتماد طلب مربط أو رفضه |
| `/api/marinas` | GET | public | قائمة المراسي |
| `/api/marinas/<int:mid>/berths` | GET | any | مرابط مرسى مع اليخت الراسي حالياً |
| `/api/notifications` | GET | any | آخر 100 إشعار |
| `/api/notifications/<int:nid>/read` | POST | any | تحديد إشعار كمقروء |
| `/api/notifications/read-all` | POST | any | تحديد كل الإشعارات كمقروءة |
| `/api/notifications/unread-count` | GET | any | عدد الإشعارات غير المقروءة |
| `/api/owner/berth-reservations` | GET | owner | طلبات المرابط الخاصة بالمالك |
| `/api/owner/bookings` | GET | owner | حجوزات يخوت المالك |
| `/api/owner/bookings/<int:bid>/complete` | POST | owner | إنهاء الرحلة وإضافة ساعات المحرك |
| `/api/owner/bookings/<int:bid>/decision` | POST | owner | موافقة المالك على الحجز أو رفضه |
| `/api/owner/bookings/<int:bid>/start` | POST | owner | بدء الرحلة بعد اعتماد التصريح |
| `/api/owner/documents` | GET | owner | وثائق يخوت المالك ونسبة الامتثال |
| `/api/owner/documents` | POST | owner | رفع وثيقة للمراجعة |
| `/api/owner/maintenance/plans` | GET | owner | خطط الصيانة مع نسب التقدم |
| `/api/owner/maintenance/plans` | POST | owner | إضافة خطة صيانة |
| `/api/owner/maintenance/plans/<int:pid>` | DELETE | owner | حذف خطة |
| `/api/owner/maintenance/plans/<int:pid>` | PUT | owner | تعديل خطة |
| `/api/owner/work-orders` | GET | owner | أوامر العمل مع العروض |
| `/api/owner/work-orders` | POST | owner | إنشاء أمر عمل يدوي |
| `/api/owner/work-orders/<int:wid>/accept-quote` | POST | owner | قبول عرض وإسناد الأمر |
| `/api/owner/work-orders/<int:wid>/cancel` | POST | owner | إلغاء أمر عمل |
| `/api/owner/yachts` | GET | owner | يخوت المالك |
| `/api/owner/yachts` | POST | owner | إضافة يخت مع خطط صيانة افتراضية |
| `/api/owner/yachts/<int:yid>` | PUT | owner | تعديل يخت |
| `/api/owner/yachts/<int:yid>/device` | POST | owner | إنشاء مفتاح جهاز GPS جديد |
| `/api/owner/yachts/<int:yid>/photos` | POST | owner | رفع صورة لليخت |
| `/api/owner/yachts/<int:yid>/photos/<int:pid>` | DELETE | owner | حذف صورة |
| `/api/provider/work-orders` | GET | provider | الأوامر المتاحة والمسندة للمزود |
| `/api/provider/work-orders/<int:wid>/complete` | POST | provider | إنهاء أمر عمل |
| `/api/provider/work-orders/<int:wid>/quote` | POST | provider | تقديم عرض سعر أو تعديله |
| `/api/provider/work-orders/<int:wid>/start` | POST | provider | بدء تنفيذ أمر عمل |
| `/api/telemetry` | POST | public | استقبال قراءات جهاز GPS (بمفتاح الجهاز) |
| `/api/tracking/live` | GET | any | آخر موقع لكل يخت مسموح به مع تنبيهاته |
| `/api/tracking/sos` | POST | tourist | نداء استغاثة من السائح أثناء رحلته |
| `/api/tracking/trail/<int:bid>` | GET | any | مسار رحلة مسجل |
| `/api/weather/assess` | GET | public | تقييم الطقس والإتاحة والإجمالي لفترة |
| `/api/weather/forecast` | GET | public | توقع 72 ساعة لموقع |
| `/api/yachts` | GET | public | البحث عن اليخوت مع تقييم الطقس للفترة |
| `/api/yachts/<int:yid>` | GET | public | تفاصيل يخت |
| `/api/zones` | GET | public | المناطق النشطة |
| `/media/documents/<int:did>` | GET | any | ملف الوثيقة لمالكها أو للمدير |
| `/media/yachts/<int:pid>` | GET | public | صورة يخت |

---

## 15. إعدادات النشر وCloudflare

### 15.1 قبل النشر

1. غيّر `APP_ENV` إلى `production`. يؤدي ذلك إلى: تفعيل `Secure` في الكوكيز، والتحويل الإجباري إلى HTTPS، وتفعيل HSTS، وإخفاء الحسابات التجريبية من صفحة الدخول.
2. ولّد `SECRET_KEY` جديداً، وغيّر `SEED_DEMO_PASSWORD` أو احذف الحسابات التجريبية بعد إنشاء حسابات حقيقية.
3. عدّل `ALLOWED_ORIGINS` إلى نطاقك الفعلي.
4. شغّل التطبيق عبر خادم إنتاج مثل Waitress أو Gunicorn خلف Nginx أو Apache بدلاً من خادم التطوير المدمج، مع شهادة HTTPS.
5. تأكد أن المجلدات `data/` و `uploads/` و `logs/` غير قابلة للوصول من الويب (ملف `.htaccess` يتكفل بذلك على Apache).

### 15.2 إعدادات Cloudflare المرجعية

المشروع غير مربوط حالياً بـ Cloudflare. عند النشر خلفه يُنصح بالإعدادات التالية:

| الإعداد | القيمة المقترحة |
|---|---|
| SSL/TLS | Full (strict) |
| Always Use HTTPS | مفعّل |
| Minimum TLS Version | 1.2 |
| HSTS | مفعّل (التطبيق يرسله أيضاً) |
| WAF Managed Rules | مفعّلة |
| Bot Fight Mode | مفعّل |
| Rate Limiting | قاعدة على `/api/auth/login` بحد 10 طلبات في الدقيقة لكل IP |
| Cache Rules | تخزين `/assets/*` مؤقتاً، وتجاوز التخزين لـ `/api/*` و `/media/*` وكل الصفحات |
| Browser Integrity Check | مفعّل |
| Hide Server Header | عبر Transform Rules بحذف ترويسة `Server` |

المسار `GET /api/health` يعيد حالة الخادم وقاعدة البيانات وزمن الاستجابة دون أي معلومات عن الإصدارات، ويمكن استخدامه في مراقبة التوفر (Health Checks) في Cloudflare.

---

## 16. القيود الحالية والتطويرات المستقبلية

### 16.1 القيود الحالية

- **الدفع محاكى**: لا يُطلب أو يُخزن أي بيانات بطاقة، ويُسجل الدفع كعملية ناجحة مباشرة.
- **التصاريح داخلية**: اعتماد تصريح الإبحار يتم من مدير المنصة، وليس عبر ربط رسمي بحرس الحدود أو الهيئة العامة للنقل.
- **الأجهزة محاكاة**: لا يوجد جهاز GPS حقيقي، والمحاكي يرسل بنفس الصيغة التي سيرسل بها الجهاز الحقيقي.
- **المناطق تقريبية**: مضلعات الشعاب والمحميات في البيانات التجريبية توضيحية وليست خرائط ملاحية رسمية.
- **المهام الدورية**: إعادة تقييم الطقس وفحص الوثائق يعملان عند فتح اللوحات وليس بجدولة مستقلة، فلو لم يفتح أحد المنصة لا تعمل.
- **SQLite**: مناسبة لمشروع التخرج، لكنها محدودة مع عدد كبير جداً من الكتابات المتزامنة.
- **الإشعارات داخل النظام فقط**: لا يوجد إرسال بالبريد أو الرسائل النصية.

### 16.2 التطويرات المستقبلية

- ربط بوابة دفع حقيقية (مثل مدى أو Apple Pay عبر مزود معتمد).
- ربط رسمي مع الجهات التنظيمية البحرية لإصدار التصاريح والتحقق من الوثائق آلياً.
- أجهزة تتبع فضائية (Satellite Trackers) للمناطق التي لا تغطيها شبكات الجوال.
- استيراد مضلعات الشعاب والمحميات الرسمية من المصادر الحكومية.
- إشعارات بالرسائل النصية والبريد، خاصة لنداءات الاستغاثة.
- تطبيق جوال للربان يعمل كجهاز تتبع ويخزن القراءات دون اتصال.
- مجدول مهام مستقل (Scheduler) لإعادة التقييم والتنبيهات.
- الانتقال إلى PostgreSQL عند التوسع.
- نظام تقييمات للسياح والمزودين.

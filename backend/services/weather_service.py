"""الطقس البحري: جلب من Open-Meteo، تخزين مؤقت 3 ساعات، وبديل محاكى عند انقطاع الإنترنت."""
import logging
import math
from datetime import timedelta

import requests

import config
from backend.db import query, get_db
from backend.dates import now_utc, now_iso, parse_iso, to_iso

log = logging.getLogger("red_yacht")
CACHE_HOURS = 3
FORECAST_DAYS = 7

RETRY_AFTER_FAIL_MIN = 10
_last_fail = {}

LIMITS = {
    "small": {"wind": 15, "gust": 20, "wave": 1.0},
    "medium": {"wind": 20, "gust": 27, "wave": 1.5},
    "large": {"wind": 25, "gust": 33, "wave": 2.5},
}


def grid_key(lat, lng):
    return f"{round(lat, 1):.1f},{round(lng, 1):.1f}"


def _simulated(lat, lng):
    """توقع حتمي: نفس المدخلات تعطي نفس النتيجة، مع فترات رياح قوية دورية لإظهار أثر الطقس."""
    start = now_utc().replace(minute=0, second=0) - timedelta(hours=2)
    rows = []
    for h in range(FORECAST_DAYS * 24 + 2):
        t = start + timedelta(hours=h)
        idx = t.timestamp() / 3600.0
        daily = math.sin((t.hour - 9) / 24.0 * 2 * math.pi)
        synoptic = math.sin(idx / 37.0 + lat + lng)
        wind = max(2.0, 8 + 3.5 * daily + 6.5 * synoptic)
        gust = wind * 1.3
        wave = max(0.2, 0.15 + wind * 0.045)
        rows.append({"time": to_iso(t), "wind": round(wind, 1), "gust": round(gust, 1), "wave": round(wave, 2)})
    return rows


def _fetch_live(lat, lng):
    common = {"latitude": lat, "longitude": lng, "timezone": "UTC", "forecast_days": FORECAST_DAYS}
    r1 = requests.get(config.WEATHER_FORECAST_URL, timeout=8,
                      params={**common, "hourly": "wind_speed_10m,wind_gusts_10m", "wind_speed_unit": "kn"})
    r1.raise_for_status()
    r2 = requests.get(config.WEATHER_MARINE_URL, timeout=8, params={**common, "hourly": "wave_height"})
    r2.raise_for_status()
    w, m = r1.json()["hourly"], r2.json()["hourly"]
    waves = dict(zip(m["time"], m["wave_height"]))
    rows = []
    for t, ws, wg in zip(w["time"], w["wind_speed_10m"], w["wind_gusts_10m"]):
        if ws is None:
            continue
        wave = waves.get(t)
        rows.append({"time": t + ":00", "wind": float(ws), "gust": float(wg if wg is not None else ws * 1.3),
                     "wave": float(wave if wave is not None else 0.25 + ws * 0.055)})
    if not rows:
        raise ValueError("empty forecast")
    return rows


def _store(key, rows, source):
    db = get_db()
    fetched = now_iso()
    db.executemany("INSERT INTO weather_cache (grid_key, forecast_time, wind_speed_knots, wind_gust_knots, "
                   "wave_height_m, source, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?) "
                   "ON CONFLICT(grid_key, forecast_time) DO UPDATE SET wind_speed_knots = excluded.wind_speed_knots, "
                   "wind_gust_knots = excluded.wind_gust_knots, wave_height_m = excluded.wave_height_m, "
                   "source = excluded.source, fetched_at = excluded.fetched_at",
                   [(key, r["time"], r["wind"], r["gust"], r["wave"], source, fetched) for r in rows])
    db.commit()


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


def suggest_safe_slots(size_class, lat, lng, duration_hours, after, count=3):
    """أقرب فترات آمنة بنفس المدة خلال 7 أيام، تبدأ بين 6 صباحاً و5 مساءً بتوقيت السعودية."""
    fc = get_forecast(lat, lng)
    limits = LIMITS[size_class]
    by_time = {h["time"]: h for h in fc["hours"]}
    slots = []
    t = (after + timedelta(hours=1)).replace(minute=0, second=0)
    end_search = now_utc() + timedelta(days=FORECAST_DAYS)
    while t < end_search and len(slots) < count:
        local_hour = (t.hour + 3) % 24
        if 6 <= local_hour <= 17:
            ok_all, found = True, 0
            for i in range(duration_hours):
                h = by_time.get(to_iso(t + timedelta(hours=i)))
                if h is None:
                    ok_all = False
                    break
                found += 1
                r = max(h["wind"] / limits["wind"], h["gust"] / limits["gust"], h["wave"] / limits["wave"])
                if r >= 0.8:
                    ok_all = False
                    break
            if ok_all and found == duration_hours:
                slots.append({"start_at": to_iso(t), "end_at": to_iso(t + timedelta(hours=duration_hours))})
                t += timedelta(hours=duration_hours + 2)
                continue
        t += timedelta(hours=1)
    return slots

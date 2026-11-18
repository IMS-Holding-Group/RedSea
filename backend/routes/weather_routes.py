from flask import Blueprint, request
from backend.db import query
from backend.dates import parse_iso
from backend.security import ok, fail, in_red_sea
from backend.services import weather_service, booking_service

bp = Blueprint("weather", __name__, url_prefix="/api/weather")


@bp.get("/assess")
def assess():
    a = request.args
    if not a.get("yacht_id", "").isdigit():
        return fail("اليخت غير محدد.")
    y = query("SELECT * FROM yachts WHERE id = ?", (int(a["yacht_id"]),), one=True)
    start, end = parse_iso(a.get("start", "")), parse_iso(a.get("end", ""))
    if not y or not start or not end or end <= start:
        return fail("بيانات الفترة غير صحيحة.")
    reasons, weather = booking_service.availability_check(y, start, end, None)
    hours = (end - start).total_seconds() / 3600
    return ok({"weather": weather, "reasons": reasons, "total": round(hours * y["hourly_rate_halalas"] / 100, 2),
               "hours": hours})


@bp.get("/forecast")
def forecast():
    try:
        lat, lng = float(request.args.get("lat")), float(request.args.get("lng"))
    except (TypeError, ValueError):
        return fail("الإحداثيات غير صحيحة.")
    if not in_red_sea(lat, lng):
        return fail("الإحداثيات خارج نطاق البحر الأحمر.")
    fc = weather_service.get_forecast(lat, lng)
    return ok({"source": fc["source"], "hours": fc["hours"][:72]})

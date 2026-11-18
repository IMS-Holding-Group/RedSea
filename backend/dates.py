"""أدوات التاريخ. التخزين دائماً UTC بصيغة ISO، والعرض بتوقيت السعودية بالصيغة المعتمدة."""
from datetime import datetime, timedelta, timezone

KSA = timedelta(hours=3)
FMT = "%Y-%m-%dT%H:%M:%S"


def now_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def now_iso():
    return now_utc().strftime(FMT)


def to_iso(dt):
    return dt.strftime(FMT)


def parse_iso(value):
    """يقبل YYYY-MM-DDTHH:MM أو مع الثواني، ويعيد None إن كانت الصيغة غير صالحة."""
    if not isinstance(value, str):
        return None
    value = value.strip().replace("Z", "")[:19]
    for f in (FMT, "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(value, f)
        except ValueError:
            continue
    return None


def format_datetime(value):
    """يحول تاريخاً UTC إلى الصيغة: 2026/1/3م 5:50ص بتوقيت السعودية."""
    dt = parse_iso(value) if isinstance(value, str) else value
    if dt is None:
        return ""
    dt = dt + KSA
    hour12 = dt.hour % 12 or 12
    suffix = "ص" if dt.hour < 12 else "م"
    return f"{dt.year}/{dt.month}/{dt.day}م {hour12}:{dt.minute:02d}{suffix}"

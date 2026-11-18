"""خوارزميات جغرافية مكتوبة يدوياً."""
import json
import math

EARTH_RADIUS_NM = 3440.065  # نصف قطر الأرض بالميل البحري


def haversine_nm(lat1, lng1, lat2, lng2):
    """Haversine: المسافة على سطح كرة بين نقطتين، بالميل البحري."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_NM * math.asin(math.sqrt(a))


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


def zones_containing(lat, lng, zones):
    """يعيد المناطق النشطة التي تقع النقطة داخلها."""
    found = []
    for z in zones:
        poly = z["polygon"] if "polygon" in z else json.loads(z["polygon_json"])
        if point_in_polygon(lat, lng, poly):
            found.append(z)
    return found


def polygon_center(poly):
    return [sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)]

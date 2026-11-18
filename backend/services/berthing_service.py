"""مطابقة مرابط المراسي بخوارزمية أفضل ملاءمة (Best Fit)."""
from backend.db import query
from backend.dates import to_iso

MARGIN = {"length": 0.5, "beam": 0.3, "draft": 0.3}


def reserved(berth_id, start, end, exclude_id=None):
    sql = ("SELECT id FROM berth_reservations WHERE berth_id = ? AND status IN ('requested','approved') "
           "AND start_at < ? AND end_at > ?")
    params = [berth_id, to_iso(end), to_iso(start)]
    if exclude_id:
        sql += " AND id != ?"
        params.append(exclude_id)
    return query(sql, params, one=True) is not None


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

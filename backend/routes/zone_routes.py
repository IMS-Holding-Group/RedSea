import json
from flask import Blueprint, abort
from backend.db import query, execute
from backend.dates import now_iso
from backend.routes import body
from backend.security import ok, role_required, v_text, v_choice, v_polygon
from backend.audit import log_action

bp = Blueprint("zones", __name__, url_prefix="/api")
ZONE_TYPES = ("no_anchor", "protected", "restricted", "cruising_area")


def out(z):
    return {"id": z["id"], "name": z["name"], "zone_type": z["zone_type"], "polygon": json.loads(z["polygon_json"]),
            "description": z["description"], "is_active": z["is_active"]}


@bp.get("/zones")
def zones():
    return ok([out(z) for z in query("SELECT * FROM zones WHERE is_active = 1 ORDER BY id")])


@bp.get("/admin/zones")
@role_required("admin")
def all_zones():
    return ok([out(z) for z in query("SELECT * FROM zones ORDER BY id")])


def form():
    d = body()
    return (v_text(d, "name", "اسم المنطقة", 3, 80), v_choice(d, "zone_type", "نوع المنطقة", ZONE_TYPES),
            v_polygon(d.get("polygon")), v_text(d, "description", "الوصف", 0, 300, required=False) or "",
            1 if d.get("is_active", True) else 0)


@bp.post("/admin/zones")
@role_required("admin")
def create():
    from flask import g
    name, ztype, poly, desc, active = form()
    zid = execute("INSERT INTO zones (name, zone_type, polygon_json, description, is_active, created_by, created_at) "
                  "VALUES (?, ?, ?, ?, ?, ?, ?)", (name, ztype, json.dumps(poly), desc, active, g.user["id"], now_iso()))
    log_action("create_zone", "zones", zid)
    return ok({"id": zid}, 201)


@bp.put("/admin/zones/<int:zid>")
@role_required("admin")
def update(zid):
    if not query("SELECT id FROM zones WHERE id = ?", (zid,), one=True):
        abort(404)
    name, ztype, poly, desc, active = form()
    execute("UPDATE zones SET name = ?, zone_type = ?, polygon_json = ?, description = ?, is_active = ? WHERE id = ?",
            (name, ztype, json.dumps(poly), desc, active, zid))
    log_action("update_zone", "zones", zid)
    return ok()


@bp.delete("/admin/zones/<int:zid>")
@role_required("admin")
def delete(zid):
    if query("SELECT id FROM bookings WHERE route_zone_id = ? LIMIT 1", (zid,), one=True):
        execute("UPDATE zones SET is_active = 0 WHERE id = ?", (zid,))
    else:
        execute("DELETE FROM zones WHERE id = ?", (zid,))
    log_action("delete_zone", "zones", zid)
    return ok()

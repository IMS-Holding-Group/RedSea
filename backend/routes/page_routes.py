"""تقديم صفحات HTML مع التحقق من الصلاحية في الخادم قبل الإرسال."""
import os
from urllib.parse import quote
from flask import Blueprint, g, request, send_from_directory, redirect, abort

import config

bp = Blueprint("pages", __name__)

PAGES = {
    "index": None, "login": None, "yachts": None, "yacht-details": None, "error": None,
    "my-bookings": ("tourist",), "trip-live": ("tourist", "owner", "admin", "marina_manager"),
    "owner-dashboard": ("owner",), "owner-yachts": ("owner",), "owner-bookings": ("owner",),
    "owner-maintenance": ("owner",), "owner-compliance": ("owner",),
    "fleet-map": ("owner", "admin", "marina_manager"),
    "marina-dashboard": ("marina_manager", "admin"), "marina-berths": ("marina_manager", "admin"),
    "provider-dashboard": ("provider",), "provider-orders": ("provider",),
    "admin-dashboard": ("admin",), "admin-users": ("admin",), "admin-zones": ("admin",),
    "admin-compliance": ("admin",), "admin-audit": ("admin",),
    "notifications": "any", "profile": "any",
}
HOME = {"tourist": "/my-bookings", "owner": "/owner-dashboard", "marina_manager": "/marina-dashboard",
        "provider": "/provider-dashboard", "admin": "/admin-dashboard"}


def serve(name):
    roles = PAGES[name]
    if roles is not None:
        if not g.get("user"):
            return redirect("/login?next=" + quote(request.full_path.rstrip("?"), safe="/?=&"))
        if roles != "any" and g.user["role"] not in roles:
            abort(403)
    if name == "login" and g.get("user"):
        return redirect(HOME[g.user["role"]])
    resp = send_from_directory(config.PAGES_DIR, f"{name}.html", max_age=0)
    resp.headers["Cache-Control"] = "no-store"
    return resp


@bp.get("/")
def index():
    return serve("index")


@bp.get("/<page>")
def page(page):
    if page not in PAGES:
        abort(404)
    return serve(page)


@bp.get("/robots.txt")
def robots():
    return send_from_directory(config.BASE_DIR, "robots.txt", mimetype="text/plain")


@bp.get("/favicon.ico")
def favicon():
    return redirect("/assets/images/favicon.svg")

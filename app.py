"""نقطة تشغيل منصة اليخت الأحمر."""
import logging
import os
import re
from logging.handlers import RotatingFileHandler

from flask import Flask, request, g, redirect, send_from_directory
from werkzeug.exceptions import HTTPException
from werkzeug.serving import WSGIRequestHandler

import config
from backend.db import close_db
from backend.security import load_session, verify_csrf, fail, ValidationError
from backend.routes import (auth_routes, yacht_routes, booking_routes, weather_routes, tracking_routes, zone_routes,
                            marina_routes, maintenance_routes, compliance_routes, dashboard_routes, admin_routes, page_routes)

BLOCKED = re.compile(r"(^|/)\.|\.(env|db|sqlite3?|py|pyc|log|bak|backup|old|ini|cfg|conf|sql)$", re.I)
CSRF_EXEMPT = {"/api/telemetry"}
CSP = ("default-src 'self'; img-src 'self' data: https://tile.openstreetmap.org; script-src 'self'; style-src 'self'; "
       "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
ERRORS = {400: "الطلب غير صالح.", 401: "يجب تسجيل الدخول أولاً.", 403: "ليست لديك صلاحية للوصول.",
          404: "الصفحة أو المورد غير موجود.", 405: "الطريقة غير مسموحة.", 413: "حجم الطلب أكبر من المسموح.",
          429: "تم تجاوز عدد المحاولات المسموح.", 500: "حدث خطأ غير متوقع. حاول مرة أخرى لاحقاً."}


class HideServerHeader:
    """وسيط WSGI يخفي ترويسة Server التي يضيفها الخادم ويحذف X-Powered-By."""

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        def custom_start(status, headers, exc_info=None):
            headers = [(k, v) for k, v in headers if k.lower() not in ("server", "x-powered-by")]
            return start_response(status, headers, exc_info)
        return self.wsgi_app(environ, custom_start)


def setup_logging(app):
    handler = RotatingFileHandler(os.path.join(config.LOG_DIR, "app.log"), maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger = logging.getLogger("red_yacht")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    app.logger.addHandler(handler)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    return logger


def create_app():
    if not config.SECRET_KEY or len(config.SECRET_KEY) < 32:
        raise RuntimeError("SECRET_KEY غير مضبوط في ملف .env")
    app = Flask(__name__, static_folder=config.ASSETS_DIR, static_url_path="/assets")
    app.config.update(SECRET_KEY=config.SECRET_KEY, MAX_CONTENT_LENGTH=config.MAX_CONTENT_LENGTH, DEBUG=False,
                      PROPAGATE_EXCEPTIONS=False, JSON_AS_ASCII=False)
    app.json.ensure_ascii = False
    log = setup_logging(app)

    for mod in (auth_routes, yacht_routes, booking_routes, weather_routes, tracking_routes, zone_routes, marina_routes,
                maintenance_routes, compliance_routes, dashboard_routes, admin_routes, page_routes):
        app.register_blueprint(mod.bp)

    @app.before_request
    def before():
        if BLOCKED.search(request.path):
            return error_response(404)
        if config.IS_PRODUCTION and not request.is_secure and request.headers.get("X-Forwarded-Proto", "http") != "https":
            return redirect(request.url.replace("http://", "https://", 1), code=301)
        load_session()
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.path.startswith("/api/") \
                and request.path not in CSRF_EXEMPT and not verify_csrf():
            return fail("انتهت صلاحية الصفحة. أعد تحميلها وحاول مرة أخرى.", 403)

    @app.after_request
    def headers(resp):
        resp.headers["Content-Security-Policy"] = CSP
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        resp.headers["Permissions-Policy"] = "geolocation=(self), camera=(), microphone=()"
        if config.IS_PRODUCTION:
            resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        origin = request.headers.get("Origin")
        if origin and origin in config.ALLOWED_ORIGINS and request.path.startswith("/api/"):
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Credentials"] = "true"
            resp.headers["Vary"] = "Origin"
        if request.path.startswith("/api/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    def error_response(code):
        if request.path.startswith("/api/") or request.path.startswith("/media/"):
            return fail(ERRORS.get(code, ERRORS[500]), code)
        path = os.path.join(config.PAGES_DIR, "error.html")
        if not os.path.exists(path):
            return ERRORS.get(code, ERRORS[500]), code
        with open(path, encoding="utf-8") as f:
            html = f.read()
        return html, code, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store"}

    @app.errorhandler(ValidationError)
    def validation(exc):
        return fail(str(exc), 400)

    @app.errorhandler(HTTPException)
    def http_error(exc):
        return error_response(exc.code if exc.code in ERRORS else 500)

    @app.errorhandler(Exception)
    def unexpected(exc):
        log.exception("unhandled error on %s %s", request.method, request.path)
        return error_response(500)

    app.teardown_appcontext(close_db)
    app.wsgi_app = HideServerHeader(app.wsgi_app)
    return app


class QuietRequestHandler(WSGIRequestHandler):
    """يمنع خادم التطوير من إظهار اسمه وإصداره في ترويسة Server."""

    def version_string(self):
        return "web"


app = create_app()

if __name__ == "__main__":
    print(f"منصة اليخت الأحمر تعمل على http://{config.HOST}:{config.PORT}")
    app.run(host=config.HOST, port=config.PORT, debug=False, request_handler=QuietRequestHandler)

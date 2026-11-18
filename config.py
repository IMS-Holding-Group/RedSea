"""إعدادات التطبيق، تُقرأ كلها من ملف .env وقت التشغيل."""
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

APP_VERSION = "1.0.0"
APP_ENV = os.getenv("APP_ENV", "production")
IS_PRODUCTION = APP_ENV != "development"
SECRET_KEY = os.getenv("SECRET_KEY", "")
DATABASE_PATH = os.path.join(BASE_DIR, os.getenv("DATABASE_PATH", "data/red_yacht.db"))
SESSION_IDLE_MINUTES = int(os.getenv("SESSION_IDLE_MINUTES", "30"))
WEATHER_MODE = os.getenv("WEATHER_MODE", "live")
WEATHER_MARINE_URL = os.getenv("WEATHER_MARINE_URL", "")
WEATHER_FORECAST_URL = os.getenv("WEATHER_FORECAST_URL", "")
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "5000"))

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
LOG_DIR = os.path.join(BASE_DIR, "logs")
PAGES_DIR = os.path.join(BASE_DIR, "pages")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
MAX_CONTENT_LENGTH = 6 * 1024 * 1024

for _d in (os.path.dirname(DATABASE_PATH), UPLOAD_DIR, os.path.join(UPLOAD_DIR, "yachts"),
           os.path.join(UPLOAD_DIR, "documents"), LOG_DIR):
    os.makedirs(_d, exist_ok=True)

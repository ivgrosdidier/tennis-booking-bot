import os
from datetime import timedelta
from dotenv import load_dotenv

if os.getenv("K_SERVICE") is None:
    load_dotenv()

IS_CLOUD = os.getenv("K_SERVICE") is not None
IS_DEV = not IS_CLOUD

def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

class Config:
    SECRET_KEY = require_env("SECRET_KEY")
    FERNET_KEY = require_env("FERNET_KEY")

    # Google OAuth
    GOOGLE_CLIENT_ID = require_env("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = require_env("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI = require_env("GOOGLE_REDIRECT_URI")

    # Club
    CLUB_LOGIN_URL = require_env("CLUB_LOGIN_URL")

    # Session config
    SESSION_COOKIE_SECURE = IS_CLOUD
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    SESSION_REFRESH_EACH_REQUEST = True

    # Calendar
    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    DEFAULT_CALENDAR_NAME = "TennisBookingBot"

    # port 
    PORT = int(os.getenv("PORT", 8080))

    # Booking bot
    # SCHEDULER_SECRET = os.getenv("SCHEDULER_SECRET")
    # CLOUD_TASKS_QUEUE = os.getenv("CLOUD_TASKS_QUEUE")
    # CLOUD_RUN_URL = os.getenv("CLOUD_RUN_URL")
    # SERVICE_ACCOUNT_EMAIL = os.getenv("SERVICE_ACCOUNT_EMAIL")

import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    SECRET_KEY                = os.environ["SECRET_KEY"]
    FERNET_KEY                = os.environ["FERNET_KEY"]
    GOOGLE_CLIENT_ID          = os.environ["GOOGLE_CLIENT_ID"]
    GOOGLE_CLIENT_SECRET      = os.environ["GOOGLE_CLIENT_SECRET"]
    GOOGLE_REDIRECT_URI       = os.environ["GOOGLE_REDIRECT_URI"]
    CLUB_LOGIN_URL            = os.environ["CLUB_LOGIN_URL"]

    SESSION_COOKIE_SECURE     = True
    SESSION_COOKIE_HTTPONLY   = True
    SESSION_COOKIE_SAMESITE   = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    SESSION_REFRESH_EACH_REQUEST = True

SCOPES = ["https://www.googleapis.com/auth/calendar"]

DEFAULT_CALENDAR_NAME = "TennisBookingBot"
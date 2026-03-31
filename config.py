import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

IS_CLOUD = os.getenv('K_SERVICE') is not None
IS_DEV   = not IS_CLOUD

class Config:
    SECRET_KEY                = os.environ["SECRET_KEY"]
    FERNET_KEY                = os.environ["FERNET_KEY"]

    # google oauth
    GOOGLE_CLIENT_ID          = os.environ["GOOGLE_CLIENT_ID"]
    GOOGLE_CLIENT_SECRET      = os.environ["GOOGLE_CLIENT_SECRET"]
    GOOGLE_REDIRECT_URI       = os.environ["GOOGLE_REDIRECT_URI"]
    CLUB_LOGIN_URL            = os.environ["CLUB_LOGIN_URL"]

    # session config
    SESSION_COOKIE_SECURE     = IS_CLOUD
    SESSION_COOKIE_HTTPONLY   = True
    SESSION_COOKIE_SAMESITE   = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    SESSION_REFRESH_EACH_REQUEST = True

    # calendar
    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    DEFAULT_CALENDAR_NAME = "TennisBookingBot"

    # club 
    CLUB_LOGIN_URL = os.environ.get("CLUB_LOGIN_URL")

    # booking bot
    # SCHEDULER_SECRET      = os.environ.get("SCHEDULER_SECRET")
    # CLOUD_TASKS_QUEUE     = os.environ.get("CLOUD_TASKS_QUEUE")
    # CLOUD_RUN_URL         = os.environ.get("CLOUD_RUN_URL")
    # SERVICE_ACCOUNT_EMAIL = os.environ.get("SERVICE_ACCOUNT_EMAIL")
 


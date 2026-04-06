# routes/__init__.py
from .auth import auth_bp
from .dashboard import dashboard_bp
from .calendar import calendar_bp
from .credentials import credentials_bp
from .partners import partners_bp
from .settings import settings_bp
from .scheduled_jobs import scheduled_jobs_bp

# This is the list your app.py will loop through
all_blueprints = [
    auth_bp, dashboard_bp, calendar_bp, 
    credentials_bp, partners_bp, settings_bp, scheduled_jobs_bp
]
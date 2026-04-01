import os, json, sys, logging, firebase_admin
from firebase_admin import credentials, firestore
from flask import session, redirect, url_for 
from functools import wraps
from cryptography.fernet import Fernet
from config import Config, IS_DEV, IS_CLOUD

# logging
def get_logger(name):
    logger = logging.getLogger(name)
    
    # Only configure if handlers don't exist yet (prevents double-logging)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG if IS_DEV else logging.INFO)
        
        # Your clever logic for Cloud vs Local timestamps
        if IS_DEV:
            fmt = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
        else:
            fmt = "[%(levelname)s] %(name)s — %(message)s"
            
        formatter = logging.Formatter(fmt)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Critical: prevent logs from "bubbling up" to the root logger 
        # which might have different, messy settings.
        logger.propagate = False
        
    return logger

# Create a root logger for extensions itself
logger = get_logger(__name__)

# Firebase
firebase_config_json = os.getenv("FIREBASE_CONFIG_JSON")
 
if firebase_config_json:
    cred = credentials.Certificate(json.loads(firebase_config_json))
    logger.info("Firebase initialized from Secret Manager")
else:
    cred = credentials.Certificate("firebase-auth.json")
    logger.info("Firebase initialized from local firebase-auth.json")
 
firebase_admin.initialize_app(cred)
db = firestore.client()

# fernet encryption initialized at import time 
try:
    fernet = Fernet(Config.FERNET_KEY.encode())
except Exception as e:
    # This will give you a MUCH better log message if it fails again
    print(f"CRITICAL: Fernet Key Initialization Failed. Error: {e}")
    raise

# helper functions 
def get_current_uid() -> str:
    uid = session.get("user", {}).get("uid")
    if not uid:
        raise ValueError("No authenticated user uid found in session")
    return uid

def auth_required(f):
    """Decorator — redirects to login if user is not in session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            logger.warning("Unauthenticated access attempt")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated

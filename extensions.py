import os
import json
import logging
import firebase_admin
from firebase_admin import credentials, firestore
from cryptography.fernet import Fernet
from config import Config, IS_DEV, IS_CLOUD

# logging
# local: log to console with timestamp, level, module name 
# cloud run: log to console 
logging.basicConfig(
    level=logging.DEBUG if IS_DEV else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s" if IS_DEV
           else "[%(levelname)s] %(name)s — %(message)s"
    # Local:     2026-03-29 10:00:00 [INFO] routes.partners — Partner added uid=abc
    # Cloud Run: [INFO] routes.partners — Partner added uid=abc
    #            (Cloud Logging adds its own timestamp)
)
 
logger = logging.getLogger(__name__)

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

# fernet encryption
fernet = Fernet(Config.FERNET_KEY.encode())


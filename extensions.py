import firebase_admin
from firebase_admin import credentials, firestore
from cryptography.fernet import Fernet
from config import Config

# Firebase
cred = credentials.Certificate("firebase-auth.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Fernet encryption
fernet = Fernet(Config.FERNET_KEY.encode())
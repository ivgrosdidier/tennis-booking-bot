import os

firebaseConfig = {
    'apiKey':            os.environ.get("FB_API_KEY"),
    'authDomain':        os.environ.get("FB_AUTH_DOMAIN"),
    'projectId':         os.environ.get("FB_PROJECT_ID"),
    'storageBucket':     os.environ.get("FB_STORAGE_BUCKET"),
    'messagingSenderId': os.environ.get("FB_MESSAGING_SENDER_ID"),
    'appId':             os.environ.get("FB_APP_ID"),
}
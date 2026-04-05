import os
from flask import Flask, redirect, url_for, Response
from config import Config
from extensions import IS_CLOUD, IS_DEV, get_logger # Use the central logger logic

# logging
logger = get_logger("app_root")
logger.info(f"App started — IS_CLOUD={IS_CLOUD} IS_DEV={IS_DEV}")

# 1. env config
# Use the centralized IS_CLOUD from extensions
if not IS_CLOUD:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# initialize flask app
app = Flask(__name__)
app.config.from_object(Config)

# import blueprints 
from routes import all_blueprints
for bp in all_blueprints:
    app.register_blueprint(bp)

# routes
@app.route('/')
def home():
    return redirect(url_for('auth.login'))

@app.route("/firebase-config.js")
def firebase_config_js():
    config = {
        "apiKey":            os.environ.get("FIREBASE_API_KEY"),
        "authDomain":        os.environ.get("FIREBASE_AUTH_DOMAIN"),
        "projectId":         os.environ.get("FIREBASE_PROJECT_ID"),
        "storageBucket":     os.environ.get("FIREBASE_STORAGE_BUCKET"),
        "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID"),
        "appId":             os.environ.get("FIREBASE_APP_ID"),
    }
    js = f"""
import {{ initializeApp }} from "https://www.gstatic.com/firebasejs/10.9.0/firebase-app.js";
import {{ getAuth, GoogleAuthProvider }} from "https://www.gstatic.com/firebasejs/10.9.0/firebase-auth.js";
import {{ getFirestore }} from "https://www.gstatic.com/firebasejs/10.9.0/firebase-firestore.js";

const app = initializeApp({json.dumps(config)});
const auth = getAuth(app);
const provider = new GoogleAuthProvider();
const db = getFirestore(app);

export {{ auth, provider, db }};
"""
    return Response(js, mimetype="application/javascript")

# entry point
if __name__ == "__main__":
    # Cloud Run provides the PORT env var; default to 8080 for local testing
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
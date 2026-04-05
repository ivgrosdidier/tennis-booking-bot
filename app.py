import os
from flask import Flask, redirect, url_for, Response
from config import Config
from extensions import IS_CLOUD, IS_DEV, get_logger # Use the central logger logic
from routes import all_blueprints

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
for bp in all_blueprints:
    app.register_blueprint(bp)

# routes
@app.route('/')
def home():
    return redirect(url_for('auth.login'))

@app.route("/static/firebase-config.js")
def firebase_config_js():
    filename = os.environ.get("FIREBASE_CONFIG_FILE", "firebase-config.js")
    filepath = os.path.join(app.static_folder, filename)
    with open(filepath, "r") as f:
        content = f.read()
    return Response(content, mimetype="application/javascript")

# entry point
if __name__ == "__main__":
    # Cloud Run provides the PORT env var; default to 8080 for local testing
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
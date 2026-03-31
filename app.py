import os
from flask import Flask, redirect, url_for
from config import Config
from extensions import IS_CLOUD, IS_DEV, init_fernet, get_logger # Use the central logger logic
import traceback 

# logging
logger = get_logger("app_root")
logger.info(f"App started — IS_CLOUD={IS_CLOUD} IS_DEV={IS_DEV}")

# 1. ENVIRONMENT CONFIG
# Use the centralized IS_CLOUD from extensions
if not IS_CLOUD:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# 2. APP INITIALIZATION
app = Flask(__name__)
app.config.from_object(Config)

# init encryption
init_fernet(Config.FERNET_KEY)

# import blueprints 
from routes import all_blueprints
for bp in all_blueprints:
    app.register_blueprint(bp)

# 5. ROUTES
@app.route('/')
def home():
    return redirect(url_for('auth.login'))

# 6. ENTRY POINT
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080)) # Cloud Run sets this automatically
    app.run(host="0.0.0.0", port=port)
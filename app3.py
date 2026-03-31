import os
import logging
from flask import Flask, redirect, url_for
from config import Config
from extensions import IS_CLOUD # Use the central logger logic

# 1. ENVIRONMENT CONFIG
# Use the centralized IS_CLOUD from extensions
if not IS_CLOUD:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# 2. APP INITIALIZATION
app = Flask(__name__)
app.config.from_object(Config)

# 3. REGISTER BLUEPRINTS (The Clean Way)
# This one import replaces all 6 manual imports
from routes import all_blueprints

for bp in all_blueprints:
    app.register_blueprint(bp)

# 4. LOGGING
# Use your consistent get_logger function
logger = logging.getLogger(__name__)
logger.info(f"App started — IS_CLOUD={IS_CLOUD} IS_DEV={IS_DEV}")

# 5. ROUTES
@app.route('/')
def home():
    return redirect(url_for('auth.login'))

# 6. ENTRY POINT
if __name__ == "__main__":
    # Cloud Run uses PORT 8080 usually, local uses 5000
    port = int(os.environ.get("PORT", 5000))
    # debug=True only if we are NOT on the cloud
    app.run(debug=not IS_CLOUD, host="0.0.0.0", port=port)
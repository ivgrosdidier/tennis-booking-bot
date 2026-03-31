import os
import logging
from flask import Flask
from config import IS_DEV, IS_CLOUD, Config

# allows Oauth over plain HTTP when testing locally
if not IS_CLOUD:
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# app 
app = Flask(__name__)
app.config.from_object(Config)

# register blueprints
from routes.auth        import auth_bp
from routes.dashboard   import dashboard_bp
from routes.credentials import credentials_bp
from routes.calendar    import calendar_bp
from routes.partners    import partners_bp
from routes.settings    import settings_bp
 
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(credentials_bp)
app.register_blueprint(calendar_bp)
app.register_blueprint(partners_bp)
app.register_blueprint(settings_bp)

# logging
logger = logging.getLogger(__name__)
logger.info(f"App started — IS_CLOUD={IS_CLOUD} IS_DEV={IS_DEV}")

# entry point 
# local: runs flask dev server on port 5000
# cloud: gunicorn used 
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=IS_DEV, host="0.0.0.0", port=port)
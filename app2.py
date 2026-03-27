import os
from flask import Flask, redirect, url_for
from config import Config

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # remove in production

app = Flask(__name__)
app.config.from_object(Config)

# Register all route blueprints
from routes.auth        import auth_bp
from routes.dashboard   import dashboard_bp
from routes.calendar    import calendar_bp
from routes.credentials import credentials_bp
from routes.partners    import partners_bp
from routes.settings    import settings_bp

app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(calendar_bp)
app.register_blueprint(credentials_bp)
app.register_blueprint(partners_bp)
app.register_blueprint(settings_bp)

@app.route('/')
def home():
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, port=port)
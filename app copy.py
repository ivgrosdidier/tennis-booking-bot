import os
from flask import Flask
from config import Config
from extensions import IS_CLOUD

# Import your Blueprints
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
# ... import others

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    
    # Handle local insecure transport
    if not IS_CLOUD:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=not IS_CLOUD, host="0.0.0.0", port=port)



########################################
"""Logging setup """
# initialize logger
logger = logging.getLogger(__name__)

# Set Level based on K_SERVICE
if os.getenv('K_SERVICE'):
    logger.setLevel(logging.INFO)  # Cloud: Only show important stuff
else:
    logger.setLevel(logging.DEBUG) # Local: Show everything for debugging

# 3. Ensure logs go to "Stdout" (Cloud Run captures anything printed to the console)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(levelname)s | %(name)s | %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Configure session cookie settings
app.config['SESSION_COOKIE_SECURE'] = True  # Ensure cookies are sent over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access to cookies
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)  # Adjust session expiration as needed
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Can be 'Strict', 'Lax', or 'None'


app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")


# Fernet key for encrypting/decrypting sensitive data (e.g., user credentials)
FERNET_KEY = os.environ["FERNET_KEY"].encode()
fernet = Fernet(FERNET_KEY)

# Google OAuth 2.0 credentials for authenticating with Google services (e.g., Calendar API)
GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
GOOGLE_REDIRECT_URI = os.environ["GOOGLE_REDIRECT_URI"]

# get login URL
CLUB_LOGIN_URL = os.environ.get("CLUB_LOGIN_URL")

# set google cal scope
SCOPES = [
    #"openid",
    "https://www.googleapis.com/auth/calendar"
]

# Firebase Admin SDK setup

service_account_info = os.getenv("FIREBASE_CONFIG_JSON")

if service_account_info:
    # We are in the Cloud: Parse the string back into a dictionary
    info = json.loads(service_account_info)
    cred = credentials.Certificate(info)
    print("[Firebase] Initialized using Secret Manager")
else:
    # We are local: Fallback to the physical file
    cred = credentials.Certificate("firebase-auth.json")
    print("[Firebase] Initialized using local JSON file")

firebase_admin.initialize_app(cred)
db = firestore.client()

# Current — allows HTTP for OAuth (only safe locally)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Fix — only set this locally
if os.environ.get("FLASK_ENV") == "development":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

########################################
""" Helper functions """

def get_current_uid() -> str:
    user = session.get("user", {})
    uid = user.get("uid")
    if not uid:
        raise ValueError("No authenticated user uid found in session.")
    return uid


def encrypt_string(value: str) -> str:
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_string(value: str) -> str:
    return fernet.decrypt(value.encode("utf-8")).decode("utf-8")


def build_google_flow(state=None):
    return Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        state=state
    )


# function to get club players list from firestore or players file 
_players_cache = None 
def get_club_players():
    global _players_cache
    if _players_cache is not None:
        return _players_cache

    if not IS_CLOUD:
        # LOCAL: Load from the JSON file
        try:
            with open('data/players.json', 'r') as f:
                _players_cache = json.load(f)
            print("[Data] Loaded players from local JSON")
        except FileNotFoundError:
            _players_cache = {}
    else:
        # CLOUD: Pull from Firestore
        try:
            # Note: You named your collection "players" in Firestore
            players_ref = db.collection("players").stream()
            _players_cache = {doc.id: doc.to_dict().get('email') for doc in players_ref}
            print(f"[Firestore] Loaded {len(_players_cache)} players")
        except Exception as e:
            print(f"[Error] Firestore fetch failed: {e}")
            _players_cache = {}

    return _players_cache

########################################
""" Authentication and Authorization """

# Decorator for routes that require authentication
def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated
        if 'user' not in session:
            return redirect(url_for('login'))
        
        else:
            return f(*args, **kwargs)
        
    return decorated_function


@app.route('/auth', methods=['POST'])
def authorize():
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return "Unauthorized", 401

    token = token[7:]  # Strip off 'Bearer ' to get the actual token

    try:
        decoded_token = auth.verify_id_token(token, check_revoked=True, clock_skew_seconds=60) # Validate token here
        session['user'] = decoded_token # Add user to session
        return redirect(url_for('dashboard'))
    
    except:
        return "Unauthorized", 401


#####################
""" Public Routes """

@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    else:
        return render_template('login.html')

@app.route('/login')
def login():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    else:
        return render_template('login.html')

@app.route('/signup')
def signup():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    else:
        return render_template('signup.html')

@app.route('/reset-password')
def reset_password():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    else:
        return render_template('forgot_password.html')

@app.route('/instructions')
def instructions():
    return render_template('instructions.html')

@app.route('/logout')
def logout():
    session.pop('user', None)  # Remove the user from session
    response = make_response(redirect(url_for('login')))
    response.set_cookie('session', '', expires=0)  # Optionally clear the session cookie
    return response




##############################################
""" Autobook toggle """

@app.route('/toggle-autobook', methods=['POST'])
@auth_required
def toggle_autobook():
    uid = get_current_uid()
    enabled = 'autobook_enabled' in request.form

    db.collection('users').document(uid).set({
        'autobook_enabled': enabled
    }, merge=True)

    if enabled:
        status = "enabled"
        flash(f"Auto-book is now {status}.", "success")
    else:
        status = "disabled"
        flash(f"Auto-book is now {status}.", "error")

    return redirect(url_for('dashboard'))


##############################################
""" Card 1: Save tennis credentials """

# test tennis credentials

##############################################
""" Card 3: Save and delete players """

_players_cache = None

def get_club_players():
    global _players_cache

    # 1. Return the memory cache if it already exists
    if _players_cache is not None:
        return _players_cache

    try:
        # 2. Pull all documents from your new collection
        # .stream() is efficient for reading the whole collection at once
        players_ref = db.collection("club_players").stream()
        
        # 3. Rebuild the dictionary: { "Player Name": "email@example.com" }
        # doc.id is the Name (since we used it as the Document ID)
        # doc.to_dict().get('email') fetches the email field inside
        _players_cache = {
            doc.id: doc.to_dict().get('email') 
            for doc in players_ref
        }
        
        print(f"[Firestore] Loaded {len(_players_cache)} players into cache")
        
    except Exception as e:
        print(f"[ERROR] Could not fetch players from Firestore: {e}")
        # Initialize as empty dict so the app doesn't crash on lookup
        _players_cache = {}

    return _players_cache

def check_name_in_club_directory(full_name):
    """
    Returns True if the titled name exists in players.json.
    Returns False if not found.
    """
    players = get_club_players()
    return full_name.strip().title() in players




if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
from flask import Flask, redirect, render_template, request, make_response, session, abort, jsonify, url_for, flash
import requests 
from bs4 import BeautifulSoup
from functools import wraps
import firebase_admin
from firebase_admin import credentials, firestore, auth
from datetime import timedelta
import os
import json
from cryptography.fernet import Fernet, InvalidToken
from google_auth_oauthlib.flow import Flow 
from googleapiclient.discovery import build
import random, string
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Configure session cookie settings
app.config['SESSION_COOKIE_SECURE'] = True  # Ensure cookies are sent over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access to cookies
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)  # Adjust session expiration as needed
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Can be 'Strict', 'Lax', or 'None'

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
cred = credentials.Certificate("firebase-auth.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1" #only for development/testing

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
""" Private Routes (Require authorization) """

@app.route('/dashboard')
@auth_required
def dashboard():
    uid = get_current_uid()
    user_ref = db.collection('users').document(uid)
    user_doc = user_ref.get()

    data = user_doc.to_dict() if user_doc.exists else {}

    autobook_enabled = data.get('autobook_enabled', False)
    club_profile_connected = data.get('club_profile_connected', False)
    google_calendar_connected = data.get('google_calendar_connected', False)

    # get partner names 
    partners_docs = db.collection('users').document(uid).collection('partners').get()
    partners = [{'id': doc.id, **doc.to_dict()} for doc in partners_docs]

    return render_template(
        'dashboard.html',
        autobook_enabled=autobook_enabled,
        club_profile_connected=club_profile_connected,
        google_calendar_connected=google_calendar_connected,
        partners=partners
    )


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
def test_login_credentials(username, password):
    try:
        with requests.Session() as s:
        # 1. Load page (gets cookies)
            s.get(CLUB_LOGIN_URL)

            # 2. Send login request
            resp = s.post(CLUB_LOGIN_URL, data={
                "userId": username,
                "password": password
            })

            html = resp.text.lower()

            # 3. Check result
            if "your email address or password is incorrect" in html:
                return False, "Invalid credentials"

            if "welcome" in html:
                return True, "Login successful"

            return False, "Could not determine login result"

    except requests.RequestException as e:
        return False, f"Network error while testing login: {e}"
    except Exception as e:
        return False, f"Unexpected error while testing login: {e}"


@app.route('/save-tennis-credentials', methods=['POST'])
@auth_required
def save_tennis_credentials():
    uid = get_current_uid()

    tennis_username = request.form.get('tennis_username')
    tennis_password = request.form.get('tennis_password') 

    is_valid, message = test_login_credentials(tennis_username, tennis_password)

    if not is_valid:
        db.collection('users').document(uid).set({
            'tennis_username_encrypted': None,
            'tennis_password_encrypted': None,
            'club_profile_connected': False
        }, merge=True)
        flash(f'Tennis login failed: {message}', 'error')
        return redirect(url_for('dashboard'))
    
    else:
        encrypted_username = encrypt_string(tennis_username)
        encrypted_password = encrypt_string(tennis_password)

        db.collection('users').document(uid).set({
            'tennis_username_encrypted': encrypted_username,
            'tennis_password_encrypted': encrypted_password,
            'club_profile_connected': True
        }, merge=True)

        flash('Tennis credentials saved.', 'success')
        return redirect(url_for('dashboard'))



##############################################
""" Card 2: Connect to Google Cal """

DEFAULT_CALENDAR_NAME = "TennisBookingBot"

@app.route('/connect-google-calendar', methods=['POST'])
@auth_required
def connect_google_calendar():
    calendar_name = (request.form.get('calendar_name') or '').strip() or DEFAULT_CALENDAR_NAME

    session["requested_calendar_name"] = calendar_name

    flow = build_google_flow()
    flow.redirect_uri = GOOGLE_REDIRECT_URI

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent"
    )

    session["google_oauth_state"] = state
    session["google_oauth_verifier"] = flow.code_verifier
    return redirect(authorization_url)


@app.route('/oauth2callback')
@auth_required
def oauth2callback():
    uid = get_current_uid()

    state = session.get("google_oauth_state")
    verifier = session.get("google_oauth_verifier")

    requested_calendar_name = session.get("requested_calendar_name", DEFAULT_CALENDAR_NAME)

    if not state or not requested_calendar_name:
        flash("Google Calendar connection failed. Please try again.", "calendar")
        return redirect(url_for("dashboard"))

    flow = build_google_flow(state=state)
    flow.redirect_uri = GOOGLE_REDIRECT_URI
    flow.fetch_token(authorization_response=request.url, code_verifier=verifier)

    credentials = flow.credentials
    service = build("calendar", "v3", credentials=credentials)

    calendars = service.calendarList().list().execute().get("items", [])
    requested_lower = requested_calendar_name.strip().lower()

    matched_calendar = next(
        (cal for cal in calendars if (cal.get("summary") or "").strip().lower() == requested_lower),
        None
    )

    # if not found, create calendar
    if not matched_calendar:
        new_calendar = service.calendars().insert(body={
            "summary": requested_calendar_name,
            "description": "Managed by TennisBookingBot",
            "timeZone": "America/Toronto"  # adjust or make dynamic
        }).execute()

        # Add it to the user's calendar list so it appears in their Google Cal
        service.calendarList().insert(body={"id": new_calendar["id"]}).execute()

        calendar_id = new_calendar["id"]
        calendar_summary = new_calendar["summary"]
        was_created = True
    else:
        calendar_id = matched_calendar["id"]
        calendar_summary = matched_calendar.get("summary")
        was_created

    db.collection('users').document(uid).set({
        'google_calendar_connected': True,
        'google_calendar_name': calendar_summary,
        'google_calendar_id': calendar_id,
        'google_refresh_token_encrypted': encrypt_string(credentials.refresh_token) if credentials.refresh_token else None,
    }, merge=True)

    if was_created:
        flash(f'No calendar named "{requested_calendar_name}" was found. BookingBot created it for you!', 'success')
    else:
        flash(f'Google Calendar connected to "{calendar_summary}".', 'success')

    return redirect(url_for("dashboard"))


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


@app.route('/add-partner', methods=['POST'])
@auth_required
def add_partner():
    uid = get_current_uid()
    full_name = request.form.get('full_name').strip().title()
    nickname = request.form.get('nickname').strip().title()

    if full_name and nickname:

        if not check_name_in_club_directory(full_name):
            flash(
                f'Player name "{full_name}" not found in club directory. '
                f'Please check the spelling.',
                'error'
            )
            return redirect(url_for('dashboard'))

        partners_ref = db.collection('users').document(uid).collection('partners')

        # Check if this full name already has an entry for this user
        existing_name = partners_ref.where('full_name', '==', full_name).get()
        if existing_name:
            flash(f'"{full_name}" already has a nickname. Edit the existing entry instead.', 'error')
            return redirect(url_for('dashboard'))
        
        # Check for duplicate nickname for this user
        existing = partners_ref.where('nickname', '==', nickname).get()
        if existing:
            flash('Nickname already exists. Edit the existing one or choose a different nickname.', 'error')
            return redirect(url_for('dashboard'))
        
        partner_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))      

        partners_ref.add({
            'partner_id': partner_id,
            'full_name': full_name,
            'nickname': nickname
        })
        flash('Partner added!', 'success')

    return redirect(url_for('dashboard'))

@app.route('/edit-partner/<partner_id>', methods=['POST'])
@auth_required
def edit_partner(partner_id):
    uid = get_current_uid()
    # Get the updated text from the editable inputs in the table
    new_name = request.form.get('full_name').strip().title()
    new_nick = request.form.get('nickname').strip().title()

    # Check against club directory first — block if not found
    if not check_name_in_club_directory(new_name):
        flash(
            f'Player name "{new_name}" not found in club directory. '
            f'Please check the spelling.',
            'error'
        )
        return redirect(url_for('dashboard'))

    partners_ref = db.collection('users').document(uid).collection('partners')

    # Check if this full name already exists on a DIFFERENT partner entry
    existing_name = partners_ref.where('full_name', '==', new_name).get()
    for doc in existing_name:
        if doc.id != partner_id:
            flash(f'"{new_name}" already has a nickname. Edit the existing entry instead.', 'error')
            return redirect(url_for('dashboard'))

    # Check for duplicate nickname excluding self
    existing = partners_ref.where('nickname', '==', new_nick).get()
    for doc in existing:
        if doc.id != partner_id:
            flash('Nickname already in use by another partner.', 'error')
            return redirect(url_for('dashboard'))

    partners_ref.document(partner_id).update({
        'full_name': new_name,
        'nickname': new_nick
    })
    flash('Partner updated!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/delete-partner/<partner_id>', methods=['POST'])
@auth_required
def delete_partner(partner_id):
    uid = get_current_uid()
    db.collection('users').document(uid).collection('partners').document(partner_id).delete()
    flash('Partner removed.', 'success')
    return redirect(url_for('dashboard'))



##############################################
""" Settings functions """
@app.route('/settings')
@auth_required
def settings():
    uid = get_current_uid()
    return render_template('settings.html')


@app.route('/delete-account', methods=['POST'])
@auth_required
def delete_account():
    uid = get_current_uid()

    try:
        # Step 1 — Delete partners subcollection
        # Firestore does NOT auto-delete subcollections when parent is deleted
        partners = db.collection('users').document(uid).collection('partners').get()
        for partner in partners:
            partner.reference.delete()

        # Step 2 — Delete the user document itself
        db.collection('users').document(uid).delete()

        # Step 3 — Clear the Flask session
        session.clear()

        print(f"[Account Deletion] Successfully deleted all data for uid={uid}")
        flash('Your account has been permanently deleted.', 'success')

    except Exception as e:
        print(f"[Account Deletion] Error deleting uid={uid}: {e}")
        flash('Something went wrong while deleting your account. Please try again.', 'error')
        return redirect(url_for('settings'))

    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
from flask import Blueprint, redirect, render_template, request
from flask import make_response, session, url_for
from firebase_admin import auth

auth_bp = Blueprint('auth', __name__)

def get_current_uid() -> str:
    user = session.get("user", {})
    uid = user.get("uid")
    if not uid:
        raise ValueError("No authenticated user uid found in session.")
    return uid


def auth_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/auth', methods=['POST'])
def authorize():
    token = request.headers.get('Authorization', '')
    if not token.startswith('Bearer '):
        return "Unauthorized", 401
    try:
        decoded = auth.verify_id_token(token[7:], check_revoked=True, clock_skew_seconds=60)
        session['user'] = decoded
        return redirect(url_for('dashboard.dashboard'))
    except:
        return "Unauthorized", 401


@auth_bp.route('/login')
def login():
    if 'user' in session:
        return redirect(url_for('dashboard.dashboard'))
    return render_template('login.html')


@auth_bp.route('/signup')
def signup():
    if 'user' in session:
        return redirect(url_for('dashboard.dashboard'))
    return render_template('signup.html')


@auth_bp.route('/reset-password')
def reset_password():
    return render_template('forgot_password.html')


@auth_bp.route('/logout')
def logout():
    session.pop('user', None)
    response = make_response(redirect(url_for('auth.login')))
    response.set_cookie('session', '', expires=0)
    return response
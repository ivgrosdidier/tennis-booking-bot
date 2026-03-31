import logging
from functools import wraps
from flask import Blueprint, redirect, render_template, request, make_response, session, url_for
from firebase_admin import auth

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)


# ── Shared helpers (imported by other route files) ─────────────────────────────

def get_current_uid() -> str:
    uid = session.get("user", {}).get("uid")
    if not uid:
        raise ValueError("No authenticated user uid found in session")
    return uid


def auth_required(f):
    """Decorator — redirects to login if user is not in session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            logger.warning("Unauthenticated access attempt")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


# ── Routes ─────────────────────────────────────────────────────────────────────

@auth_bp.route("/auth", methods=["POST"])
def authorize():
    """Receives Firebase ID token from JS, verifies it, sets session."""
    token = request.headers.get("Authorization", "")
    if not token.startswith("Bearer "):
        logger.warning("Auth attempt with missing or malformed token")
        return "Unauthorized", 401
    try:
        decoded = auth.verify_id_token(token[7:], check_revoked=True, clock_skew_seconds=60)
        session["user"] = decoded
        logger.info(f"User authenticated uid={decoded.get('uid')}")
        return redirect(url_for("dashboard.dashboard"))
    except Exception as e:
        logger.warning(f"Token verification failed: {e}")
        return "Unauthorized", 401


@auth_bp.route("/")
@auth_bp.route("/login")
def login():
    if "user" in session:
        return redirect(url_for("dashboard.dashboard"))
    return render_template("login.html")


@auth_bp.route("/signup")
def signup():
    if "user" in session:
        return redirect(url_for("dashboard.dashboard"))
    return render_template("signup.html")


@auth_bp.route("/reset-password")
def reset_password():
    if "user" in session:
        return redirect(url_for("dashboard.dashboard"))
    return render_template("forgot_password.html")


@auth_bp.route("/instructions")
def instructions():
    return render_template("instructions.html")


@auth_bp.route("/logout")
def logout():
    uid = session.get("user", {}).get("uid", "unknown")
    session.pop("user", None)
    response = make_response(redirect(url_for("auth.login")))
    response.set_cookie("session", "", expires=0)
    logger.info(f"User logged out uid={uid}")
    return response
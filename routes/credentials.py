import requests
from flask import Blueprint, request, redirect, url_for, flash
from extensions import db, auth_required, get_current_uid, get_logger
from helpers.crypto import encrypt_string
from config import Config

logger = get_logger(__name__)
credentials_bp = Blueprint("credentials", __name__)

def test_login_credentials(username: str, password: str) -> tuple[bool, str]:
    """
    Attempts a real login against the club booking system.
    Returns (success: bool, message: str).
    """
    try:
        with requests.Session() as s:
            s.get(Config.CLUB_LOGIN_URL)
            resp = s.post(Config.CLUB_LOGIN_URL, data={
                "userId":   username,
                "password": password,
            })
            html = resp.text.lower()

            if "your email address or password is incorrect" in html:
                return False, "Invalid credentials"
            if "welcome" in html:
                return True, "Login successful"
            return False, "Could not determine login result"

    except requests.RequestException as e:
        logger.error(f"Network error testing credentials: {e}")
        return False, f"Network error: {e}"
    except Exception as e:
        logger.error(f"Unexpected error testing credentials: {e}")
        return False, f"Unexpected error: {e}"


@credentials_bp.route("/save-tennis-credentials", methods=["POST"])
@auth_required
def save_tennis_credentials():
    uid      = get_current_uid()
    username = request.form.get("tennis_username", "").strip()
    password = request.form.get("tennis_password", "").strip()

    if not username or not password:
        flash("Please enter both username and password.", "error")
        return redirect(url_for("dashboard.dashboard"))

    is_valid, message = test_login_credentials(username, password)

    if not is_valid:
        db.collection("users").document(uid).set({
            "tennis_username_encrypted": None,
            "tennis_password_encrypted": None,
            "club_profile_connected":    False,
        }, merge=True)
        flash(f"Tennis login failed: {message}", "error")
        logger.warning(f"Credential test failed uid={uid}: {message}")
        return redirect(url_for("dashboard.dashboard"))

    try:
        db.collection("users").document(uid).set({
            "tennis_username_encrypted": encrypt_string(username),
            "tennis_password_encrypted": encrypt_string(password),
            "club_profile_connected":    True,
        }, merge=True)
        flash("Tennis credentials saved.", "success")
        logger.info(f"Credentials saved uid={uid}")
    except Exception as e:
        logger.error(f"Failed to save credentials uid={uid}: {e}")
        flash("Failed to save credentials. Please try again.", "error")

    return redirect(url_for("dashboard.dashboard"))
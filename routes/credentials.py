import requests
from flask import Blueprint, request, redirect, url_for, flash
from extensions import db, auth_required, get_current_uid, get_logger
from helpers.crypto import encrypt_string, decrypt_string
from helpers.players import resolve_tennis_site_name
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
    
    # Detect if the password is just the UI mask (e.g. "*******")
    is_masked = all(c == '*' for c in password) and len(password) > 0

    if not username or not password:
        flash("Please enter both username and password.", "error")
        return redirect(url_for("dashboard.dashboard"))

    # If masked, fetch the real password from Firestore to perform the test login
    if is_masked:
        user_doc = db.collection("users").document(uid).get()
        existing_data = user_doc.to_dict() if user_doc.exists else {}
        encrypted_pw = existing_data.get("tennis_password_encrypted")
        
        if encrypted_pw:
            try:
                password = decrypt_string(encrypted_pw)
            except Exception as e:
                logger.error(f"Failed to decrypt existing password for test: {e}")
                flash("Session error. Please re-enter your password.", "error")
                return redirect(url_for("dashboard.dashboard"))

    is_valid, message = test_login_credentials(username, password)

    if not is_valid:
        # Update only the connection status. We keep the username strings 
        # so the user can see what they typed and fix typos.
        db.collection("users").document(uid).set({
            "club_profile_connected": False,
        }, merge=True)
        flash(f"Tennis login failed: {message}", "error")
        logger.warning(f"Credential test failed uid={uid}: {message}")
        return redirect(url_for("dashboard.dashboard"))

    try:
        update_data = {
            "tennis_username":           username,
            "club_profile_connected":    True,
        }

        # Only update the encrypted password if the user actually typed a new one
        if not is_masked:
            update_data["tennis_password_encrypted"] = encrypt_string(password)

        db.collection("users").document(uid).set(update_data, merge=True)
        flash("Tennis credentials saved.", "success")
        logger.info(f"Credentials saved uid={uid}")
    except Exception as e:
        logger.error(f"Failed to save credentials uid={uid}: {e}")
        flash("Failed to save credentials. Please try again.", "error")
        return redirect(url_for("dashboard.dashboard"))

    # Resolve tennis_site_name if not already set.
    # Reads the user doc to get full_name and current tennis_site_name.
    # Non-critical — a failure here doesn't block the credential save.
    try:
        user_doc = db.collection("users").document(uid).get()
        user_data = user_doc.to_dict() or {}
        if not user_data.get("tennis_site_name"):
            resolve_tennis_site_name(
                user_id=uid,
                email=user_data.get("email", ""),
                full_name=user_data.get("full_name", ""),
                tennis_username=username,
            )
    except Exception as e:
        logger.error(f"Failed to resolve tennis_site_name for {uid}: {e}")

    return redirect(url_for("dashboard.dashboard"))
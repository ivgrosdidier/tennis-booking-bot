from flask import Blueprint, render_template, request, redirect, url_for, flash
from extensions import db, auth_required, get_current_uid, get_logger

logger = get_logger(__name__)
dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard")
@auth_required
def dashboard():
    uid = get_current_uid()
    try:
        user_doc = db.collection("users").document(uid).get()
        data = user_doc.to_dict() if user_doc.exists else {}

        partners_docs = db.collection("users").document(uid).collection("partners").get()
        partners = [{"id": doc.id, **doc.to_dict()} for doc in partners_docs]

        logger.debug(f"Dashboard loaded uid={uid} partners={len(partners)}")
    except Exception as e:
        logger.error(f"Dashboard load failed uid={uid}: {e}")
        data, partners = {}, []

    return render_template(
        "dashboard.html",
        autobook_enabled          = data.get("autobook_enabled", False),
        club_profile_connected    = data.get("club_profile_connected", False),
        google_calendar_connected = data.get("google_calendar_connected", False),
        partners                  = partners,
    )


@dashboard_bp.route("/toggle-autobook", methods=["POST"])
@auth_required
def toggle_autobook():
    uid     = get_current_uid()
    enabled = "autobook_enabled" in request.form

    try:
        db.collection("users").document(uid).set(
            {"autobook_enabled": enabled}, merge=True
        )
        status = "enabled" if enabled else "disabled"
        flash(f"Auto-book is now {status}.", "success" if enabled else "error")
        logger.info(f"Autobook {status} uid={uid}")
    except Exception as e:
        logger.error(f"Autobook toggle failed uid={uid}: {e}")
        flash("Something went wrong. Please try again.", "error")

    return redirect(url_for("dashboard.dashboard"))
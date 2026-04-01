import random
import string
from flask import Blueprint, request, redirect, url_for, flash
from extensions import db
from helpers.players import check_name_in_club_directory, partners_ref, check_duplicate_name, check_duplicate_nick
from extensions import db, auth_required, get_current_uid, get_logger

logger = get_logger(__name__)
partners_bp = Blueprint("partners", __name__)

@partners_bp.route("/add-partner", methods=["POST"])
@auth_required
def add_partner():
    uid       = get_current_uid()
    full_name = request.form.get("full_name", "").strip().title()
    nickname  = request.form.get("nickname", "").strip().title()
 
    if not full_name or not nickname:
        flash("Please enter both a full name and a nickname.", "error")
        return redirect(url_for("dashboard.dashboard"))
 
    if not check_name_in_club_directory(full_name):
        flash(f'"{full_name}" not found in club directory. Please check the spelling.', "error")
        return redirect(url_for("dashboard.dashboard"))
 
    ref = partners_ref(uid)
 
    if check_duplicate_name(ref, full_name):
        flash(f'"{full_name}" already has a nickname. Edit the existing entry instead.', "error")
        return redirect(url_for("dashboard.dashboard"))
 
    if check_duplicate_nick(ref, nickname):
        flash("Nickname already exists. Choose a different one.", "error")
        return redirect(url_for("dashboard.dashboard"))
 
    try:
        ref.add({
            "partner_id": "".join(random.choices(string.ascii_uppercase + string.digits, k=3)),
            "full_name":  full_name,
            "nickname":   nickname,
        })
        flash("Partner added!", "success")
        logger.info(f"Partner added uid={uid} name='{full_name}'")
    except Exception as e:
        logger.error(f"Failed to add partner uid={uid}: {e}")
        flash("Failed to add partner. Please try again.", "error")
 
    return redirect(url_for("dashboard.dashboard"))
 
@partners_bp.route("/edit-partner/<partner_id>", methods=["POST"])
@auth_required
def edit_partner(partner_id):
    uid      = get_current_uid()
    new_name = request.form.get("full_name", "").strip().title()
    new_nick = request.form.get("nickname", "").strip().title()
 
    if not check_name_in_club_directory(new_name):
        flash(f'"{new_name}" not found in club directory. Please check the spelling.', "error")
        return redirect(url_for("dashboard.dashboard"))
 
    ref = partners_ref(uid)

    if check_duplicate_name(ref, new_name, exclude_id=partner_id):
        flash(f'"{new_name}" already has a nickname. Edit the existing entry instead.', "error")
        return redirect(url_for("dashboard.dashboard"))
 
    if check_duplicate_nick(ref, new_nick, exclude_id=partner_id):
        flash("Nickname already in use by another partner.", "error")
        return redirect(url_for("dashboard.dashboard"))
 
    try:
        ref.document(partner_id).update({"full_name": new_name, "nickname": new_nick})
        flash("Partner updated!", "success")
        logger.info(f"Partner updated uid={uid} partner_id={partner_id}")
    except Exception as e:
        logger.error(f"Failed to update partner uid={uid} partner_id={partner_id}: {e}")
        flash("Failed to update partner. Please try again.", "error")
 
    return redirect(url_for("dashboard.dashboard"))
 
 
@partners_bp.route("/delete-partner/<partner_id>", methods=["POST"])
@auth_required
def delete_partner(partner_id):
    uid = get_current_uid()
    try:
        partners_ref(uid).document(partner_id).delete()
        flash("Partner removed.", "success")
        logger.info(f"Partner deleted uid={uid} partner_id={partner_id}")
    except Exception as e:
        logger.error(f"Failed to delete partner uid={uid} partner_id={partner_id}: {e}")
        flash("Failed to remove partner. Please try again.", "error")
 
    return redirect(url_for("dashboard.dashboard"))
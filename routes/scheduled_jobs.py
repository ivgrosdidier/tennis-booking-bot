from flask import Blueprint, render_template, redirect, url_for, flash, session
from extensions import db, auth_required, get_current_uid, get_logger

logger = get_logger(__name__)
settings_bp = Blueprint("settings", __name__)

@settings_bp.route('/settings')
@auth_required
def settings():
    return render_template('settings.html')
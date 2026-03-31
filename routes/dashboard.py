from flask import Blueprint, render_template, session
from extensions import db
from routes.auth import auth_required, get_current_uid

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
@auth_required
def dashboard():
    uid = get_current_uid()
    
    # 1. Fetch User Document
    user_ref = db.collection('users').document(uid)
    user_doc = user_ref.get()
    data = user_doc.to_dict() if user_doc.exists else {}

    # 2. Extract UI Flags
    autobook_enabled = data.get('autobook_enabled', False)
    club_profile_connected = data.get('club_profile_connected', False)
    google_calendar_connected = data.get('google_calendar_connected', False)

    # 3. Fetch Partners Subcollection
    partners_docs = user_ref.collection('partners').get()
    partners = [{'id': doc.id, **doc.to_dict()} for doc in partners_docs]

    return render_template(
        'dashboard.html',
        autobook_enabled=autobook_enabled,
        club_profile_connected=club_profile_connected,
        google_calendar_connected=google_calendar_connected,
        partners=partners
    )
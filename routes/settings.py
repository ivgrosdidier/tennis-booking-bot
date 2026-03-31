from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from extensions import db
from routes.auth import auth_required, get_current_uid

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings')
@auth_required
def settings():
    return render_template('settings.html')

@settings_bp.route('/delete-account', methods=['POST'])
@auth_required
def delete_account():
    uid = get_current_uid()

    try:
        # Step 1 — Delete partners subcollection
        # Note: Firestore requires manual deletion of subcollections
        partners = db.collection('users').document(uid).collection('partners').get()
        for partner in partners:
            partner.reference.delete()

        # Step 2 — Delete the main user document
        db.collection('users').document(uid).delete()

        # Step 3 — Clear session and redirect to login
        session.clear()
        
        flash('Your account has been permanently deleted.', 'success')
        return redirect(url_for('auth.login')) # Pointing to the auth blueprint's login route

    except Exception as e:
        # Log this error using the logger we set up earlier!
        print(f"[Account Deletion Error] {e}") 
        flash('Something went wrong. Please try again.', 'error')
        return redirect(url_for('settings.settings'))
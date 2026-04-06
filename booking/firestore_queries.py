# database queries

from firebase_admin import firestore
from booking.models import BookingRequest
import logging
from helpers.crypto import decrypt_string
from google.cloud.firestore_v1.base_query import FieldFilter

logger = logging.getLogger(__name__)
db = firestore.client()

def get_eligible_users():
    """Fetch users with autobook enabled"""
    users = []
    
    query = db.collection('users').filter(
        filter=FieldFilter('autobook_enabled', '==', True)
    ).filter(
        filter=FieldFilter('club_profile_connected', '==', True)
    ).filter(
        filter=FieldFilter('google_calendar_connected', '==', True)
    )
    
    for doc in query.stream():
        data = doc.to_dict()
        user_id = doc.id

        try:
            # We use .get() to avoid KeyErrors if a field is missing
            tennis_pw_enc = data.get('tennis_password_encrypted')
            google_rt_enc = data.get('google_refresh_token_encrypted')
            
            if not tennis_pw_enc or not google_rt_enc:
                logger.warning(f"User {user_id} missing encrypted credentials. Skipping.")
                continue

            # get partners
            partners = {}
            partners_ref = db.collection('users').document(user_id).collection('partners')
            for p_doc in partners_ref.stream():
                partners[p_doc.id] = p_doc.to_dict()

            # construct clean data object
            user_packet = {
                "user_id": data.get('user_id'),
                "tennis_username": data.get('tennis_username'),
                "tennis_password": decrypt_string(tennis_pw_enc),
                "google_refresh_token": decrypt_string(google_rt_enc),
                "google_cal_id": data.get('google_calendar_id'),
                "google_cal_name": data.get('google_calendar_name'),
                "partners": partners,
                'email': data.get('email')
            }
            
            users.append(user_packet)

        except Exception as e:
            logger.error(f"Failed to process/decrypt data for user {user_id}: {e}")
            continue 

    return users

def find_player_by_email(email: str):
    """Find player name by email"""
    players = db.collection('players').filter(filter=FieldFilter('email', '==', email)).limit(1).stream()
    for doc in players:
        return doc.id
    return None

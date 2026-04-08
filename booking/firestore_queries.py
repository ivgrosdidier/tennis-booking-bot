# database queries

from extensions import db, get_logger
from helpers.crypto import decrypt_string
from helpers.players import resolve_tennis_site_name
from google.cloud.firestore_v1.base_query import FieldFilter

logger = get_logger(__name__)

def get_eligible_users():
    """Fetch users with autobook enabled"""
    users = []
    
    query = (db.collection('users')
               .where(filter=FieldFilter('autobook_enabled', '==', True))
               .where(filter=FieldFilter('club_profile_connected', '==', True))
               .where(filter=FieldFilter('google_calendar_connected', '==', True)))

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

            tennis_site_name = data.get('tennis_site_name')

            # Lazy backfill for existing users who don't have tennis_site_name yet.
            # Runs once, writes result to Firestore, never runs again for this user.
            if not tennis_site_name:
                try:
                    tennis_site_name = resolve_tennis_site_name(
                        user_id=user_id,
                        email=data.get('email', ''),
                        full_name=data.get('full_name', ''),
                        tennis_username=data.get('tennis_username', ''),
                    )
                except Exception as e:
                    logger.error(f"Could not resolve tennis_site_name for {user_id}: {e}")

            # construct clean data object
            user_packet = {
                "user_id": data.get('user_id'),
                'email': data.get('email'),
                "tennis_site_name": tennis_site_name,
                "tennis_username": data.get('tennis_username'),
                "tennis_password": decrypt_string(tennis_pw_enc),
                "google_refresh_token": decrypt_string(google_rt_enc),
                "google_cal_id": data.get('google_calendar_id'),
                "partners": partners
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

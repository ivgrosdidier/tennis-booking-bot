from firebase_admin import firestore

db = firestore.client()

def get_eligible_users():
    query = (db.collection('users')
               .where('autobook_enabled', '==', True)
               .where('setup_complete', '==', True))
    return [{'uid': doc.id, **doc.to_dict()} for doc in query.stream()]
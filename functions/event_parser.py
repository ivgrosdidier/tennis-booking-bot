from firebase_admin import firestore
from player_helpers import get_tptc_players

db = firestore.client()

def parse_event(event, user_uid):
    title      = event.get('summary', '').strip()
    event_time = event['start'].get('dateTime', event['start'].get('date'))
    lower      = title.lower()
    remainder  = title.split(' ', 1)[1].strip() if ' ' in title else ''

    if 'guest' in lower:
        guest_name = remainder.replace('Guest', '').replace('guest', '').strip()
        return {'type': 'singles', 'is_guest': True,
                'guest_name': guest_name, 'time': event_time, 'event_id': event['id']}

    if lower.startswith('doubles'):
        raw_names = [n.strip() for n in remainder.split(',')]
        resolved  = [resolve_partner_name(n, user_uid) for n in raw_names]
        return {'type': 'doubles', 'is_guest': False,
                'partners': resolved, 'time': event_time, 'event_id': event['id']}

    partner = resolve_partner_name(remainder, user_uid) if remainder else None
    return {'type': 'singles', 'is_guest': False,
            'partner_name': partner, 'time': event_time, 'event_id': event['id']}


def resolve_partner_name(name_or_nick, user_uid):
    players = get_tptc_players()
    titled  = name_or_nick.strip().title()

    if titled in players:
        return titled

    partners = (db.collection('users')
                  .document(user_uid)
                  .collection('partners')
                  .where('nickname', '==', titled)
                  .get())
    if partners:
        return partners[0].to_dict().get('full_name')

    return titled
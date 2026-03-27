from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import date, timedelta, datetime
import pytz
import os

CLIENT_ID     = os.environ.get('GOOGLE_CLIENT_ID')
CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')

def get_events_for_user(user):
    """Returns calendar events 6 days from today for a specific user."""
    token = decrypt_string(user['google_refresh_token_encrypted'])

    creds = Credentials(
        token=None,
        refresh_token=token,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token"
    )

    service = build('calendar', 'v3', credentials=creds)

    toronto = pytz.timezone('America/Toronto')
    target_date = date.today() + timedelta(days=6)
    start = toronto.localize(datetime.combine(target_date, datetime.min.time()))
    end   = toronto.localize(datetime.combine(target_date, datetime.max.time()))

    result = service.events().list(
        calendarId=user['google_calendar_id'],
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True
    ).execute()

    return result.get('items', [])

def parse_event(event, user_uid):
    """
    Returns dict: {type, partner_name, partner_email, is_guest, time}

    Handles formats:
      Singles
      Singles Jon
      Singles Jonathan Smith
      Singles Guest Sam H
      Doubles Jon, Jane, Bob
    """
    title = event.get('summary', '').strip()
    event_time = event['start'].get('dateTime', event['start'].get('date'))

    title_lower = title.lower()
    is_doubles = title_lower.startswith('doubles')
    is_singles = title_lower.startswith('singles')
    is_guest   = 'guest' in title_lower

    # Strip the Singles/Doubles prefix
    remainder = title.split(' ', 1)[1].strip() if ' ' in title else ''

    if is_guest:
        # "Singles Guest Sam H" → guest_name = "Sam H"
        guest_name = remainder.replace('Guest', '').replace('guest', '').strip()
        return {
            'type': 'singles',
            'is_guest': True,
            'guest_name': guest_name,
            'time': event_time,
            'event_id': event['id']
        }

    if is_doubles:
        # "Doubles Jon, Jane, Bob" → resolve each name
        raw_names = [n.strip() for n in remainder.split(',')]
        resolved = [resolve_partner_name(n, user_uid) for n in raw_names]
        return {
            'type': 'doubles',
            'is_guest': False,
            'partners': resolved,
            'time': event_time,
            'event_id': event['id']
        }

    # Singles with one partner name or nickname
    partner_full = resolve_partner_name(remainder, user_uid) if remainder else None
    return {
        'type': 'singles',
        'is_guest': False,
        'partner_name': partner_full,
        'time': event_time,
        'event_id': event['id']
    }


def resolve_partner_name(name_or_nick, user_uid):
    """
    Given a name or nickname, returns the full club-system name.
    Checks in order:
      1. Is it already a full name in the players dict?
      2. Is it a nickname in the user's partners subcollection?
      3. Check email map for matching email in event description (handled separately)
    """
    players = get_tptc_players()  # your existing cached dict {name: email}

    # Already a full name
    titled = name_or_nick.strip().title()
    if titled in players:
        return titled

    # Try nickname lookup in partners subcollection
    partners = (db.collection('users')
                  .document(user_uid)
                  .collection('partners')
                  .where('nickname', '==', titled)
                  .get())
    if partners:
        return partners[0].to_dict().get('full_name')

    # Return as-is — may be a guest or unrecognized name
    return titled



from playwright.sync_api import sync_playwright

def book_court(user, parsed_event):
    """
    Logs into club site and submits a court booking.
    Returns True if successful, False otherwise.
    """
    username = decrypt_string(user['club_username_encrypted'])
    password = decrypt_string(user['club_password_encrypted'])

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # --- LOGIN ---
            page.goto('https://clubbookingsite.com/login')
            page.fill('#username', username)
            page.fill('#password', password)
            page.click('#login-btn')
            page.wait_for_load_state('networkidle')

            # --- NAVIGATE TO BOOKING ---
            # These selectors will depend on your actual club site
            # You'll fill these in once you can inspect the live site
            page.goto('https://clubbookingsite.com/book')
            page.select_option('#date-picker', parsed_event['time'][:10])
            page.select_option('#time-picker', parsed_event['time'][11:16])

            # Fill partner name
            if parsed_event.get('partner_name'):
                page.fill('#partner-name', parsed_event['partner_name'])

            # Submit
            page.click('#submit-booking')
            page.wait_for_load_state('networkidle')

            # Check for success indicator on page
            success = page.query_selector('.booking-confirmed') is not None

            browser.close()
            return success

        except Exception as e:
            print(f"[Booking] Error for uid={user['uid']}: {e}")
            browser.close()
            return False



def mark_event_booked(user, event_id, original_title):
    """Updates the calendar event title to 'Booked: [original title]'."""
    token = decrypt_string(user['google_refresh_token_encrypted'])
    creds = Credentials(
        token=None,
        refresh_token=token,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token"
    )
    service = build('calendar', 'v3', credentials=creds)
    service.events().patch(
        calendarId=user['google_calendar_id'],
        eventId=event_id,
        body={'summary': f'Booked: {original_title}'}
    ).execute()



def _build_credentials(user):
    from crypto_helpers import decrypt_string
    return Credentials(
        token=None,
        refresh_token=decrypt_string(user['google_refresh_token_encrypted']),
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token"
    )


from concurrent.futures import ThreadPoolExecutor, as_completed

def run_all_bookings():
    users = get_eligible_users()
    print(f"[Scheduler] Processing {len(users)} eligible users")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_user, user): user for user in users}
        for future in as_completed(futures):
            user = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"[Error] uid={user['uid']}: {e}")


def process_user(user):
    events = get_events_for_user(user)
    for event in events:
        parsed = parse_event(event, user['uid'])
        success = book_court(user, parsed)
        if success:
            mark_event_booked(user, parsed['event_id'], event['summary'])
            print(f"[Booked] uid={user['uid']} event={event['summary']}")
        else:
            print(f"[Failed] uid={user['uid']} event={event['summary']}")


def try_acquire_booking_lock(date_str, time_str, court_type):
    """
    Returns True if this process acquired the lock (should proceed).
    Returns False if another user already claimed this slot.
    Uses Firestore transactions to prevent race conditions.
    """
    lock_id = f"{date_str}_{time_str}_{court_type}"
    lock_ref = db.collection('booking_locks').document(lock_id)

    @db.transaction()
    def claim_lock(transaction, lock_ref):
        snapshot = lock_ref.get(transaction=transaction)
        if snapshot.exists:
            return False  # already claimed
        transaction.set(lock_ref, {
            'claimed_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        })
        return True

    return claim_lock(lock_ref)


# In process_user:
def process_user(user):
    events = get_events_for_user(user)
    for event in events:
        parsed = parse_event(event, user['uid'])
        date_str = parsed['time'][:10]
        time_str = parsed['time'][11:16]

        if not try_acquire_booking_lock(date_str, time_str, parsed['type']):
            print(f"[Skip] Slot {date_str} {time_str} already claimed by another user")
            continue

        success = book_court(user, parsed)
        if success:
            mark_event_booked(user, parsed['event_id'], event['summary'])
"""
Integration test suite for the booking pipeline.

Runs against your real Firebase and Google Calendar — read-only, safe to run anytime.
The actual court booking step is intentionally excluded (would book real courts).

Usage:
    python tests/integration_test.py                  # test all users, 6 days from now
    python tests/integration_test.py --all-events     # fetch all upcoming events (no date filter)
    python tests/integration_test.py --date 2026-04-20  # specific date

Each section prints PASS / FAIL clearly so you can diagnose exactly where things break.
"""

import sys
import os
import argparse
from datetime import datetime, timedelta, date

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extensions import get_logger
from config import Config

logger = get_logger('integration_test')
DIVIDER = '=' * 60


def section(title):
    print(f'\n{DIVIDER}')
    print(f'  {title}')
    print(DIVIDER)


def ok(msg):   print(f'  [PASS] {msg}')
def fail(msg): print(f'  [FAIL] {msg}')
def info(msg): print(f'  [INFO] {msg}')


# ---------------------------------------------------------------------------
# Section 1 — Firestore: eligible users
# ---------------------------------------------------------------------------

def test_get_eligible_users():
    section('1. Firestore — get_eligible_users()')
    from booking.firestore_queries import get_eligible_users

    try:
        users = get_eligible_users()
        ok(f'get_eligible_users() returned {len(users)} user(s)')
    except Exception as e:
        fail(f'get_eligible_users() raised: {e}')
        return []

    if not users:
        info('No eligible users found (autobook_enabled=True + both connections set). '
             'Check your Firestore documents.')
        return []

    required_keys = [
        'user_id', 'email', 'tennis_username', 'tennis_password',
        'google_refresh_token', 'google_cal_id', 'partners'
    ]

    for user in users:
        uid = user.get('user_id', '?')
        missing = [k for k in required_keys if k not in user or not user[k]]
        if missing:
            fail(f'User {uid} missing fields: {missing}')
        else:
            ok(f'User {uid} ({user["email"]}) — all required fields present')

        if user.get('tennis_site_name'):
            ok(f'  tennis_site_name: {user["tennis_site_name"]}')
        else:
            info(f'  tennis_site_name not yet set for {uid} (will be resolved on first morning run)')

        info(f'  Calendar ID: {user["google_cal_id"]}')
        info(f'  Partners: {len(user.get("partners", {}))} stored')

    return users


# ---------------------------------------------------------------------------
# Section 2 — Google Calendar: fetch events
# ---------------------------------------------------------------------------

def test_calendar_events(users, target_date=None, all_events=False):
    section('2. Google Calendar — fetch events')
    from booking.calendar_parser import get_calendar_events, identify_opponent

    if not users:
        info('Skipping — no eligible users')
        return []

    if all_events:
        info('Mode: ALL upcoming events (no date filter)')
    elif target_date:
        info(f'Mode: events on {target_date} (6 days from now = booking window)')

    all_parsed = []

    for user in users:
        uid = user['user_id']
        info(f'\n  User: {uid} ({user["email"]})')

        if all_events:
            # Fetch all events in the next 30 days so you can see what's in the calendar
            raw_events = _get_all_upcoming_events(user)
        else:
            raw_events = get_calendar_events(user, target_date)

        if not raw_events:
            info(f'  No events found')
            continue

        ok(f'  Found {len(raw_events)} event(s)')

        for event in raw_events:
            summary = event.get('summary', '(no title)')
            start = event['start'].get('dateTime') or event['start'].get('date', '?')
            organizer = event.get('organizer', {}).get('email', '?')
            is_creator = (organizer == user['email'])

            # Try opponent identification
            try:
                opponent = identify_opponent(event, user)
            except Exception as e:
                opponent = f'ERROR: {e}'

            info(f'    Event : {summary}')
            info(f'    Start : {start}')
            info(f'    Creator: {"YES (this user)" if is_creator else f"NO ({organizer})"}')
            info(f'    Opponent identified as: {opponent}')

            if 'Booked' in summary:
                info(f'    (already marked Booked — would be skipped by pipeline)')

            all_parsed.append((user, event))

    return all_parsed


def _get_all_upcoming_events(user, days_ahead=30):
    """Fetch all events in the next `days_ahead` days — for testing visibility only."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=user['google_refresh_token'],
        client_id=Config.GOOGLE_CLIENT_ID,
        client_secret=Config.GOOGLE_CLIENT_SECRET,
        token_uri='https://oauth2.googleapis.com/token'
    )
    service = build('calendar', 'v3', credentials=creds)

    now = datetime.utcnow()
    start = now.isoformat() + 'Z'
    end = (now + timedelta(days=days_ahead)).isoformat() + 'Z'

    result = service.events().list(
        calendarId=user['google_cal_id'],
        timeMin=start,
        timeMax=end,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    return result.get('items', [])


# ---------------------------------------------------------------------------
# Section 3 — Calendar parser: parse_events()
# ---------------------------------------------------------------------------

def test_parse_events(users, target_date):
    section('3. Calendar Parser — parse_events()')
    from booking.calendar_parser import parse_events

    if not users:
        info('Skipping — no eligible users')
        return []

    try:
        requests = parse_events(users)
        ok(f'parse_events() returned {len(requests)} BookingRequest(s)')
    except Exception as e:
        fail(f'parse_events() raised: {e}')
        return []

    for req in requests:
        info(f'\n  BookingRequest:')
        info(f'    user_id    : {req.user_id}')
        info(f'    date       : {req.date}')
        info(f'    time       : {req.start_time} – {req.end_time} ({req.duration} min)')
        info(f'    opponent   : {req.opponent}')
        info(f'    match_type : {req.match_type}')
        info(f'    is_creator : {req.is_creator}')
        ok(f'  Credentials attached: {bool(req.tennis_username and req.tennis_password)}')

    return requests


# ---------------------------------------------------------------------------
# Section 4 — Court availability (read-only scrape, no booking)
# ---------------------------------------------------------------------------

def test_court_availability(target_date):
    section('4. Court Availability — check_court_availability()')
    from booking.check_court_availability import check_court_availability

    info(f'Checking availability for {target_date}')
    info('(Uses bot credentials from .env — TENNIS_USERNAME / TENNIS_PASSWORD)')

    try:
        available = check_court_availability(target_date)
    except Exception as e:
        fail(f'check_court_availability() raised: {e}')
        return {}

    if not available:
        info('No available slots returned. Could mean: courts are fully booked, '
             'login failed, or the date is outside season hours.')
        return {}

    ok(f'Found available slots at {len(available)} time(s):')
    for time, courts in sorted(available.items()):
        court_names = [c['court'] for c in courts]
        info(f'  {time}: {", ".join(court_names)}')

    return available


# ---------------------------------------------------------------------------
# Section 5 — Deduplication and court assignment (dry run)
# ---------------------------------------------------------------------------

def test_dedup_and_assign(requests, available):
    section('5. Dedup & Assignment — deduplicate_and_assign()')
    from booking.court_assignment import deduplicate_and_assign

    if not requests:
        info('Skipping — no booking requests')
        return []
    if not available:
        info('Skipping — no available courts')
        return []

    try:
        assigned = deduplicate_and_assign(requests, available)
        ok(f'deduplicate_and_assign() produced {len(assigned)} assignment(s)')
    except Exception as e:
        fail(f'deduplicate_and_assign() raised: {e}')
        return []

    for req in assigned:
        info(f'\n  Assignment:')
        info(f'    {req.user_id} vs {req.opponent}')
        info(f'    Requested: {req.start_time} | Times to try: {req.times_to_try}')
        info(f'    Pre-assigned court: {req.court}')
        info(f'    Booking href: {req.booking_href}')

    return assigned


# ---------------------------------------------------------------------------
# Section 6 — Firestore: players collection lookup
# ---------------------------------------------------------------------------

def test_player_lookup():
    section('6. Firestore — players collection')
    from helpers.players import get_club_players

    try:
        players = get_club_players()
        ok(f'Loaded {len(players)} players from {"JSON (dev)" if os.getenv("K_SERVICE") is None else "Firestore (cloud)"}')
        if players:
            sample = list(players.items())[:3]
            for name, email in sample:
                info(f'  {name}: {email}')
    except Exception as e:
        fail(f'get_club_players() raised: {e}')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--all-events', action='store_true',
                        help='Fetch all upcoming calendar events instead of just 6 days from now')
    parser.add_argument('--date', type=str, default=None,
                        help='Target date to test (YYYY-MM-DD). Default: today + 6 days.')
    args = parser.parse_args()

    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
    else:
        target_date = (datetime.now() + timedelta(days=6)).date()

    print(f'\nTesting booking pipeline — target date: {target_date}')
    print('Read-only. The actual booking step is intentionally excluded.\n')

    # Run each section in pipeline order
    users = test_get_eligible_users()
    test_player_lookup()
    test_calendar_events(users, target_date=target_date, all_events=args.all_events)
    requests = test_parse_events(users, target_date)
    available = test_court_availability(target_date)
    test_dedup_and_assign(requests, available)

    print(f'\n{DIVIDER}')
    print('  Done. Review [FAIL] lines above for issues.')
    print(DIVIDER)


if __name__ == '__main__':
    main()

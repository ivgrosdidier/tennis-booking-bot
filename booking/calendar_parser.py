# parse calendar events

from datetime import datetime, timedelta
from booking.models import BookingRequest
from booking.firestore_queries import find_player_by_email
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from config import Config
from extensions import get_logger
import re

logger = get_logger(__name__)


def get_calendar_events(user, target_date):
    """Fetch events for target_date using the user's stored refresh token."""
    try:
        creds = Credentials(
            token=None,
            refresh_token=user['google_refresh_token'],
            client_id=Config.GOOGLE_CLIENT_ID,
            client_secret=Config.GOOGLE_CLIENT_SECRET,
            token_uri="https://oauth2.googleapis.com/token"
        )
        service = build('calendar', 'v3', credentials=creds)

        start_of_day = datetime.combine(target_date, datetime.min.time()).isoformat() + 'Z'
        end_of_day = datetime.combine(target_date, datetime.max.time()).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId=user['google_cal_id'],
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        return events_result.get('items', [])

    except Exception as e:
        logger.error(f"Calendar fetch failed for user {user['user_id']}: {e}")
        return []


def identify_opponent(event, user):
    """
    Identify all opponents/partners in a calendar event.
    Returns a comma-separated string of player names.
    For doubles, this may include up to 3 names.

    Strategies (in order):
    0. Title contains 'GP' or 'Guest Player' + name
    1. Attendee email matches a player in the players collection
    2. Title or attendee matches a partner's nickname or full name
    3. Fallback: use the event title directly
    """
    found_opponents = []
    title_lower = event.get('summary', '').lower()
    partners = user.get('partners', {})

    # Strategy 0: Guest Player prefix in title
    guest_pattern = r'(?:gp|guest player)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)'
    for guest_name in re.findall(guest_pattern, title_lower):
        formatted = f"Guest Player {guest_name.strip().title()}"
        if formatted not in found_opponents:
            found_opponents.append(formatted)

    # Strategy 1: Attendee emails in the players collection
    for attendee in event.get('attendees', []):
        email = attendee.get('email', '')
        if email and email != user.get('email'):
            player_name = find_player_by_email(email)
            if player_name and player_name not in found_opponents:
                found_opponents.append(player_name)

    # Strategy 2: Partner nickname or full name appears in the title
    for partner_data in partners.values():
        db_nickname = (partner_data.get('nickname', '') or '').lower()
        db_full_name = (partner_data.get('full_name', '') or '').lower()

        if (db_nickname and db_nickname in title_lower) or \
           (db_full_name and db_full_name in title_lower):
            actual_name = partner_data.get('full_name')
            if actual_name and actual_name not in found_opponents:
                found_opponents.append(actual_name)

    if found_opponents:
        return ', '.join(found_opponents)

    # Strategy 3: Fallback — use cleaned event title
    return event.get('summary', '').strip()


def parse_events(users):
    """
    For each eligible user, fetch their Google Calendar events 6 days from now
    and return a list of BookingRequest objects.
    """
    requests = []
    target_dt = datetime.now() + timedelta(days=6)
    target_date_str = target_dt.strftime('%Y-%m-%d')

    for user in users:
        events = get_calendar_events(user, target_dt.date())

        for event in events:
            # Skip events that are already booked
            if 'Booked' in event.get('summary', ''):
                continue

            try:
                start_str = event['start'].get('dateTime', '')
                end_str = event['end'].get('dateTime', '')
                start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                duration_mins = int((end_dt - start_dt).total_seconds() / 60)
                event_date = start_dt.strftime('%Y-%m-%d')
                event_time = start_dt.strftime('%H:%M')   # 24h format
                end_time = end_dt.strftime('%H:%M')
            except Exception as e:
                logger.error(f"Time parsing error on event '{event.get('summary')}': {e}")
                continue

            if event_date != target_date_str:
                continue

            opponent_str = identify_opponent(event, user)
            if not opponent_str:
                logger.warning(f"No opponent found for event '{event.get('summary')}', skipping.")
                continue

            match_type = 'doubles' if ',' in opponent_str else 'singles'

            req = BookingRequest(
                user_id=user['user_id'],
                event_id=event.get('id'),
                date=event_date,
                start_time=event_time,
                end_time=end_time,
                duration=duration_mins,
                opponent=opponent_str,
                match_type=match_type
            )

            # Attach user credentials so booking workers are self-contained
            req.user_email = user['email']
            req.tennis_site_name = user.get('tennis_site_name') or user['user_id']
            req.tennis_username = user['tennis_username']
            req.tennis_password = user['tennis_password']
            req.google_cal_id = user['google_cal_id']
            req.google_refresh_token = user['google_refresh_token']

            # is_creator: True if this user created the event (not just an invitee)
            req.is_creator = (
                event.get('organizer', {}).get('email') == user.get('email')
            )

            requests.append(req)
            logger.info(f"Found event: {user['user_id']} vs {opponent_str} at {event_time} on {event_date}")

    return requests

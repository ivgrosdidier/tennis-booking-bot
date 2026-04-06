# parse calendar events

from datetime import datetime, timedelta
from booking.models import BookingRequest
from booking.firestore_queries import find_player_by_email, get_user_partners
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from config import Config
import logging
import re

logger = logging.getLogger(__name__)

def get_calendar_events(user, target_date):
    """Fetch events using existing Config and Refresh Token"""
    try:
        # 1. Leverage your existing Config for credentials
        creds = Credentials(
            token=None,  # Access token is fetched automatically
            refresh_token=user['google_refresh_token'],
            client_id=Config.GOOGLE_CLIENT_ID,
            client_secret=Config.GOOGLE_CLIENT_SECRET,
            token_uri="https://oauth2.googleapis.com/token"
        )

        service = build('calendar', 'v3', credentials=creds)

        # 2. Setup the timeframe for the target date
        # Note: .isoformat() + 'Z' works for UTC; adjust if using Toronto local time
        start_of_day = datetime.combine(target_date, datetime.min.time()).isoformat() + 'Z'
        end_of_day = datetime.combine(target_date, datetime.max.time()).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId=user['google_cal_id'],
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        # returns list of google cal event resources (dicts)
        return events_result.get('items', [])

    except Exception as e:
        logger.error(f"Calendar fetch failed for user {user['user_id']}: {e}")
        return []


def identify_opponent(event, user):
    """Identify all opponents, handling 'GP' or 'Guest Player' specifically"""
    found_opponents = []
    # Lowercase for searching, but keep a copy for case-sensitive extraction if needed
    title_lower = event.get('summary', '').lower()
    partners = user.get('partners', {})
    
    # --- Strategy 0: Check for Guest Players (GP / Guest Player) ---
    # This regex looks for 'gp' or 'guest player' followed by a name
    # It captures the name that follows until a comma or the end of the string
    guest_pattern = r'(?:gp|guest player)\s+([a-zA-Z]+)'
    guest_matches = re.findall(guest_pattern, title_lower)
    
    for guest_name in guest_matches:
        formatted_guest = f"Guest Player {guest_name.strip().title()}"
        if formatted_guest not in found_opponents:
            found_opponents.append(formatted_guest)

    # --- Strategy 1: Check ALL guest emails (Skip if already found as GP) ---
    attendees = event.get('attendees', [])
    for attendee in attendees:
        email = attendee.get('email', '')
        if email and email != user.get('email'):
            player_name = find_player_by_email(email)
            if player_name and player_name not in found_opponents:
                found_opponents.append(player_name)

    # --- Strategy 2 & 3: Check Database Partners ---
    # We only check partners if they haven't been identified as a Guest already
    for partner_id, partner_data in partners.items():
        db_nickname = (partner_data.get('nickname', '') or "").lower()
        db_full_name = (partner_data.get('full_name', '') or "").lower()
        
        if (db_nickname and db_nickname in title_lower) or \
           (db_full_name and db_full_name in title_lower):
            actual_name = partner_data.get('full_name')
            if actual_name not in found_opponents:
                found_opponents.append(actual_name)

    # --- Final Logic ---
    if found_opponents:
        return ", ".join(found_opponents)

    # Strategy 4: Fallback (Cleaned Title)
    # Remove common prefix words to get a clean name
    clean_title = title_lower.strip().title()
    return clean_title


def parse_events(users):
    requests = []
    # Target is 6 days from now for the booking window
    target_dt = datetime.now() + timedelta(days=6)
    target_date_str = target_dt.strftime('%Y-%m-%d')
    
    for user in users:
        events = get_calendar_events(user, target_dt.date())
        
        for event in events:
            if 'Booked' in event.get('summary', ''):
                continue
            
            try:
                # 1. Parse Start and End
                start_str = event.get('start', {}).get('dateTime', '')
                end_str = event.get('end', {}).get('dateTime', '')
                
                start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                
                # 2. Calculate Duration in minutes
                duration_mins = int((end_dt - start_dt).total_seconds() / 60)
                
                event_date = start_dt.strftime('%Y-%m-%d')
                event_time = start_dt.strftime('%H:%M')
                end_time = end_dt.strftime('%H:%M')
            except Exception as e:
                logger.error(f"Time parsing error: {e}")
                continue
            
            if event_date != target_date_str:
                continue
            
            # 3. Identify Opponents (supports multiple names)
            opponent_str = identify_opponent(event, user)
            if not opponent_str:
                continue

            # 4. Determine Match Type
            # If there's a comma in the string, it's more than 1 person = Doubles
            match_type = "doubles" if "," in opponent_str else "singles"
            
            # 5. Create Request with new fields
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
            req.is_creator = (event.get('organizer', {}).get('email') == user.get('email'))
            
            requests.append(req)
    
    return requests
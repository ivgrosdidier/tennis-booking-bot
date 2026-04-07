# Update Google Calendar events after booking

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from config import Config
from extensions import get_logger

logger = get_logger(__name__)


def _update_event_title(request, court):
    """
    Prepend '[Booked - Court X]' to the Google Calendar event title.
    Uses the user's stored refresh token (no session needed).
    """
    try:
        creds = Credentials(
            token=None,
            refresh_token=request.google_refresh_token,
            client_id=Config.GOOGLE_CLIENT_ID,
            client_secret=Config.GOOGLE_CLIENT_SECRET,
            token_uri="https://oauth2.googleapis.com/token"
        )
        service = build('calendar', 'v3', credentials=creds)

        # Fetch current event so we preserve all existing fields
        event = service.events().get(
            calendarId=request.google_cal_id,
            eventId=request.event_id
        ).execute()

        old_title = event.get('summary', '')
        event['summary'] = f"[Booked - {court}] {old_title}"

        service.events().update(
            calendarId=request.google_cal_id,
            eventId=request.event_id,
            body=event
        ).execute()

        logger.info(f"Calendar updated for event {request.event_id} → {event['summary']}")

    except Exception as e:
        logger.error(f"Failed to update calendar event {request.event_id}: {e}")


def update_calendar(assigned, results):
    """
    For each successfully booked request, update its Google Calendar event title.
    Failed bookings are left unchanged.
    """
    for req in assigned:
        result = results.get(req.event_id)
        if result and result.success:
            _update_event_title(req, result.court)

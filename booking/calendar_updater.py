# Update Google Calendar events after booking

from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from config import Config
from extensions import get_logger

logger = get_logger(__name__)


def _build_creds(request):
    return Credentials(
        token=None,
        refresh_token=request.google_refresh_token,
        client_id=Config.GOOGLE_CLIENT_ID,
        client_secret=Config.GOOGLE_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token"
    )


def _update_event(request, result):
    """
    Update the Google Calendar event after a successful booking:
      - Prepend '[Booked - Court X]' to the title
      - If a fallback time was used (booked_time ≠ requested start_time),
        shift the event's start and end times to match what was actually booked.
    """
    try:
        service = build('calendar', 'v3', credentials=_build_creds(request))

        event = service.events().get(
            calendarId=request.google_cal_id,
            eventId=request.event_id
        ).execute()

        old_title = event.get('summary', '')
        event['summary'] = f"[Booked - {result.court}] {old_title}"

        # If the booking landed on a different time than requested, shift the event.
        booked_time = result.booked_time  # 'HH:MM' (24h)
        if booked_time and booked_time != request.start_time:
            original_start_str = event['start'].get('dateTime')
            original_end_str = event['end'].get('dateTime')

            if original_start_str and original_end_str:
                original_start = datetime.fromisoformat(original_start_str)
                original_end = datetime.fromisoformat(original_end_str)
                duration = original_end - original_start

                # Build the new start datetime by swapping in the booked time
                booked_dt = datetime.strptime(booked_time, '%H:%M')
                new_start = original_start.replace(
                    hour=booked_dt.hour, minute=booked_dt.minute, second=0, microsecond=0
                )
                new_end = new_start + duration

                event['start']['dateTime'] = new_start.isoformat()
                event['end']['dateTime'] = new_end.isoformat()

                logger.info(
                    f"Event time shifted: {request.start_time} → {booked_time} "
                    f"for event {request.event_id}"
                )

        service.events().update(
            calendarId=request.google_cal_id,
            eventId=request.event_id,
            body=event
        ).execute()

        logger.info(f"Calendar updated: '{event['summary']}' for event {request.event_id}")

    except Exception as e:
        logger.error(f"Failed to update calendar event {request.event_id}: {e}")


def update_calendar(assigned, results):
    """
    For each successfully booked request, update its Google Calendar event.
    Failed bookings are left unchanged.
    """
    for req in assigned:
        result = results.get(req.event_id)
        if result and result.success:
            _update_event(req, result)

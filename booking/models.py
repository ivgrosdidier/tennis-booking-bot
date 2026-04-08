# contains booking request class

"""Data structures for booking system"""

class BookingRequest:
    """
    A tennis booking request — one per calendar event to book.

    The 'opponent' field is a comma-separated string of player names.
    For singles: "Alice Smith"
    For doubles: "Alice Smith, Bob Jones, Carol Lee"  (up to 3 opponents)
    The match_type ('singles' or 'doubles') is derived from how many names are in the string.
    """
    def __init__(self, user_id, event_id, date, start_time, end_time, duration, opponent, match_type):
        # Who is booking
        self.user_id = user_id
        self.user_email = None          # set by parse_events
        self.tennis_site_name = None    # set by parse_events — name as it appears on the club site
        self.tennis_username = None     # set by parse_events
        self.tennis_password = None     # set by parse_events
        self.google_cal_id = None       # set by parse_events (for calendar update)
        self.google_refresh_token = None  # set by parse_events

        # What to book
        self.event_id = event_id        # Google Calendar event ID
        self.date = date                # YYYY-MM-DD
        self.start_time = start_time    # HH:MM (24h)
        self.end_time = end_time        # HH:MM (24h)
        self.duration = duration        # minutes
        self.opponent = opponent        # comma-separated string, e.g. "Alice, Bob, Carol"
        self.match_type = match_type    # 'singles' or 'doubles'

        # Set during deduplication / assignment
        self.is_creator = False
        self.court = None               # e.g. 'Court 1' — pre-assigned, may change at runtime
        self.booking_href = None        # URL for the pre-assigned court
        # Ordered list of times to attempt: [original, 1hr before, 1hr after, 2hrs after]
        # Only times that actually have courts available. Set during assignment.
        self.times_to_try = []


class BookingResult:
    """Result of a booking attempt."""
    def __init__(self, event_id, success, court=None, booked_time=None, error=None):
        self.event_id = event_id
        self.success = success
        self.court = court
        # The time actually booked — may differ from the requested time if a
        # fallback slot was used. Used by calendar_updater to fix the event time.
        self.booked_time = booked_time
        self.error = error

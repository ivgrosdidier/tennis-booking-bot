"""Main orchestrator — runs the full booking pipeline."""

import time
from datetime import datetime, timedelta

from booking.firestore_queries import get_eligible_users
from booking.calendar_parser import parse_events
from booking.check_court_availability import check_court_availability
from booking.court_assignment import deduplicate_and_assign
from booking.court_booker import book_courts
from booking.calendar_updater import update_calendar
from extensions import get_logger

logger = get_logger(__name__)

# Book at this time (HH:MM, 24h). Cloud Scheduler triggers at 7:50 to give
# phases 1-3 time to complete, then we sleep until this moment.
BOOKING_TIME = (7, 58)  # 7:58 AM — 2 minutes before the booking window opens


def _wait_until_booking_time():
    """Sleep until BOOKING_TIME. If we're already past it, proceed immediately."""
    now = datetime.now()
    target = now.replace(hour=BOOKING_TIME[0], minute=BOOKING_TIME[1], second=0, microsecond=0)
    wait_secs = (target - now).total_seconds()
    if wait_secs > 0:
        logger.info(f"Phases 1-3 complete. Waiting {wait_secs:.0f}s until {BOOKING_TIME[0]}:{BOOKING_TIME[1]:02d}...")
        time.sleep(wait_secs)
    else:
        logger.info("Already past booking time — proceeding immediately.")


def run_booking_process():
    """
    Execute the complete booking pipeline:
      Phase 1 — Fetch eligible users from Firestore
      Phase 2 — Parse each user's Google Calendar (6 days from now)
      Phase 3 — Check court availability, deduplicate, assign courts
      ⏳  Sleep until BOOKING_TIME
      Phase 4 — Book courts in parallel (one thread per booking)
      Phase 5 — Update Google Calendar events with booking confirmation
    """
    stats = {
        'started_at': datetime.now().isoformat(),
        'users_processed': 0,
        'events_found': 0,
        'bookings_assigned': 0,
        'bookings_successful': 0,
        'errors': []
    }

    try:
        logger.info("=" * 60)
        logger.info("STARTING MORNING BOOKING PROCESS")
        logger.info("=" * 60)

        target_date = (datetime.now() + timedelta(days=6)).date()

        # --- Phase 1: Eligible users ---
        logger.info("[PHASE 1] Fetching eligible users from Firestore...")
        users = get_eligible_users()
        stats['users_processed'] = len(users)
        if not users:
            logger.warning("No eligible users found. Exiting.")
            return stats

        # --- Phase 2: Parse calendar events ---
        logger.info("[PHASE 2] Parsing calendar events...")
        booking_requests = parse_events(users)
        stats['events_found'] = len(booking_requests)
        if not booking_requests:
            logger.warning("No booking requests found. Exiting.")
            return stats

        # --- Phase 3: Court availability + assignment ---
        logger.info("[PHASE 3] Checking court availability...")
        available_by_time = check_court_availability(target_date)
        if not available_by_time:
            logger.warning("No courts available. Exiting.")
            return stats

        logger.info("[PHASE 3] Deduplicating and assigning courts...")
        assigned = deduplicate_and_assign(booking_requests, available_by_time)
        stats['bookings_assigned'] = len(assigned)
        if not assigned:
            logger.warning("No bookings could be assigned. Exiting.")
            return stats

        # --- Wait until booking window ---
        _wait_until_booking_time()

        # --- Phase 4: Book courts in parallel ---
        logger.info("[PHASE 4] Booking courts...")
        results = book_courts(assigned, available_by_time)
        stats['bookings_successful'] = sum(1 for r in results.values() if r.success)

        # --- Phase 5: Update calendars ---
        logger.info("[PHASE 5] Updating calendar events...")
        update_calendar(assigned, results)

        logger.info("=" * 60)
        logger.info(
            f"DONE — {stats['bookings_successful']}/{stats['bookings_assigned']} booked "
            f"for {stats['users_processed']} users"
        )
        logger.info("=" * 60)

        stats['completed_at'] = datetime.now().isoformat()
        return stats

    except Exception as e:
        logger.error(f"CRITICAL ERROR in booking process: {e}", exc_info=True)
        stats['errors'].append(str(e))
        return stats

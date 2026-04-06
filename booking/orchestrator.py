"""Main orchestrator for booking process"""

from datetime import datetime, timedelta
from booking.firestore_queries import get_eligible_users
from booking.calendar_parser import parse_events
from booking.court_assignment import deduplicate_and_assign
from booking.court_booker import get_available_courts, book_courts
from booking.calendar_updater import update_calendar
import logging

logger = logging.getLogger(__name__)

def run_booking_process():
    """Execute the complete booking process"""
    
    stats = {
        'started_at': datetime.now().isoformat(),
        'users_processed': 0,
        'events_found': 0,
        'bookings_assigned': 0,
        'bookings_successful': 0,
        'errors': []
    }
    
    try:
        logger.info("=" * 70)
        logger.info("STARTING MORNING BOOKING PROCESS")
        logger.info("=" * 70)
        
        # Phase 1
        logger.info("\n[PHASE 1] Fetching eligible users...")
        users = get_eligible_users()
        stats['users_processed'] = len(users)
        
        if not users:
            logger.warning("No eligible users")
            return stats
        
        # Phase 2
        logger.info("\n[PHASE 2] Parsing calendar events...")
        booking_requests = parse_events(users)
        stats['events_found'] = len(booking_requests)
        
        if not booking_requests:
            logger.warning("No booking requests")
            return stats
        
        # Phase 3
        logger.info("\n[PHASE 3] Deduplicating and assigning courts...")
        target_date = (datetime.now() + timedelta(days=6)).strftime('%Y-%m-%d')
        available_courts = get_available_courts(target_date)
        assigned = deduplicate_and_assign(booking_requests, available_courts)
        stats['bookings_assigned'] = len(assigned)
        
        if not assigned:
            logger.warning("No courts available")
            return stats
        
        # Phase 4
        logger.info("\n[PHASE 4] Booking courts...")
        results = book_courts(assigned)
        successful = sum(1 for r in results.values() if r.get('success'))
        stats['bookings_successful'] = successful
        
        # Phase 5
        logger.info("\n[PHASE 5] Updating calendar...")
        update_calendar(assigned, results)
        
        logger.info("\n" + "=" * 70)
        logger.info("BOOKING PROCESS COMPLETED")
        logger.info("=" * 70)
        
        stats['completed_at'] = datetime.now().isoformat()
        return stats
    
    except Exception as e:
        logger.error(f"CRITICAL ERROR: {e}", exc_info=True)
        stats['errors'].append(str(e))
        return stats
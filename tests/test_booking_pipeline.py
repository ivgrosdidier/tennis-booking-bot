"""
Quick sanity check for the two most foundational functions.
For the full pipeline test, use integration_test.py instead.

Usage:
    python tests/test_booking_pipeline.py
"""

import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extensions import get_logger
from booking.firestore_queries import get_eligible_users
from booking.calendar_parser import get_calendar_events

logger = get_logger('test_booking_pipeline')


def run():
    target_date = date.today() + timedelta(days=6)
    logger.info(f"Checking booking date: {target_date}")

    try:
        users = get_eligible_users()
        logger.info(f"Found {len(users)} eligible user(s)")
    except Exception as e:
        logger.error(f"get_eligible_users() failed: {e}")
        return

    for user in users:
        uid = user['user_id']
        logger.info(f"User {uid} | calendar: {user['google_cal_id']} | partners: {len(user.get('partners', {}))}")

        events = get_calendar_events(user, target_date)
        if not events:
            logger.info(f"  No events on {target_date}")
        else:
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                logger.info(f"  Event: {event.get('summary', '(no title)')} at {start}")


if __name__ == '__main__':
    run()

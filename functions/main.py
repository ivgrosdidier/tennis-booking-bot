from firebase_functions import scheduler_fn
from firebase_functions.options import Timezone
from datetime import date
from user_helpers import get_eligible_users
from calendar_helpers import get_events_for_user
from event_parser import parse_event
from booking import book_court
from calendar_helpers import mark_event_booked
from concurrent.futures import ThreadPoolExecutor, as_completed

SEASON_START = (8, 11)   # August 11  ← change these easily
SEASON_END   = (11, 1)   # November 1

@scheduler_fn.on_schedule(
    schedule="59 7 * * *",
    timezone=Timezone("America/Toronto"),
    memory=1024,
    timeout_sec=540
)
def daily_booking_runner(event):
    today = date.today()
    start = date(today.year, *SEASON_START)
    end   = date(today.year, *SEASON_END)

    if not (start <= today <= end):
        print(f"[Scheduler] Outside season, skipping.")
        return

    run_all_bookings()


def run_all_bookings():
    users = get_eligible_users()
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
import os
from datetime import date, timedelta
import logging

# Import your existing logic
from config import Config
from booking.firestore_queries import get_eligible_users
from booking.calendar_parser import get_calendar_events # Assuming you saved the function there

# Setup basic logging to see the process in the terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_integration_test():
    """
    1. Pulls all eligible users from Firestore.
    2. Decrypts tokens and passwords.
    3. Fetches Google Calendar events for the target booking date.
    """
    # Define the date we want to check (e.g., booking for 2 days from now)
    target_date = date.today() + timedelta(days=2)
    print(f"--- Starting Test for Booking Date: {target_date} ---")

    # Step 1: Get users (this handles decryption and subcollections internally)
    try:
        eligible_users = get_eligible_users()
        print(f"Found {len(eligible_users)} eligible users in Firestore.\n")
    except Exception as e:
        print(f"CRITICAL: Failed to fetch users from Firestore: {e}")
        return

    # Step 2: Loop through each user and check their calendar
    for user in eligible_users:
        print(f"Checking User: {user['user_id']} ({user.get('tennis_username', 'No Username')})")
        print(f"Target Calendar ID: {user['google_cal_id']}")

        # Step 3: Call the Calendar API using the user's decrypted refresh token
        events = get_calendar_events(user, target_date)

        if not events:
            print(f"  [!] No events found for {user['user_id']} on {target_date}.")
        else:
            print(f"  [✓] Found {len(events)} events:")
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                summary = event.get('summary', 'No Title')
                print(f"      - {summary} starting at {start}")
        
        # Check if partners were pulled correctly
        partner_count = len(user.get('partners', {}))
        print(f"  [i] Partners synced: {partner_count}")
        print("-" * 40)

if __name__ == "__main__":
    # Ensure your environment variables are set before running
    # (e.g., GOOGLE_APPLICATION_CREDENTIALS, FERNET_KEY, etc.)
    run_integration_test()
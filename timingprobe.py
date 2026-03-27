# timing_probe.py — run this once manually, not as a Cloud Function
import requests
import time
from datetime import datetime
import pytz

TORONTO = pytz.timezone('America/Toronto')
TARGET_HOUR = 8   # bookings open at 8 AM
PROBE_DATE  = '2026-08-17'  # a real date to test with
PROBE_TIME  = '10:00'       # a real time slot to try

results = []

def probe_booking_attempt(username, password, attempt_num):
    """Tries to submit a booking and records the result and timestamp."""
    now = datetime.now(TORONTO)
    timestamp = now.strftime('%H:%M:%S.%f')

    try:
        # Replace with your actual booking endpoint and payload
        # once you've inspected the live site
        response = requests.post(
            'https://clubbookingsite.com/api/book',
            json={
                'date': PROBE_DATE,
                'time': PROBE_TIME,
                'username': username,
                'password': password
            },
            timeout=10
        )
        status = response.status_code
        body_snippet = response.text[:200]
    except Exception as e:
        status = 'ERROR'
        body_snippet = str(e)

    result = {
        'attempt': attempt_num,
        'timestamp': timestamp,
        'status': status,
        'response': body_snippet
    }
    results.append(result)
    print(f"Attempt {attempt_num} at {timestamp} → {status}")
    return result


def wait_until_near_8am():
    """Waits until 7:59:50 AM Toronto time."""
    while True:
        now = datetime.now(TORONTO)
        if now.hour == 7 and now.minute == 59 and now.second >= 50:
            break
        time.sleep(0.1)


if __name__ == '__main__':
    username = input("Club username: ")
    password = input("Club password: ")

    print("Waiting until 7:59:50 AM Toronto time...")
    wait_until_near_8am()
    print("Starting probe...")

    # Fire 20 attempts across the 8:00:00 window, 100ms apart
    for i in range(20):
        probe_booking_attempt(username, password, i + 1)
        time.sleep(0.1)  # 100ms between attempts

    print("\n=== Results ===")
    for r in results:
        print(f"  {r['attempt']:2d} | {r['timestamp']} | {r['status']} | {r['response'][:80]}")

    # Find first success
    successes = [r for r in results if str(r['status']).startswith('2')]
    if successes:
        print(f"\nFirst success at: {successes[0]['timestamp']}")
    else:
        print("\nNo successful attempts — check selectors/endpoint")
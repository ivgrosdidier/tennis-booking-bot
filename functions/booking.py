import requests
from datetime import datetime
import os
from crypto_helpers import decrypt_string
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def book_court(user, parsed_event):
    username = decrypt_string(user['club_username_encrypted'])
    password = decrypt_string(user['club_password_encrypted'])

    # Fetch URLs from environment
    login_url = os.getenv('CLUB_LOGIN_URL')
    calendar_template = os.getenv('CALENDAR_URL_TEMPLATE')

    # Parse the event time (assuming format 'YYYY-MM-DDTHH:MM:SS')
    event_dt = datetime.fromisoformat(parsed_event['time'])
    
    # Format the calendar URL
    # Note: Month is event_dt.month - 1 to satisfy the 0-indexed requirement
    calendar_url = calendar_template.format(
        year=event_dt.year,
        month=event_dt.month - 1, 
        day=event_dt.day
    )

    s = requests.Session()

    # Login
    s.post(login_url, data={
        'username': username,
        'password': password
    })

    # Optional: You might need to GET the calendar_url first 
    # if the site requires a session cookie from that specific page.
    # s.get(calendar_url)

    # Submit booking
    # Note: Using 'https://www.tptc.ca/tptc/home/booking.do' 
    # Consider moving this to .env as well if it changes!
    response = s.post(
        'https://www.tptc.ca/tptc/home/booking.do',
        data={
            'date':         parsed_event['time'][:10],
            'time':         parsed_event['time'][11:16],
            'partner_name': parsed_event.get('partner_name', ''),
        }
    )

    return 'confirmed' in response.text.lower()
import requests
import os
from crypto_helpers import decrypt_string

def book_court(user, parsed_event):
    username = decrypt_string(user['club_username_encrypted'])
    password = decrypt_string(user['club_password_encrypted'])

    s = requests.Session()

    # Login
    s.post('https://www.tptc.ca/tptc/home/login.do', data={
        'username': username,
        'password': password
    })

    # Submit booking
    # ← field names TBD once you inspect the live form
    response = s.post(
        'https://www.tptc.ca/tptc/home/booking.do',
        data={
            'date':         parsed_event['time'][:10],
            'time':         parsed_event['time'][11:16],
            'partner_name': parsed_event.get('partner_name', ''),
        }
    )

    return 'confirmed' in response.text.lower()
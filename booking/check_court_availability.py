import os
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from dotenv import load_dotenv
from config import Config
import logging 

logger = logging.getLogger(__name__)

def check_court_availability(target_date):
    """
    Main trigger function to log in and find open slots 
    for a specific date (e.g. 6 days from now).
    """
    session = make_session()
    
    try:
        print(f"--- 🎾 Starting Availability Check for {target_date} ---")
        
        # 1. Login
        login(session, Config.TENNIS_USER, Config.TENNIS_PASS)
        print("Log-in successful.")

        # 2. Prep Date Parameters
        # TPTC months are usually 0-indexed in the URL (Jan=0)
        year = target_date.year
        month_idx = target_date.month - 1 
        day = target_date.day
        date_str = target_date.strftime('%Y-%m-%d')

        # 3. Get the Soup
        soup, _ = get_calendar_soup(session, year, month_idx, day)

        # 4. Extract Data
        df = extract_calendar_table(soup, date_str)
        
        if df.empty:
            print("No calendar data found for this date.")
            return []

        # 5. Filter for Available Courts
        # Logic: Availability is usually a specific bgcolor OR missing 'booking_text'
        # We also filter out 'None' times
        available = df[
            (df['time'].notna()) & 
            (df['booking_text'].isna() | (df['booking_text'] == ""))
        ].copy()

        # Clean up the output
        available_slots = available[['time', 'court', 'href']].to_dict('records')
        
        print(f"Found {len(available_slots)} available slots.")
        for slot in available_slots:
            print(f"  ✅ {slot['time']} - {slot['court']}")

        return available_slots

    except Exception as e:
        print(f"❌ Availability Check Failed: {e}")
        return []
    finally:
        session.close()

# Example trigger (to be called by your main morning script)
if __name__ == "__main__":
    # Check for the booking window (usually today + 6 days)
    booking_date = datetime.now() + timedelta(days=6)
    available_list = check_court_availability(booking_date)
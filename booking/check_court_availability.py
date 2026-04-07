# Club website scraping — login, fetch calendar, extract available courts

import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import Config
from extensions import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def make_session():
    """Create a requests.Session with automatic retries on transient errors."""
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


def login_club(session, username, password):
    """
    Log into the club website using CLUB_LOGIN_URL from .env.
    Raises an exception if login fails.
    """
    resp = session.post(
        Config.CLUB_LOGIN_URL,
        data={'userId': username, 'password': password},
        allow_redirects=True
    )
    resp.raise_for_status()

    # Detect login failure — adjust these checks based on the actual response
    if 'invalid' in resp.text.lower() or 'login' in resp.url.lower():
        raise ValueError(f"Club login failed for user '{username}'")

    logger.info(f"Club login successful for '{username}'")


def get_calendar_soup(session, year, month_idx, day):
    """
    Fetch the club day-view calendar page.
    month_idx is 0-based (e.g. April = 3).
    URL is built from CALENDAR_URL_TEMPLATE in .env.
    """
    url = Config.CALENDAR_URL_TEMPLATE.format(year=year, month=month_idx, day=day)
    resp = session.get(url)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, 'html.parser')


def extract_calendar_table(soup, date_str):
    """
    Parse the club calendar HTML and return a DataFrame with columns:
        time         (str, HH:MM 24h)
        court        (str, e.g. 'Court 1')
        booking_text (str or None — None/empty means the slot is available)
        href         (str or None — the URL to follow to book this slot)

    ⚠️  You may need to adjust the table selectors below based on the
        actual HTML structure. Inspect the page and update the class/id
        names to match.
    """
    rows_data = []

    # Find the calendar table — try common class names, fall back to first table
    table = (
        soup.find('table', class_='calTable') or
        soup.find('table', id='calTable') or
        soup.find('table', class_='calendar') or
        soup.find('table')
    )

    if not table:
        logger.warning(f"No calendar table found in HTML for {date_str}")
        return pd.DataFrame()

    all_rows = table.find_all('tr')
    if len(all_rows) < 2:
        return pd.DataFrame()

    # Court names from header row (skip first 'Time' column)
    header_cells = all_rows[0].find_all(['th', 'td'])
    court_names = [cell.get_text(strip=True) for cell in header_cells[1:]]

    # Data rows
    for row in all_rows[1:]:
        cells = row.find_all('td')
        if not cells:
            continue

        raw_time = cells[0].get_text(strip=True)
        normalized_time = _normalize_time(raw_time)
        if not normalized_time:
            continue

        for i, cell in enumerate(cells[1:]):
            court_name = court_names[i] if i < len(court_names) else f"Court {i + 1}"
            text = cell.get_text(strip=True)
            link = cell.find('a')
            href = link.get('href') if link else None

            # booking_text is None when the slot is available
            booking_text = text if text and text.lower() != 'available' else None

            rows_data.append({
                'date': date_str,
                'time': normalized_time,
                'court': court_name,
                'booking_text': booking_text,
                'href': href
            })

    return pd.DataFrame(rows_data)


def _normalize_time(raw):
    """Convert '07:00 AM', '7:00AM', or '07:00' → '07:00' (24h, zero-padded)."""
    raw = raw.strip()
    for fmt in ('%I:%M %p', '%I:%M%p', '%H:%M'):
        try:
            return datetime.strptime(raw, fmt).strftime('%H:%M')
        except ValueError:
            continue
    logger.debug(f"Could not parse time string: '{raw}'")
    return None


# ---------------------------------------------------------------------------
# Main function — called by the orchestrator
# ---------------------------------------------------------------------------

def check_court_availability(target_date):
    """
    Log into the club site with bot credentials (TENNIS_USERNAME / TENNIS_PASSWORD from .env)
    and return all available court slots for target_date.

    Returns a dict grouped by start time:
        { '07:00': [{'court': 'Court 1', 'href': 'https://...'}, ...], ... }
    """
    session = make_session()
    try:
        login_club(session, Config.TENNIS_USER, Config.TENNIS_PASS)

        year = target_date.year
        month_idx = target_date.month - 1  # calendar uses 0-indexed months (April = 3)
        day = target_date.day
        date_str = target_date.strftime('%Y-%m-%d')

        soup = get_calendar_soup(session, year, month_idx, day)
        df = extract_calendar_table(soup, date_str)

        if df.empty:
            logger.warning(f"No calendar data found for {date_str}")
            return {}

        # Keep only slots where booking_text is empty (available)
        available = df[df['booking_text'].isna() | (df['booking_text'] == '')].copy()

        # Group by time → list of {court, href}, sorted by court name
        grouped = {}
        for _, row in available.iterrows():
            t = row['time']
            if t not in grouped:
                grouped[t] = []
            grouped[t].append({'court': row['court'], 'href': row['href']})

        for t in grouped:
            grouped[t].sort(key=lambda x: x['court'])

        total = sum(len(v) for v in grouped.values())
        logger.info(f"Found {total} available slots on {date_str}")
        return grouped

    except Exception as e:
        logger.error(f"Court availability check failed: {e}", exc_info=True)
        return {}
    finally:
        session.close()

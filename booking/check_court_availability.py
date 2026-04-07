# Club website scraping — login, fetch calendar, extract available courts

import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import Config
from extensions import get_logger

logger = get_logger(__name__)

# (connect_timeout, read_timeout) in seconds
TIMEOUT = (10, 30)

# Derive the app base URL from CLUB_LOGIN_URL.
# e.g. "https://host/app/home/login.do" → "https://host/app/home"
def _base():
    return Config.CLUB_LOGIN_URL.rsplit('/', 1)[0]


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def make_session():
    """Create a requests.Session with retries and a browser-like User-Agent."""
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0"})

    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=1.5,                         # waits: 1.5s, 3s, 6s, 12s, 24s
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def _safe_request(fn, *args, **kwargs):
    """Wrap a requests call with a single retry on ReadTimeout."""
    try:
        return fn(*args, **kwargs)
    except requests.exceptions.ReadTimeout:
        logger.warning("ReadTimeout — sleeping 5s then retrying once...")
        time.sleep(5)
        return fn(*args, **kwargs)


def login_club(session, username, password):
    """
    POST credentials to the club login endpoint, then GET a protected page
    to verify the session actually stuck.
    Raises RuntimeError on login failure or session timeout.
    """
    base = _base()
    payload = {"userId": username, "password": password}

    r = _safe_request(
        session.post, Config.CLUB_LOGIN_URL,
        data=payload, allow_redirects=True, timeout=TIMEOUT
    )
    r.raise_for_status()

    # Verify the session is valid by hitting a page that requires auth
    w = _safe_request(
        session.get, f"{base}/reportView.do?id=124&workflow=true",
        timeout=TIMEOUT
    )
    w.raise_for_status()

    if "session has timed out" in w.text.lower():
        raise RuntimeError(f"Club login failed for '{username}' — session did not persist.")

    logger.info(f"Club login successful for '{username}'")


def get_calendar_soup(session, year, month_idx, day):
    """
    Fetch the club day-view calendar page.
    month_idx is 0-based (e.g. April = 3).
    URL is built from CALENDAR_URL_TEMPLATE in .env.
    """
    url = Config.CALENDAR_URL_TEMPLATE.format(year=year, month=month_idx, day=day)
    session.headers["Referer"] = url

    resp = _safe_request(session.get, url, timeout=TIMEOUT)
    resp.raise_for_status()

    if "session has timed out" in resp.text.lower():
        raise RuntimeError(f"Session timed out fetching calendar for {year}-{month_idx+1:02d}-{day:02d}")

    return BeautifulSoup(resp.text, "html.parser")


# ---------------------------------------------------------------------------
# Calendar parsing
# ---------------------------------------------------------------------------

def extract_calendar_table(soup, date_str):
    """
    Parse the club calendar HTML and return a DataFrame with columns:
        date, time, court, bgcolor, font_color, booking_text, href

    HTML structure (confirmed):
      <table class="calendar">
        <tr><th>Court 1</th><th>Court 2</th>...</tr>   ← court names in headers
        <tr>                                             ← one row per time slot
          <td bgcolor="...">
            <a href="workflowView.do?...">
              <span class="time">12:00 PM</span>         ← or class="timered"
              <span class="calbook">Available</span>      ← or class="calbookred"
            </a>
          </td>
          ...one <td> per court...
        </tr>
      </table>

    'booking_text' is None when the cell text is 'Available' (the slot is free).
    For booked slots it contains the player/team name.
    'bgcolor' can be used to identify booking type if needed (see color_dictionary).
    """
    calendar_table = soup.find("table", class_="calendar")
    if not calendar_table:
        logger.warning(f"No <table class='calendar'> found for {date_str}")
        return pd.DataFrame()

    headers = [th.get_text(strip=True) for th in calendar_table.find_all("th")]
    records = []

    for row in calendar_table.find_all("tr")[1:]:    # skip header row
        tds = row.find_all("td")
        for court_index, td in enumerate(tds):
            court_name = headers[court_index] if court_index < len(headers) else f"Court {court_index + 1}"

            link = td.find("a")
            href = link.get("href") if link else None

            # class is either "time" (normal) or "timered" (peak hour / restricted)
            time_span = td.find("span", class_=["time", "timered"])
            # class is either "calbook" (normal) or "calbookred"
            booking_span = td.find("span", class_=["calbook", "calbookred"])
            font_tag = td.find("font")

            raw_time = time_span.get_text(strip=True) if time_span else None
            calbook_text = booking_span.get_text(strip=True) if booking_span else None

            records.append({
                "date": date_str,
                "time": _normalize_time(raw_time) if raw_time else None,
                "court": court_name,
                "bgcolor": td.get("bgcolor"),
                "font_color": font_tag.get("color") if font_tag else None,
                "booking_text": None if (calbook_text or "").lower() == "available" else calbook_text,
                "href": href,
            })

    return pd.DataFrame(records)


def _normalize_time(raw):
    """Convert '07:00 AM', '7:00AM', or '07:00' → '07:00' (24h, zero-padded)."""
    raw = raw.strip()
    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M"):
        try:
            return datetime.strptime(raw, fmt).strftime("%H:%M")
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

    Returns a dict grouped by start time (24h HH:MM):
        { '07:00': [{'court': 'Court 1', 'href': '...'}, ...], ... }
    """
    session = make_session()
    try:
        login_club(session, Config.TENNIS_USER, Config.TENNIS_PASS)

        year = target_date.year
        month_idx = target_date.month - 1      # calendar uses 0-indexed months (April = 3)
        day = target_date.day
        date_str = target_date.strftime("%Y-%m-%d")

        soup = get_calendar_soup(session, year, month_idx, day)
        df = extract_calendar_table(soup, date_str)

        if df.empty:
            logger.warning(f"No calendar data found for {date_str}")
            return {}

        # Keep only rows with no time (malformed) and no booking text (available)
        available = df[
            df["time"].notna() &
            (df["booking_text"].isna() | (df["booking_text"] == ""))
        ].copy()

        # Group by time → list of {court, href}, sorted by court name
        grouped = {}
        for _, row in available.iterrows():
            t = row["time"]
            if t not in grouped:
                grouped[t] = []
            grouped[t].append({"court": row["court"], "href": row["href"]})

        for t in grouped:
            grouped[t].sort(key=lambda x: x["court"])

        total = sum(len(v) for v in grouped.values())
        logger.info(f"Found {total} available slots on {date_str}")
        return grouped

    except Exception as e:
        logger.error(f"Court availability check failed: {e}", exc_info=True)
        return {}
    finally:
        session.close()

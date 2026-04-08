# Court booking logic — parallel workers, one per booking request

import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from booking.check_court_availability import make_session, login_club, _safe_request, TIMEOUT, _base
from booking.models import BookingResult
from extensions import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Shared court pool
# ---------------------------------------------------------------------------

def _build_court_pool(available_by_time):
    """
    Build the shared mutable pool of available courts.

    Structure: { 'HH:MM': deque([{'court': ..., 'href': ...}, ...]) }

    Each worker pops from the front of the deque for their chosen time.
    Once popped, a slot is gone — no other worker can claim it.
    This is the single source of truth for what's still available at runtime.
    """
    return {
        time: deque(slots)
        for time, slots in available_by_time.items()
    }


def _pop_court(pool, lock, time):
    """
    Atomically pop the next available court at `time` from the shared pool.
    Returns {'court': str, 'href': str} or None if the pool at that time is empty.
    """
    with lock:
        q = pool.get(time)
        if q:
            return q.popleft()
    return None


# ---------------------------------------------------------------------------
# HTTP booking logic
# ---------------------------------------------------------------------------

def _attempt_booking(session, href, opponent_name):
    """
    Book a court slot using two HTTP requests — no browser needed.

    Flow:
      1. GET workflowView.do  → booking confirmation form with hidden session fields
      2. POST the form        → submits the reservation

    Confirmed field: Team_Two_Auto (jQuery UI autocomplete — opponent display name).
    We also populate Team_Two with the same value as a fallback in case the server
    needs the hidden resolved-ID field alongside the visible autocomplete field.

    ⚠️  If bookings are rejected, inspect the POST body via DevTools Network tab
        when booking manually and add any missing fields here.

    Returns (success: bool, error: str | None, booked_time: str | None)
    The booked_time is parsed from the form hidden fields if present.
    """
    base = _base()
    full_url = href if href.startswith('http') else f"{base}/{href.lstrip('/')}"

    # Step 1 — GET the booking/workflow page
    resp = _safe_request(session.get, full_url, timeout=TIMEOUT)
    resp.raise_for_status()

    if "session has timed out" in resp.text.lower():
        return False, 'session_expired', None

    soup = BeautifulSoup(resp.text, 'html.parser')
    form = soup.find('form')
    if not form:
        logger.error(f"No form found on booking page: {full_url}")
        return False, 'no_form', None

    # Collect all hidden/pre-filled inputs (workflow token, court id, date, time, etc.)
    fields = {
        inp['name']: inp.get('value', '')
        for inp in form.find_all('input')
        if inp.get('name')
    }

    # Fill in the opponent name
    first_opponent = opponent_name.split(',')[0].strip()
    fields['Team_Two_Auto'] = first_opponent
    fields['Team_Two'] = first_opponent

    # Step 2 — POST the form
    action = form.get('action', '')
    post_url = action if action.startswith('http') else f"{base}/{action.lstrip('/')}"
    post_resp = _safe_request(session.post, post_url, data=fields,
                              allow_redirects=True, timeout=TIMEOUT)
    post_resp.raise_for_status()

    lower = post_resp.text.lower()
    failure_phrases = ['already booked', 'not available', 'unavailable', 'court is taken']
    if any(phrase in lower for phrase in failure_phrases):
        return False, 'court_taken', None

    return True, None, None


# ---------------------------------------------------------------------------
# Per-request worker
# ---------------------------------------------------------------------------

def _book_single(request, pool, lock):
    """
    Book one court for one request.

    Iterates through req.times_to_try in order. For each time, pops courts
    from the shared pool one by one until a booking succeeds or the pool
    for that time is exhausted. Then moves to the next time.

    The pool is the live source of truth — once a slot is popped by any
    worker, no other worker can claim it.

    Returns a BookingResult with booked_time set to the actual time booked
    (may differ from the requested time if a fallback was used).
    """
    session = make_session()
    try:
        login_club(session, request.tennis_username, request.tennis_password)
    except Exception as e:
        logger.error(f"Login failed for {request.user_id}: {e}")
        return BookingResult(event_id=request.event_id, success=False, error='login_failed')

    # Put the pre-assigned court back at the front of its pool slot so this
    # worker tries it first before anyone else can grab it.
    if request.court and request.booking_href:
        with lock:
            q = pool.get(request.start_time)
            if q is not None:
                q.appendleft({'court': request.court, 'href': request.booking_href})

    for time in request.times_to_try:
        while True:
            slot = _pop_court(pool, lock, time)
            if slot is None:
                # Pool for this time exhausted — move to next fallback time
                logger.info(f"{request.user_id}: no courts left at {time}, trying next time slot")
                break

            logger.info(f"{request.user_id}: trying {slot['court']} at {time}")
            success, error, _ = _attempt_booking(session, slot['href'], request.opponent)

            if success:
                request.court = slot['court']
                if time != request.start_time:
                    logger.info(
                        f"{request.user_id}: booked at fallback time {time} "
                        f"(originally requested {request.start_time})"
                    )
                return BookingResult(
                    event_id=request.event_id,
                    success=True,
                    court=slot['court'],
                    booked_time=time
                )

            if error == 'court_taken':
                # Externally taken — slot is already gone from our pool (we popped it),
                # so we just loop and pop the next one.
                logger.warning(f"{slot['court']} at {time} already taken externally, trying next court...")
                continue

            # Any other error (login, no form, etc.) — stop retrying entirely
            return BookingResult(event_id=request.event_id, success=False, error=error)

    return BookingResult(event_id=request.event_id, success=False, error='no_courts_available')


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def book_courts(assigned, available_by_time):
    """
    Spawn one thread per booking request and run them in parallel.

    All workers share a single court pool (dict of deques) and a lock.
    Popping from the pool is atomic — no two workers can claim the same court.

    Returns: dict of { event_id: BookingResult }
    """
    if not assigned:
        return {}

    # Build the shared live pool from the full availability snapshot.
    # Workers pop from this as they need courts.
    pool = _build_court_pool(available_by_time)
    lock = threading.Lock()

    results = {}

    with ThreadPoolExecutor(max_workers=len(assigned)) as executor:
        futures = {
            executor.submit(_book_single, req, pool, lock): req
            for req in assigned
        }

        for future in as_completed(futures):
            req = futures[future]
            try:
                result = future.result()
            except Exception as e:
                logger.error(f"Unexpected error for {req.user_id}: {e}", exc_info=True)
                result = BookingResult(event_id=req.event_id, success=False, error=str(e))

            results[req.event_id] = result
            if result.success:
                logger.info(f"SUCCESS: {req.user_id} → {result.court} at {result.booked_time}")
            else:
                logger.info(f"FAILED: {req.user_id} → {result.error}")

    return results

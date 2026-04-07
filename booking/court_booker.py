# Court booking logic — parallel workers, one per booking request

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from booking.check_court_availability import make_session, login_club
from booking.models import BookingResult
from extensions import get_logger

logger = get_logger(__name__)


def _attempt_booking(session, href, opponent_name):
    """
    Book a court slot using two HTTP requests — no browser needed.

    Flow (confirmed from Selenium code):
      1. GET workflowView.do  → loads the booking form with hidden session fields
      2. POST the form        → submits the reservation with the opponent's name

    Confirmed form field:
      Team_Two_Auto — the opponent's display name (jQuery UI autocomplete).
      In the browser, selecting a name from the autocomplete dropdown may also
      populate a hidden 'Team_Two' field with a player ID. We submit both with
      the same value as a best-effort fallback.

    ⚠️  If bookings are rejected, open the Network tab in DevTools while booking
        manually, check the exact POST body, and add any missing fields here.

    Returns (success: bool, error: str | None)
    """
    from booking.check_court_availability import _safe_request, TIMEOUT, _base

    base = _base()
    full_url = href if href.startswith('http') else f"{base}/{href.lstrip('/')}"

    # Step 1 — GET the workflow/booking page
    resp = _safe_request(session.get, full_url, timeout=TIMEOUT)
    resp.raise_for_status()

    if "session has timed out" in resp.text.lower():
        return False, 'session_expired'

    soup = BeautifulSoup(resp.text, 'html.parser')
    form = soup.find('form')
    if not form:
        logger.error(f"No form found on booking page: {full_url}")
        return False, 'no_form'

    # Collect all hidden/pre-filled inputs (workflow token, court id, date, time, etc.)
    fields = {
        inp['name']: inp.get('value', '')
        for inp in form.find_all('input')
        if inp.get('name')
    }

    # Fill in the opponent — only the first name for singles; for doubles the
    # booking site may have additional fields (inspect and add them if needed)
    first_opponent = opponent_name.split(',')[0].strip()
    fields['Team_Two_Auto'] = first_opponent
    fields['Team_Two'] = first_opponent     # hidden field the autocomplete may populate

    # Step 2 — POST the form
    action = form.get('action', '')
    post_url = action if action.startswith('http') else f"{base}/{action.lstrip('/')}"
    post_resp = _safe_request(session.post, post_url, data=fields,
                              allow_redirects=True, timeout=TIMEOUT)
    post_resp.raise_for_status()

    lower = post_resp.text.lower()

    failure_phrases = ['already booked', 'not available', 'unavailable', 'court is taken']
    if any(phrase in lower for phrase in failure_phrases):
        return False, 'court_taken'

    # No failure phrase detected → treat as success.
    # ⚠️  Verify once the booking window is open: check what the confirmation page says.
    return True, None


def _book_single(request, all_slots_for_time, lock, claimed_courts):
    """
    Book one court for one request.

    Tries the pre-assigned court first (already in claimed_courts from the
    assignment phase). If the site says it's taken, atomically claims the
    next free court from all_slots_for_time and retries.

    The lock + claimed_courts set prevents two workers from racing to book
    the same fallback court.
    """
    session = make_session()
    try:
        login_club(session, request.tennis_username, request.tennis_password)
    except Exception as e:
        logger.error(f"Login failed for {request.user_id}: {e}")
        return BookingResult(event_id=request.event_id, success=False, error='login_failed')

    # Build ordered list: assigned court first, then all others as fallbacks
    assigned_court = request.court
    slots_to_try = (
        [s for s in all_slots_for_time if s['court'] == assigned_court] +
        [s for s in all_slots_for_time if s['court'] != assigned_court]
    )

    for slot in slots_to_try:
        court_key = (request.date, request.start_time, slot['court'])

        # Atomically claim this court — skip if another worker already claimed it
        with lock:
            if court_key in claimed_courts:
                continue
            claimed_courts.add(court_key)

        logger.info(f"{request.user_id}: trying {slot['court']}")
        success, error = _attempt_booking(session, slot['href'], request.opponent)

        if success:
            request.court = slot['court']  # update in case we used a fallback
            return BookingResult(
                event_id=request.event_id,
                success=True,
                court=slot['court']
            )

        if error == 'court_taken':
            # Release our claim so this court stays available for error tracking
            with lock:
                claimed_courts.discard(court_key)
            logger.warning(f"{slot['court']} already taken externally, trying next...")
            continue

        # Any other error — stop retrying
        return BookingResult(event_id=request.event_id, success=False, error=error)

    return BookingResult(event_id=request.event_id, success=False, error='no_courts_available')


def book_courts(assigned, available_by_time):
    """
    Spawn one thread per booking request and run them in parallel.

    All threads share a lock and claimed_courts set so they don't race
    to book the same fallback court.

    Returns: dict of { event_id: BookingResult }
    """
    if not assigned:
        return {}

    lock = threading.Lock()
    # Pre-claim each request's assigned court so no other worker picks it first
    claimed_courts = {
        (req.date, req.start_time, req.court)
        for req in assigned
        if req.court
    }

    results = {}

    with ThreadPoolExecutor(max_workers=len(assigned)) as executor:
        futures = {
            executor.submit(
                _book_single,
                req,
                available_by_time.get(req.start_time, []),
                lock,
                claimed_courts
            ): req
            for req in assigned
        }

        for future in as_completed(futures):
            req = futures[future]
            try:
                result = future.result()
            except Exception as e:
                logger.error(f"Unexpected error booking for {req.user_id}: {e}", exc_info=True)
                result = BookingResult(event_id=req.event_id, success=False, error=str(e))

            results[req.event_id] = result
            status = 'SUCCESS' if result.success else f'FAILED ({result.error})'
            logger.info(f"Booking result for {req.user_id}: {status}")

    return results

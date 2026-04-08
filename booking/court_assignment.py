# Deduplication and court assignment

from datetime import datetime, timedelta
from extensions import get_logger

logger = get_logger(__name__)


def _player_set(req):
    """
    Return the frozenset of all player names involved in this match.
    Used as a match fingerprint for deduplication.
    """
    user_name = req.tennis_site_name or req.user_id
    opponent_names = {n.strip() for n in req.opponent.split(',') if n.strip()}
    return frozenset({user_name} | opponent_names)


def get_courts_for_slot(available_by_time, start_time, duration_mins):
    """
    Return courts available for the ENTIRE duration of a booking slot.
    A 90-minute booking at 10:00 requires courts free at both 10:00 AND 11:00.

    Returns: list of {'court': str, 'href': str}, sorted by court name.
    """
    start_dt = datetime.strptime(start_time, '%H:%M')
    hours_needed = max(1, (duration_mins + 59) // 60)

    required_times = [
        (start_dt + timedelta(hours=i)).strftime('%H:%M')
        for i in range(hours_needed)
    ]

    first_slots = available_by_time.get(required_times[0], [])
    available = {s['court']: s['href'] for s in first_slots}

    for t in required_times[1:]:
        courts_at_t = {s['court'] for s in available_by_time.get(t, [])}
        available = {c: h for c, h in available.items() if c in courts_at_t}

    return sorted(
        [{'court': c, 'href': h} for c, h in available.items()],
        key=lambda x: x['court']
    )


def _fallback_times(start_time, available_by_time, duration_mins):
    """
    Return an ordered list of times to attempt booking, starting with the
    requested time and expanding outward within the allowed window:
        1. Original time (always first)
        2. 1 hour before  (up to 1hr before allowed)
        3. 1 hour after   (up to 2hrs after allowed)
        4. 2 hours after

    Only includes times that exist in available_by_time AND have at least one
    court free for the full duration. Times outside 06:00-22:00 are excluded.
    """
    start_dt = datetime.strptime(start_time, '%H:%M')

    # Order: original → 1hr before → 1hr after → 2hrs after
    offsets_minutes = [0, -60, 60, 120]

    result = []
    for offset in offsets_minutes:
        candidate = start_dt + timedelta(minutes=offset)
        # Sanity-check reasonable court hours
        if not (6 <= candidate.hour <= 22):
            continue
        t = candidate.strftime('%H:%M')
        if t not in available_by_time:
            continue
        if get_courts_for_slot(available_by_time, t, duration_mins):
            result.append(t)

    return result


def deduplicate_and_assign(requests, available_by_time):
    """
    Step 1 — Deduplicate:
      Strategy A: same event_id → both users have the same Google Calendar event.
                  Keep the creator.
      Strategy B: same (date, start_time, player set) → independently created
                  events for the same match. Keep the creator.

    Step 2 — Assign courts:
      For each unique booking, try the requested time first, then fallback times
      (1hr before → 1hr after → 2hrs after). Pre-assign the first available court
      at the best time, without replacement across requests.

    Sets req.times_to_try (ordered list for worker to follow at runtime) and
    req.court / req.booking_href (the pre-assigned first attempt).

    Returns: list of BookingRequest with assignment fields set.
    """
    # --- Strategy A: group by event_id ---
    by_event = {}
    for req in requests:
        by_event.setdefault(req.event_id, []).append(req)

    after_a = []
    for group in by_event.values():
        creator = next((r for r in group if r.is_creator), group[0])
        after_a.append(creator)

    # --- Strategy B: group by (date, start_time, player_set) ---
    by_match = {}
    for req in after_a:
        key = (req.date, req.start_time, _player_set(req))
        by_match.setdefault(key, []).append(req)

    deduplicated = []
    for group in by_match.values():
        creator = next((r for r in group if r.is_creator), group[0])
        deduplicated.append(creator)

    logger.info(
        f"Dedup: {len(requests)} raw → {len(after_a)} after event_id → "
        f"{len(deduplicated)} after match key"
    )

    # --- Pre-assign courts (sample without replacement across all requests) ---
    assigned = []
    used_court_keys = set()  # (date, time, court) — prevents double-assignment

    for req in deduplicated:
        # Compute ordered fallback times for this request
        req.times_to_try = _fallback_times(req.start_time, available_by_time, req.duration)

        if not req.times_to_try:
            logger.warning(
                f"No courts available at any time for {req.user_id} "
                f"vs {req.opponent} on {req.date} around {req.start_time}"
            )
            continue

        # Pre-assign: pick the first free court at the first available time
        chosen_slot = None
        chosen_time = None
        for t in req.times_to_try:
            slots = get_courts_for_slot(available_by_time, t, req.duration)
            for slot in slots:
                key = (req.date, t, slot['court'])
                if key not in used_court_keys:
                    chosen_slot = slot
                    chosen_time = t
                    used_court_keys.add(key)
                    break
            if chosen_slot:
                break

        if chosen_slot:
            req.court = chosen_slot['court']
            req.booking_href = chosen_slot['href']
            fallback_note = f" (fallback from {req.start_time})" if chosen_time != req.start_time else ""
            logger.info(
                f"Assigned {chosen_slot['court']} at {chosen_time}{fallback_note} "
                f"→ {req.user_id} vs {req.opponent}"
            )
            assigned.append(req)
        else:
            logger.warning(
                f"All courts already assigned for {req.user_id} at all candidate times"
            )

    return assigned

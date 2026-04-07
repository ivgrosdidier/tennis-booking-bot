# Deduplication and court assignment

from datetime import datetime, timedelta
from extensions import get_logger

logger = get_logger(__name__)


def _player_set(req):
    """
    Return the frozenset of all player names involved in this match.
    Used as a match fingerprint for deduplication.

    Example singles:  {'John Smith', 'Mary Jones'}
    Example doubles:  {'John Smith', 'Mary Jones', 'Bob Lee', 'Sue Park'}

    tennis_site_name is the user's name as it appears on the club booking site
    (same format as player names in the players collection).
    Falls back to user_id until tennis_site_name is populated in Firestore.
    """
    user_name = req.tennis_site_name or req.user_id
    opponent_names = {n.strip() for n in req.opponent.split(',') if n.strip()}
    return frozenset({user_name} | opponent_names)


def get_courts_for_slot(available_by_time, start_time, duration_mins):
    """
    Return courts available for the ENTIRE duration of a booking slot.

    Example: a 90-minute booking at 10:00 requires courts free at both
    10:00 AND 11:00. This intersects availability across all required hours.

    Returns: list of {'court': str, 'href': str}, sorted by court name.
    """
    start_dt = datetime.strptime(start_time, '%H:%M')
    hours_needed = max(1, (duration_mins + 59) // 60)  # ceil to nearest hour

    required_times = [
        (start_dt + timedelta(hours=i)).strftime('%H:%M')
        for i in range(hours_needed)
    ]

    # Start with courts available at the first time slot
    first_slots = available_by_time.get(required_times[0], [])
    available = {s['court']: s['href'] for s in first_slots}

    # Keep only courts also free at each subsequent hour
    for t in required_times[1:]:
        courts_at_t = {s['court'] for s in available_by_time.get(t, [])}
        available = {c: h for c, h in available.items() if c in courts_at_t}

    return sorted(
        [{'court': c, 'href': h} for c, h in available.items()],
        key=lambda x: x['court']
    )


def deduplicate_and_assign(requests, available_by_time):
    """
    Step 1 — Deduplicate:
      Strategy A: same event_id → both users have the same Google Calendar event
                  (one created it, the other was an invitee). Keep the creator.
      Strategy B: same (date, start_time, player set) → both users independently
                  created events for the same match. Keep the creator; if neither
                  is flagged as creator, keep the first one found.

    Step 2 — Assign courts:
      For each unique booking, pick the first available court for the full
      duration. No two bookings get the same court (sample without replacement).

    Returns: list of BookingRequest with .court and .booking_href set.
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

    # --- Assign courts (sample without replacement) ---
    assigned = []
    used_court_keys = set()  # (date, start_time, court)

    for req in deduplicated:
        slots = get_courts_for_slot(available_by_time, req.start_time, req.duration)

        chosen = None
        for slot in slots:
            key = (req.date, req.start_time, slot['court'])
            if key not in used_court_keys:
                chosen = slot
                used_court_keys.add(key)
                break

        if chosen:
            req.court = chosen['court']
            req.booking_href = chosen['href']
            assigned.append(req)
            logger.info(
                f"Assigned {chosen['court']} → {req.user_id} vs {req.opponent} at {req.start_time}"
            )
        else:
            logger.warning(
                f"No available court for {req.user_id} at {req.start_time} on {req.date}"
            )

    return assigned

# dedupes and assigns courts 

import logging

logger = logging.getLogger(__name__)

def deduplicate_and_assign(requests, available_courts):
    """
    Remove duplicates (keep event creator)
    Assign courts (first come, first served)
    """
    
    # Group by (date, time, opponent)
    grouped = {}
    for req in requests:
        key = (req.date, req.time, req.opponent.lower())
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(req)
    
    logger.info(f"Grouped {len(requests)} requests into {len(grouped)} bookings")
    
    # Deduplicate: keep event creator
    deduplicated = []
    for key, group in grouped.items():
        if len(group) > 1:
            creator = next((r for r in group if r.is_creator), None)
            chosen = creator if creator else group[0]
        else:
            chosen = group[0]
        deduplicated.append(chosen)
    
    # Assign courts
    assigned = []
    used_courts = set()
    
    for req in deduplicated:
        courts = available_courts.get(req.date, {}).get(req.time, [])
        
        if not courts:
            logger.warning(f"No courts for {req.date} {req.time}")
            continue
        
        for court in courts:
            court_key = (req.date, req.time, court)
            if court_key not in used_courts:
                req.court = court
                used_courts.add(court_key)
                assigned.append(req)
                logger.info(f"Assigned {court} to {req.opponent}")
                break
    
    return assigned
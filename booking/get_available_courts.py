from datetime import datetime, timedelta

def find_available_courts(session, target_date, start_time_str, duration_hours=1):
    """
    Returns a prioritized list of court names available for the requested slot.
    """
    # 1. Get the full day's data
    year = target_date.year
    month_index = target_date.month - 1
    day = target_date.day
    date_str = target_date.strftime("%Y-%m-%d")

    soup, _ = get_calendar_soup(session, year, month_index, day)
    df = extract_calendar_table(soup, date_str)

    if df.empty:
        return []

    # 2. Define the hours we need to check
    # Convert "05:00" or "5:00 PM" into a consistent comparison format
    try:
        start_dt = datetime.strptime(start_time_str, "%H:%M")
    except ValueError:
        start_dt = datetime.strptime(start_time_str, "%I:%M %p")
    
    required_hours = []
    for i in range(duration_hours):
        hour_dt = start_dt + timedelta(hours=i)
        # Match the site's format (e.g., "02:00 PM")
        required_hours.append(hour_dt.strftime("%I:%M %p"))

    # 3. Analyze availability by court
    court_availability = {} # { 'Court 1': [True, False], 'Court 2': [True, True] }
    
    for hour in required_hours:
        # Filter dataframe for this specific time row
        row_data = df[df['time'] == hour]
        
        for _, row in row_data.iterrows():
            court = row['court']
            is_avail = row['booking_text'] == "Available"
            
            if court not in court_availability:
                court_availability[court] = []
            court_availability[court].append(is_avail)

    # 4. Prioritize Results
    fully_available = []
    partially_available = []

    for court, status_list in court_availability.items():
        # A court must have data for ALL requested hours to be 'fully' available
        if len(status_list) == duration_hours and all(status_list):
            fully_available.append(court)
        elif any(status_list):
            partially_available.append(court)

    # Sort numerically (Court 1, Court 2...)
    fully_available.sort()
    
    # Return the full list: Prioritize 2-hour blocks first, then 1-hour fragments
    return fully_available + partially_available

# --- Example Usage in your Morning Loop ---

def process_morning_bookings(session, booking_requests):
    """
    booking_requests: list of objects with .date, .time, .duration
    """
    for req in booking_requests:
        print(f"Checking availability for {req.opponent} at {req.time}...")
        
        available_courts = find_available_courts(
            session, 
            req.date, 
            req.time, 
            duration_hours=(req.duration // 60)
        )
        
        if not available_courts:
            print(f"Skipping: No courts found for {req.time}")
            continue

        # Try to book each court until one succeeds
        for court in available_courts:
            success = attempt_booking(session, req, court) # You'll define this POST
            if success:
                print(f"Successfully booked {court} for {req.opponent}")
                break
            else:
                print(f"Court {court} failed or taken, trying next...")


from datetime import datetime, timedelta

def find_available_courts(session, target_date, start_time_str, duration_hours=1):
    """
    Returns a prioritized list of court names available for the requested slot.
    """
    # 1. Get the full day's data
    year = target_date.year
    month_index = target_date.month - 1
    day = target_date.day
    date_str = target_date.strftime("%Y-%m-%d")

    soup, _ = get_calendar_soup(session, year, month_index, day)
    df = extract_calendar_table(soup, date_str)

    if df.empty:
        return []

    # 2. Define the hours we need to check
    # Convert "05:00" or "5:00 PM" into a consistent comparison format
    try:
        start_dt = datetime.strptime(start_time_str, "%H:%M")
    except ValueError:
        start_dt = datetime.strptime(start_time_str, "%I:%M %p")
    
    required_hours = []
    for i in range(duration_hours):
        hour_dt = start_dt + timedelta(hours=i)
        # Match the site's format (e.g., "02:00 PM")
        required_hours.append(hour_dt.strftime("%I:%M %p"))

    # 3. Analyze availability by court
    court_availability = {} # { 'Court 1': [True, False], 'Court 2': [True, True] }
    
    for hour in required_hours:
        # Filter dataframe for this specific time row
        row_data = df[df['time'] == hour]
        
        for _, row in row_data.iterrows():
            court = row['court']
            is_avail = row['booking_text'] == "Available"
            
            if court not in court_availability:
                court_availability[court] = []
            court_availability[court].append(is_avail)

    # 4. Prioritize Results
    fully_available = []
    partially_available = []

    for court, status_list in court_availability.items():
        # A court must have data for ALL requested hours to be 'fully' available
        if len(status_list) == duration_hours and all(status_list):
            fully_available.append(court)
        elif any(status_list):
            partially_available.append(court)

    # Sort numerically (Court 1, Court 2...)
    fully_available.sort()
    
    # Return the full list: Prioritize 2-hour blocks first, then 1-hour fragments
    return fully_available + partially_available

# --- Example Usage in your Morning Loop ---

def process_morning_bookings(session, booking_requests):
    """
    booking_requests: list of objects with .date, .time, .duration
    """
    for req in booking_requests:
        print(f"Checking availability for {req.opponent} at {req.time}...")
        
        available_courts = find_available_courts(
            session, 
            req.date, 
            req.time, 
            duration_hours=(req.duration // 60)
        )
        
        if not available_courts:
            print(f"Skipping: No courts found for {req.time}")
            continue

        # Try to book each court until one succeeds
        for court in available_courts:
            success = attempt_booking(session, req, court) # You'll define this POST
            if success:
                print(f"Successfully booked {court} for {req.opponent}")
                break
            else:
                print(f"Court {court} failed or taken, trying next...")


from datetime import datetime, timedelta

def find_available_courts(session, target_date, start_time_str, duration_hours=1):
    """
    Returns a prioritized list of court names available for the requested slot.
    """
    # 1. Get the full day's data
    year = target_date.year
    month_index = target_date.month - 1
    day = target_date.day
    date_str = target_date.strftime("%Y-%m-%d")

    soup, _ = get_calendar_soup(session, year, month_index, day)
    df = extract_calendar_table(soup, date_str)

    if df.empty:
        return []

    # 2. Define the hours we need to check
    # Convert "05:00" or "5:00 PM" into a consistent comparison format
    try:
        start_dt = datetime.strptime(start_time_str, "%H:%M")
    except ValueError:
        start_dt = datetime.strptime(start_time_str, "%I:%M %p")
    
    required_hours = []
    for i in range(duration_hours):
        hour_dt = start_dt + timedelta(hours=i)
        # Match the site's format (e.g., "02:00 PM")
        required_hours.append(hour_dt.strftime("%I:%M %p"))

    # 3. Analyze availability by court
    court_availability = {} # { 'Court 1': [True, False], 'Court 2': [True, True] }
    
    for hour in required_hours:
        # Filter dataframe for this specific time row
        row_data = df[df['time'] == hour]
        
        for _, row in row_data.iterrows():
            court = row['court']
            is_avail = row['booking_text'] == "Available"
            
            if court not in court_availability:
                court_availability[court] = []
            court_availability[court].append(is_avail)

    # 4. Prioritize Results
    fully_available = []
    partially_available = []

    for court, status_list in court_availability.items():
        # A court must have data for ALL requested hours to be 'fully' available
        if len(status_list) == duration_hours and all(status_list):
            fully_available.append(court)
        elif any(status_list):
            partially_available.append(court)

    # Sort numerically (Court 1, Court 2...)
    fully_available.sort()
    
    # Return the full list: Prioritize 2-hour blocks first, then 1-hour fragments
    return fully_available + partially_available

# --- Example Usage in your Morning Loop ---

def process_morning_bookings(session, booking_requests):
    """
    booking_requests: list of objects with .date, .time, .duration
    """
    for req in booking_requests:
        print(f"Checking availability for {req.opponent} at {req.time}...")
        
        available_courts = find_available_courts(
            session, 
            req.date, 
            req.time, 
            duration_hours=(req.duration // 60)
        )
        
        if not available_courts:
            print(f"Skipping: No courts found for {req.time}")
            continue

        # Try to book each court until one succeeds
        for court in available_courts:
            success = attempt_booking(session, req, court) # You'll define this POST
            if success:
                print(f"Successfully booked {court} for {req.opponent}")
                break
            else:
                print(f"Court {court} failed or taken, trying next...")     
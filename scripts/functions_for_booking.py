# find avail courts 

def find_available_court(page, target_time):
    """
    Scans the calendar page for the first available court at a specific time.
    Returns the selector or index of the court to click.
    """
    # target_time example: "08:00 AM"
    # Find the row that matches the time string
    row = page.locator("tr", has_text=target_time)
    
    # Within that row, find the first cell with class 'calbook'
    available_court = row.locator(".calbook").first
    
    if available_court.count() > 0:
        return available_court
    return None


# deduplicate users 

def get_all_pending_matches(users):
    unique_matches = []
    seen_match_keys = set()

    for user in users:
        events = get_events_for_user(user)
        for event in events:
            parsed = parse_event(event, user['uid'])
            
            # Create a unique key regardless of who is 'User 1' or 'User 2'
            players = sorted([user['full_name'], parsed.get('partner_name', 'Guest')])
            match_key = f"{parsed['time']}_{'_'.join(players)}"

            if match_key not in seen_match_keys:
                seen_match_keys.add(match_key)
                unique_matches.append({
                    'booker': user, # The person whose account we use
                    'parsed_event': parsed,
                    'match_key': match_key
                })
    return unique_matches


# combined booking

def book_court_v2(user, parsed_event):
    username = decrypt_string(user['club_username_encrypted'])
    password = decrypt_string(user['club_password_encrypted'])

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 1. Login
        page.goto(os.getenv('CLUB_LOGIN_URL'))
        page.fill('#username', username)
        page.fill('#password', password)
        page.click('#login-btn')

        # 2. Navigate to specific Calendar Day
        event_dt = datetime.fromisoformat(parsed_event['time'])
        calendar_url = os.getenv('CALENDAR_URL_TEMPLATE').format(
            year=event_dt.year,
            month=event_dt.month - 1,
            day=event_dt.day
        )
        page.goto(calendar_url)

        # 3. Find and click an available court cell (.calbook)
        # We look for the row matching the time, e.g., "09:00 AM"
        target_time_str = event_dt.strftime("%I:%M %p") 
        court_slot = find_available_court(page, target_time_str)

        if not court_slot:
            print(f"No courts available at {target_time_str}")
            return False

        court_slot.click() # This usually opens the booking form page
        page.wait_for_load_state('networkidle')

        # 4. Fill the booking form
        # Note: On TPTC, clicking the cell often auto-fills the court/time
        if parsed_event.get('partner_name'):
             # Replace with actual selector for partner search/field
            page.fill('#partner_name_field', parsed_event['partner_name'])
        
        page.click('#submit_booking_button')
        
        success = "confirmed" in page.content().lower()
        browser.close()
        return success
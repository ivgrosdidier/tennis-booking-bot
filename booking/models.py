# contains booking request class

"""Data structures for booking system"""

class BookingRequest:
    """A tennis booking request"""
    def __init__(self, user_id, event_id, date, time, opponent, court=None):
        self.user_id = user_id
        self.event_id = event_id
        self.date = date
        self.time = time
        self.opponent = opponent
        self.court = court
        self.is_creator = False

class BookingResult:
    """Result of a booking attempt"""
    def __init__(self, event_id, success, court=None, error=None):
        self.event_id = event_id
        self.success = success
        self.court = court
        self.error = error
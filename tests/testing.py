import os
import pytest
import firebase_admin
import json
from firebase_admin import credentials, firestore
from booking.firestore_queries import get_eligible_users, find_player_by_email

# --- CONFIGURATION ---
SERVICE_ACCOUNT_PATH = "firebase-auth.json"

def setup_module(module):
    """Initializes the Firebase app for the entire test module."""
    if not firebase_admin._apps:
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)

def test_get_eligible_users_structure():
    """
    Checks if the function returns a list, validates the 
    structure, and prints the collected user info.
    """
    users = get_eligible_users()
    
    # Check that it returns a list
    assert isinstance(users, list), "Should return a list of users"
    
    print(f"\n--- Total Eligible Users Found: {len(users)} ---")
    
    for i, user in enumerate(users):
        print(f"\nUser #{i+1}:")
        # Using json.dumps to make the dictionary print pretty in the terminal
        print(json.dumps(user, indent=4, default=str))

        # Validation Logic
        required_keys = [
            "user_id", "email", "tennis_username", 
            "tennis_password", "google_refresh_token", 
            "google_cal_id", "partners"
        ]
        for key in required_keys:
            assert key in user, f"Key '{key}' missing from user {user.get('user_id')}"
            
        assert isinstance(user['partners'], dict), f"Partners for {user.get('user_id')} should be a dict"

    if len(users) == 0:
        print("Warning: No users met the eligibility criteria in the database.")
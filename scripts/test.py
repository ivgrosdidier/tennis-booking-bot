import os
import json
from helpers.players import get_club_players, check_name_in_club_directory
from config import IS_DEV

def run_diagnostic():
    print("=== TENNIS BOT DIAGNOSTIC ===")
    print(f"Current Directory: {os.getcwd()}")
    print(f"IS_DEV Setting: {IS_DEV}")
    
    # 1. Test the cache loading
    players = get_club_players()
    print(f"Cache Size: {len(players)} players loaded.")
    
    if len(players) == 0:
        print("❌ ERROR: Cache is empty! Check your JSON path or Firestore connection.")
        return

    # 2. Inspect the keys for "Mitchell"
    print("\n--- Key Inspection ---")
    mitchell_hits = [k for k in players.keys() if "mitchell" in k.lower()]
    if mitchell_hits:
        print(f"Found similar keys in cache: {mitchell_hits}")
    else:
        print("❌ ERROR: No keys containing 'mitchell' found in cache.")

    # 3. Test the exact function the Blueprint uses
    test_name = "Mitchell Yasui"
    print(f"\n--- Function Test ---")
    print(f"Testing check_name_in_club_directory('{test_name}')...")
    
    result = check_name_in_club_directory(test_name)
    
    if result:
        print("✅ SUCCESS: The function found the name.")
    else:
        print("❌ FAILURE: The function did not find the name.")
        
        # Why did it fail?
        search_term = test_name.strip().lower()
        if search_term in players:
            print("Logic Check: The name IS in the dict, but the function returned False? (Check your imports)")
        else:
            print(f"Logic Check: '{search_term}' is literally not a key in the loaded dictionary.")
            print(f"Dictionary sample: {list(players.keys())[:5]}")

if __name__ == "__main__":
    run_diagnostic()
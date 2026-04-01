import json

def check_player_emails(file_path):
    # The list of names we are looking for
    target_names = ["Isabelle Grosdidier", "Mitchell Yasui", "Shawn Swartz", "Monica Siwicka", "Michael Parks"]
    
    try:
        with open(file_path, 'r') as f:
            player_data = json.load(f)
        
        # Dictionary comprehension to find matches
        matches = {name: player_data[name] for name in target_names if name in player_data}
        
        return matches

    except FileNotFoundError:
        return "Error: The file 'data/players.json' was not found."
    except json.JSONDecodeError:
        return "Error: Failed to decode JSON. Check the file format."

# Execute the check
results = check_player_emails('data/players.json')

if isinstance(results, dict):
    if results:
        print(f"Found {len(results)} matches:")
        for name, email in results.items():
            print(f"- {name}: {email}")
    else:
        print("No matches found for the specified names.")
else:
    print(results)
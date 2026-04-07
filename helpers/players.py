from extensions import db, get_logger
from google.cloud.firestore_v1.base_query import FieldFilter
from config import IS_DEV
import json
import os

logger = get_logger(__name__)

def partners_ref(uid: str):
    """Shorthand for the partners subcollection reference."""
    return db.collection("users").document(uid).collection("partners")
 
 
def check_duplicate_name(ref, full_name: str, exclude_id: str = None) -> bool:
    """Returns True if full_name already exists (excluding current doc if editing)."""
    for doc in ref.where("full_name", "==", full_name).get():
        if doc.id != exclude_id:
            return True
    return False
 
def check_duplicate_nick(ref, nickname: str, exclude_id: str = None) -> bool:
    """Returns True if nickname already exists (excluding current doc if editing)."""
    for doc in ref.where("nickname", "==", nickname).get():
        if doc.id != exclude_id:
            return True
    return False

# Module-level cache — loaded once per process lifetime
# None = not loaded yet | dict = loaded (even if empty)
_players_cache: dict | None = None

def get_club_players() -> dict:
    """
    Returns {name: email} dict loaded from Firestore club_players collection.
    Cached in memory after first load — reads Firestore only once per process.
    """
    global _players_cache

    if _players_cache is not None:
        return _players_cache
    
    # --- LOCAL LOGIC ---
    if IS_DEV:
        try:
            base_dir = os.path.dirname(os.path.dirname(__file__)) 
            json_path = os.path.join(base_dir, "data", "players.json")

            with open(json_path, "r") as f:
                raw_data = json.load(f)
                # CRITICAL: Normalize keys to title case for matching
                _players_cache = {str(k).strip().title(): v for k, v in raw_data.items()}
            
            logger.info(f"Successfully cached {len(_players_cache)} players from JSON")
        except Exception as e:
            logger.error(f"Failed to load JSON cache: {e}")
            _players_cache = {}

    # --- CLOUD LOGIC ---
    else:
        try:
            docs = db.collection("players").stream()
            _players_cache = {doc.id: doc.to_dict().get("email") for doc in docs}
            logger.info(f"Loaded {len(_players_cache)} players from Firestore")
        except Exception as e:
            logger.error(f"Could not load club_players from Firestore: {e}")
            _players_cache = {}

    return _players_cache

def get_sorted_player_names() -> list[str]:
    """Returns a list of all player names, sorted alphabetically."""
    players = get_club_players()
    return sorted(list(players.keys()))

def check_name_in_club_directory(full_name: str) -> bool:
    players = get_club_players()
    search_term = full_name.strip().title()
    
    # Using pipe symbols | to see if there are hidden spaces
    logger.info(f"DEBUG: Search Term is |{search_term}|")
    
    exists = search_term in players
    if not exists:
        # Show exactly what the keys look like with pipes
        sample = [f"|{k}|" for k in list(players.keys())[:3]]
        logger.info(f"DEBUG: Not found. Cache contains: {sample}")
        
    return exists

def check_name_in_club_directory2(full_name: str) -> bool:
    """Returns True if the titled name exists in the club directory."""
    return full_name.strip().title() in get_club_players()


def resolve_tennis_site_name(user_id: str, email: str, full_name: str, tennis_username: str) -> str | None:
    """
    Determine a user's name as it appears in the club's player directory,
    save it as 'tennis_site_name' on their Firestore user document, and return it.

    This runs at most 2 Firestore reads + up to 2 writes — once per user ever.
    After the first run, the result is cached in Firestore and never recalculated.

    Lookup order:
      1. Find a player document whose 'email' field matches this user's email
         → that document's ID (the player name) is their tennis_site_name
      2. Check if full_name (title-cased) is itself a document in the players collection
         → use it as tennis_site_name (they exist but have no email recorded)
      3. Neither found → create a new player document (full_name as ID,
         tennis_username as the email field) and use full_name as tennis_site_name
    """
    global _players_cache

    if not full_name or not email:
        logger.warning(f"Cannot resolve tennis_site_name for {user_id}: missing full_name or email")
        return None

    normalized_name = full_name.strip().title()
    tennis_site_name = None

    # Strategy 1: find by email in the players collection (1 Firestore read)
    results = db.collection('players').where(
        filter=FieldFilter('email', '==', email)
    ).limit(1).stream()
    for doc in results:
        tennis_site_name = doc.id
        break

    # Strategy 2: check if their full_name is already a player document (1 Firestore read)
    if not tennis_site_name:
        doc = db.collection('players').document(normalized_name).get()
        if doc.exists:
            tennis_site_name = normalized_name

    # Strategy 3: not in directory — add them (1 Firestore write to players)
    if not tennis_site_name:
        tennis_site_name = normalized_name
        db.collection('players').document(normalized_name).set({'email': tennis_username})
        logger.info(f"Added new player to directory: '{normalized_name}'")
        # Keep the in-memory cache consistent if it's already been loaded
        if _players_cache is not None:
            _players_cache[normalized_name] = tennis_username

    # Save result to the user document (1 Firestore write)
    db.collection('users').document(user_id).update({'tennis_site_name': tennis_site_name})
    logger.info(f"tennis_site_name resolved for {user_id}: '{tennis_site_name}'")
    return tennis_site_name

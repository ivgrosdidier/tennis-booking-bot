import logging
from extensions import db
from config import IS_DEV
import json
import os 

logger = logging.getLogger(__name__)

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

import logging
from extensions import db

logger = logging.getLogger(__name__)

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

    try:
        docs = db.collection("club_players").stream()
        _players_cache = {doc.id: doc.to_dict().get("email") for doc in docs}
        logger.info(f"Loaded {len(_players_cache)} players from Firestore")
    except Exception as e:
        logger.error(f"Could not load club_players from Firestore: {e}")
        _players_cache = {}

    return _players_cache


def check_name_in_club_directory(full_name: str) -> bool:
    """Returns True if the titled name exists in the club directory."""
    return full_name.strip().title() in get_club_players()


def reload_players() -> dict:
    """Force a fresh Firestore read — useful after updating the collection."""
    global _players_cache
    _players_cache = None
    return get_club_players()
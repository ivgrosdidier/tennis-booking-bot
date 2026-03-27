import json

_players_cache = None

def get_club_players():
    global _players_cache
    if _players_cache is not None:
        return _players_cache

    try:
        with open('data/players.json', encoding='utf-8') as f:
            raw = json.load(f)
            _players_cache = {name.strip().title() for name in raw.keys()}
            print(f"[Club Directory] Loaded {len(_players_cache)} players")
    except FileNotFoundError:
        print("[WARNING] players.json not found")
        _players_cache = set()

    return _players_cache


def check_name_in_club_directory(full_name: str) -> bool:
    return full_name.strip().title() in get_club_players()
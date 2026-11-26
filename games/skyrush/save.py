"""Local player profiles and SkyRush progress."""

import json
import os
import shutil
import tempfile
import unicodedata
from pathlib import Path

from src.shared.scene import load_json, save_json

SAVE_PATH = "results/skyrush_save.json"
OLD_PATH = "results/leaderboard.json"   # before the split into two games
PROFILES_PATH = "results/skyrush_profiles.json"
MAX_NAME_LENGTH = 20
_active_profile = None


def empty_progress():
    return {"missions": {}, "duels": {}, "adventures": []}


def can_import_legacy_progress():
    return (not os.path.exists(PROFILES_PATH)
            and (os.path.isfile(SAVE_PATH) or os.path.isfile(OLD_PATH)))


def _profiles():
    try:
        with open(PROFILES_PATH, encoding="utf-8") as file:
            profiles = json.load(file)
    except FileNotFoundError:
        return {}
    if not isinstance(profiles, dict) or any(
            not isinstance(player, dict) or not isinstance(player.get("name"), str)
            or not isinstance(player.get("progress"), dict) for player in profiles.values()):
        raise ValueError("The player save could not be read.")
    return profiles


def _save_profiles(profiles):
    path = Path(PROFILES_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False,
                                       dir=path.parent, prefix="skyrush-", suffix=".tmp")
    try:
        with temp:
            json.dump(profiles, temp, ensure_ascii=False, indent=2)
        os.replace(temp.name, path)
    finally:
        Path(temp.name).unlink(missing_ok=True)


def profile_names():
    return sorted((player["name"] for player in _profiles().values()), key=str.casefold)


def active_profile_name():
    return _active_profile


def _profile_key(name):
    return unicodedata.normalize("NFKC", name).casefold()


def select_profile(name):
    global _active_profile
    _active_profile = None if name is None else _profiles()[_profile_key(name)]["name"]


def create_profile(name):
    name = " ".join(unicodedata.normalize("NFKC", name).split())
    if not name or len(name) > MAX_NAME_LENGTH or not any(ch.isalnum() for ch in name):
        raise ValueError(f"Enter a name with 1 to {MAX_NAME_LENGTH} characters.")
    if not all(ch.isalnum() or ch in " _-" for ch in name):
        raise ValueError("Use letters, numbers, spaces, - or _.")
    profiles = _profiles()
    key = _profile_key(name)
    if key in profiles:
        raise ValueError("That name is already in use. Choose it from the list.")
    board = empty_progress()
    if not profiles and can_import_legacy_progress():
        old = SAVE_PATH if os.path.isfile(SAVE_PATH) else OLD_PATH
        with open(old, encoding="utf-8") as file:
            board = json.load(file)
        if not isinstance(board, dict):
            raise ValueError("The previous save could not be read.")
    profiles[key] = {"name": name, "progress": board}
    _save_profiles(profiles)
    select_profile(name)


def delete_profile(name):
    key = _profile_key(name)
    profiles = _profiles()
    del profiles[key]
    _save_profiles(profiles)
    if _active_profile is not None and _profile_key(_active_profile) == key:
        select_profile(None)


def load_leaderboard():
    if _active_profile is not None:
        return _profiles()[_profile_key(_active_profile)]["progress"]
    if not os.path.exists(SAVE_PATH) and os.path.exists(OLD_PATH):
        shutil.copyfile(OLD_PATH, SAVE_PATH)     # keep earlier progress
    return load_json(SAVE_PATH, empty_progress())


def save_leaderboard(board):
    if _active_profile is None:
        save_json(SAVE_PATH, board)
    else:
        profiles = _profiles()
        profiles[_profile_key(_active_profile)]["progress"] = board
        _save_profiles(profiles)


def complete_adventure(adventure):
    """Record a first clear alongside the existing SkyRush progress."""
    board = load_leaderboard()
    completed = board.setdefault("adventures", [])
    if adventure in completed:
        return False
    completed.append(adventure)
    save_leaderboard(board)
    return True

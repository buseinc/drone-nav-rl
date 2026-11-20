"""Scene base class and the persistent leaderboard."""

import json
import os

LEADERBOARD_PATH = "results/leaderboard.json"


class Scene:
    """One screen of the game. The App calls these every frame."""

    def __init__(self, app):
        self.app = app

    def handle_event(self, event):
        pass

    def update(self, dt):
        """dt = milliseconds since the last frame."""

    def draw(self, surf):
        pass


def load_leaderboard():
    try:
        with open(LEADERBOARD_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"missions": {}, "duels": {}}


def save_leaderboard(board):
    os.makedirs(os.path.dirname(LEADERBOARD_PATH), exist_ok=True)
    with open(LEADERBOARD_PATH, "w", encoding="utf-8") as f:
        json.dump(board, f, indent=2)

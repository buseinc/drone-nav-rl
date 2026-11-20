"""Scene base class and small JSON save helpers, shared by both games."""

import json
import os


class Scene:
    """One screen of a game. The App calls these every frame."""

    def __init__(self, app):
        self.app = app

    def handle_event(self, event):
        pass

    def update(self, dt):
        """dt = milliseconds since the last frame."""

    def draw(self, surf):
        pass


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

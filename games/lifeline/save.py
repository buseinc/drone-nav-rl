"""Lifeline save file (chapter progress). Separate from SkyRush."""

from src.shared.scene import load_json, save_json

SAVE_PATH = "results/lifeline_save.json"


def load_progress():
    return load_json(SAVE_PATH, {"chapters": {}})


def save_progress(data):
    save_json(SAVE_PATH, data)

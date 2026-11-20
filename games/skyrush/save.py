"""SkyRush save file (mission stars, duel records)."""

import os
import shutil

from src.shared.scene import load_json, save_json

SAVE_PATH = "results/skyrush_save.json"
OLD_PATH = "results/leaderboard.json"   # before the split into two games


def load_leaderboard():
    if not os.path.exists(SAVE_PATH) and os.path.exists(OLD_PATH):
        shutil.copyfile(OLD_PATH, SAVE_PATH)     # keep earlier progress
    return load_json(SAVE_PATH, {"missions": {}, "duels": {}})


def save_leaderboard(board):
    save_json(SAVE_PATH, board)

"""Game-world rules shared by every mode.

The world advances in ticks of TICK ms. On every tick each drone performs
exactly one action (a move or HOVER) and every patrol moves one cell. This
keeps the game identical to the environment ORCA was trained in.
"""

import random

from src.drone_env_v4 import HOVER, DroneEnvV4

TICK = 200
# If you are hovering and press a key within this part of a tick, the move
# still counts for the current tick (no waiting for the next one).
GRACE = 0.45 * TICK

AI_NAME = "ORCA"

# Arenas: the hazard sets ORCA was trained on.
ARENAS = [
    {"name": "CLEAR SKIES", "wind": 0, "enemies": 0,
     "tagline": "Open air. Pure racing line.",
     "color": (81, 220, 150)},
    {"name": "WIND VALLEY", "wind": 2, "enemies": 0,
     "tagline": "Jet streams push you. Ride them or fight them.",
     "color": (120, 210, 240)},
    {"name": "PATROL ZONE", "wind": 0, "enemies": 2,
     "tagline": "Security drones on patrol. Time your moves.",
     "color": (235, 70, 160)},
    {"name": "THE STORM", "wind": 2, "enemies": 2,
     "tagline": "Wind and patrols together. Only for aces.",
     "color": (255, 214, 90)},
]

# ORCA's skill levels: chance to hesitate one tick when it turns.
# Calibrated with a simulated perfect-route player who hesitates on half
# of the turns: ROOKIE ~80% player wins, ACE ~45%, LEGEND never hesitates.
LEVELS = [
    {"name": "ROOKIE", "hesitate": 0.75,
     "desc": "Hesitates at most turns. Good for warming up."},
    {"name": "ACE", "hesitate": 0.3,
     "desc": "Quick and sharp. A fair fight."},
    {"name": "LEGEND", "hesitate": 0.0,
     "desc": "Never hesitates. Beat it with a smarter route."},
]


def make_env(arena, seed=None, obstacles=15):
    a = ARENAS[arena]
    return DroneEnvV4(seed=seed, obstacle_count=obstacles,
                      wind_streams=a["wind"], enemy_count=a["enemies"])


def copy_env(env):
    """A second env with exactly the same map, wind and patrols."""
    other = DroneEnvV4(seed=0, obstacle_count=0, grid_size=env.grid_size)
    other.set_map(**env.map_spec())
    return other


class AIPilot:
    """Picks ORCA's action each tick, with human-like hesitation."""

    def __init__(self, agent, level=None):
        self.agent = agent
        self.p = LEVELS[level]["hesitate"] if level is not None else 0.0
        self.last_dir = None

    def act(self, env):
        action = self.agent.act(env.get_state())
        if action == HOVER:
            return action
        turning = self.last_dir is not None and action != self.last_dir
        if (turning and random.random() < self.p
                and not env.would_crash(HOVER)):
            return HOVER        # "thinking" - only if hovering is safe
        self.last_dir = action
        return action

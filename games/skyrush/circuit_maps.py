"""Generate and check Endless Circuit courses before showing them."""

import random
from collections import deque

from games.skyrush.missions import (follow_the_guard_env, hook_env,
                                    patrol_rhythm_env, wind_switch_env)
from src.drone_env_v4 import DIRS, N_ACTIONS, DroneEnvV4
from src.shared.world import copy_env

STAGE_KINDS = ("wind", "patrol", "mixed", "mixed", "boss")
STAGE_NAMES = {"wind": "Wind Run", "patrol": "Patrol Run", "mixed": "Storm Run", "boss": "Legend Race"}
STAGE_ZONES = {"wind": 1, "patrol": 2, "mixed": 3}
TEMPLATES = {"wind": (hook_env, wind_switch_env),
             "patrol": (follow_the_guard_env, patrol_rhythm_env),
             "mixed": (hook_env, wind_switch_env)}
BOSS_KINDS = ("wind", "patrol", "mixed")
# These variants also give the bundled Legend model a finish behind the shortest route.
FALLBACK_SEEDS = {"wind": (2, 3, 10), "patrol": (1, 8, 17), "mixed": (8, 20, 28)}


def read_map(spec):
    env = DroneEnvV4(seed=0, obstacle_count=0)
    env.set_map(**spec)
    return env


def course_spec(template, kind, phase):
    spec = template.map_spec()
    walls = spec["obstacles"]
    if kind == "patrol":
        if len(spec["enemies"]) == 1:
            walls.update(((4, 0), (6, 0)))
        else:
            walls.update(((3, 9), (6, 9)))
        return spec

    gate = 7 if (6, 7) in spec["wind"] else 8
    walls.update((6, col) for col in range(template.grid_size) if col != gate)
    walls.discard((6, gate))
    spec["wind"][(6, gate)] = (-1, 0)
    if kind == "mixed":
        track = [(4, col) for col in range(3, 9)]
        walls.difference_update(track)
        walls.update((3, col) for col in range(template.grid_size) if col != gate)
        walls.discard((3, gate))
        spec["enemies"] = [{"track": track, "phase": phase}]
    return spec


def varied_map(template, kind, rng, extra_walls):
    spec = course_spec(template, kind, rng.randrange(10) if kind == "mixed" else 0)

    size = template.grid_size
    turn = rng.randrange(4)
    mirror = rng.choice((False, True))

    def transform(pos):
        row, col = pos
        for _ in range(turn):
            row, col = col, size - 1 - row
        return (row, size - 1 - col) if mirror else (row, col)

    zero = transform((0, 0))
    directions = {direction: tuple(a - b for a, b in zip(transform(direction), zero))
                  for direction in DIRS}
    wind = {transform(pos): directions[direction] for pos, direction in spec["wind"].items()}
    walls = {transform(pos) for pos in spec["obstacles"]}
    patrols = [{"track": [transform(pos) for pos in patrol["track"]],
                "phase": patrol["phase"] + rng.randrange(-2, 3)} for patrol in spec["enemies"]]
    protected = set(wind) | {cell for patrol in patrols for cell in patrol["track"]}
    start, goal = transform(spec["start"]), transform(spec["goal"])

    def nearby(pos):
        row, col = pos
        options = [(row + dr, col + dc) for dr, dc in (*DIRS, (0, 0))]
        return [point for point in options if 0 <= point[0] < size and 0 <= point[1] < size
                and point not in walls and point not in protected]

    start, goal = rng.choice(nearby(start)), rng.choice(nearby(goal))
    extras = [(r, c) for r in range(size) for c in range(size)
              if (r, c) not in protected and (r, c) not in walls and (r, c) not in (start, goal)]
    walls.update(rng.sample(extras, extra_walls))
    return read_map(dict(start=start, goal=goal, obstacles=walls, wind=wind, enemies=patrols))


def has_route_without(env, patrol_cells=None):
    """Check every safe route while avoiding wind pushes or a particular patrol lane."""
    period = env._period()
    start = env.start, 0
    queue = deque([start])
    seen = {start}
    while queue:
        position, tick = queue.popleft()
        for action in range(N_ACTIONS):
            path, event = env.transition(position, action, tick)
            if event == "crash":
                continue
            if patrol_cells is None and len(path) > 1:
                continue
            if patrol_cells is not None and not patrol_cells.isdisjoint(path):
                continue
            if event == "goal":
                return True
            neighbor = path[-1], (tick + 1) % period
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return False


def has_trick(env, kind):
    best = env.optimal_length()
    if not 6 <= best <= 28:
        return False
    spec = env.map_spec()
    if kind in ("wind", "mixed"):
        if not env.wind or has_route_without(env):
            return False
        no_wind = read_map({**spec, "wind": {}}).optimal_length()
        if no_wind != -1 and no_wind - best < 2:
            return False
    if kind in ("patrol", "mixed"):
        if not env.enemies or any(has_route_without(env, set(enemy["track"]))
                                  for enemy in env.enemies):
            return False
        no_patrol = read_map({**spec, "enemies": []}).optimal_length()
        if no_patrol >= best:
            return False
    return True


def legend_can_race(env, agent):
    work = copy_env(env)
    for _ in range(75):
        _, _, done, info = work.step(agent.act(work.get_state()))
        if done:
            return info["event"] == "goal" and work.steps > env.optimal_length()
    return False


def generate_course(run_seed, stage, agent, previous_map=None):
    """Return (kind, arena, map) for a 1-based stage in a run."""
    rng = random.Random(f"{run_seed}:{stage}")
    kind = STAGE_KINDS[(stage - 1) % len(STAGE_KINDS)]
    boss = kind == "boss"
    tier = (stage - 1) // len(STAGE_KINDS)
    hazard = BOSS_KINDS[min(len(BOSS_KINDS) - 1, tier)] if boss else kind
    zone = STAGE_ZONES[hazard]
    templates = [build() for build in TEMPLATES[hazard]]
    extra_walls = min(6, 2 + stage // len(STAGE_KINDS))

    def acceptable(env):
        return (env.map_spec() != previous_map and has_trick(env, hazard)
                and (not boss or legend_can_race(env, agent)))

    for attempt in range(96 if boss else 40):
        walls = max(0, extra_walls - attempt // 24)
        env = varied_map(rng.choice(templates), hazard, rng, walls)
        if acceptable(env):
            return kind, zone, env
    for seed in FALLBACK_SEEDS[hazard]:
        template = templates[seed % len(templates)]
        env = varied_map(template, hazard, random.Random(seed), 2)
        if acceptable(env):
            return kind, zone, env
    raise ValueError("No course with a valid route could be generated.")

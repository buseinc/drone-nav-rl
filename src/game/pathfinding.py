"""Route helpers: optimal route for scoring, perfect autopilot for demos."""

from collections import deque

from src.drone_env_v4 import HOVER, N_ACTIONS


def best_action(env):
    """First action of a fastest route from the drone's current cell and
    tick, considering walls, wind and patrol timing (breadth-first search
    over (cell, tick mod patrol period)). Used by the guide's demos."""
    period = env._period()
    seen = {(env.position, env.t % period)}
    queue = deque()
    for a in range(N_ACTIONS):
        path, event = env.transition(env.position, a, env.t)
        if event == "crash":
            continue
        if event == "goal":
            return a
        key = (path[-1], (env.t + 1) % period)
        if key not in seen:
            seen.add(key)
            queue.append((path[-1], env.t + 1, a))
    while queue:
        pos, t, first = queue.popleft()
        for a in range(N_ACTIONS):
            path, event = env.transition(pos, a, t)
            if event == "crash":
                continue
            if event == "goal":
                return first
            key = (path[-1], (t + 1) % period)
            if key not in seen:
                seen.add(key)
                queue.append((path[-1], t + 1, first))
    return HOVER

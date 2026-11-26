"""DroneEnvV4 - V3 plus hazards: wind zones and patrolling enemy drones.

New compared to V3:
  * Action 4 = HOVER (stay in place for one tick). Needed to let an enemy
    pass by.
  * The world runs in ticks: every step() is one tick, enemies move one
    cell per tick no matter what the drone does.
  * Wind: a wind cell pushes the drone one cell in its direction after it
    arrives (or hovers) there. Consecutive wind cells chain the push, so a
    wind stream works like a conveyor belt. Pushing into a wall just stops.
  * Enemies: patrol back and forth on a straight track. Touching one (or
    swapping places with one) is a crash.

Observation (7x7 window around the drone, 6 channels + goal features):
    walls, visited, wind_row, wind_col, enemy_now, enemy_next
enemy_next tells where every enemy will be after this tick. Collisions are
checked against those positions, so with this channel the drone has all
the information it needs (the problem stays Markov).
"""

import math
from collections import deque

import numpy as np

MOVES = [(-1, 0), (1, 0), (0, -1), (0, 1), (0, 0)]  # Up Down Left Right Hover
HOVER = 4
N_ACTIONS = 5
DIRS = MOVES[:4]

GOAL_REWARD = 10.0
CRASH_REWARD = -10.0
STEP_REWARD = -0.2
PROGRESS_WEIGHT = 1.0
# Ending a tick on a cell you already visited (going back and forth, or
# hovering) costs a little extra. Without it the first V4 agent learned to
# hover or oscillate "safely" instead of flying to the goal.
REVISIT_PENALTY = 0.3
MAX_PUSH = 8


class DroneEnvV4:
    VIEW = 7
    CHANNELS = ["walls", "visited", "wind_row", "wind_col",
                "enemy_now", "enemy_next"]

    def __init__(self, grid_size=10, obstacle_count=15, seed=42,
                 max_steps=150, wind_streams=0, enemy_count=0):
        self.grid_size = grid_size
        self.obstacle_count = obstacle_count
        self.wind_streams = wind_streams
        self.enemy_count = enemy_count
        self.max_start_goal_dist = None
        self.max_steps = max_steps
        self.rng = np.random.default_rng(seed)
        self.reset()

    @property
    def state_size(self):
        return len(self.CHANNELS) * self.VIEW * self.VIEW + 4

    # ================= map generation =================

    def _free_cells(self, exclude=()):
        n = self.grid_size
        return [(r, c) for r in range(n) for c in range(n)
                if (r, c) not in self.obstacles and (r, c) not in exclude]

    def _pick(self, cells):
        return cells[int(self.rng.integers(len(cells)))]

    def _bfs_from_goal(self):
        n = self.grid_size
        dist = np.full((n, n), -1, dtype=np.int32)
        dist[self.goal] = 0
        queue = deque([self.goal])
        while queue:
            r, c = queue.popleft()
            for dr, dc in DIRS:
                nr, nc = r + dr, c + dc
                if (0 <= nr < n and 0 <= nc < n
                        and (nr, nc) not in self.obstacles
                        and dist[nr, nc] == -1):
                    dist[nr, nc] = dist[r, c] + 1
                    queue.append((nr, nc))
        return dist

    def _make_wind(self):
        self.wind = {}
        protected = {self.start, self.goal}
        for _ in range(self.wind_streams):
            for _ in range(30):
                cell = self._pick(self._free_cells(protected))
                d = DIRS[int(self.rng.integers(4))]
                length = int(self.rng.integers(3, 6))
                cells, cur = [], cell
                while (len(cells) < length and not self.is_blocked(cur)
                       and cur not in protected and cur not in self.wind):
                    cells.append(cur)
                    cur = (cur[0] + d[0], cur[1] + d[1])
                if len(cells) >= 3:
                    for c in cells:
                        self.wind[c] = d
                    break

    def _make_enemies(self):
        self.enemies = []
        sr, sc = self.start
        protected = {self.start, self.goal,
                     (sr - 1, sc), (sr + 1, sc), (sr, sc - 1), (sr, sc + 1)}
        used = set()
        for _ in range(self.enemy_count):
            for _ in range(40):
                cell = self._pick(self._free_cells(protected | used))
                d = DIRS[int(self.rng.integers(2)) * 2 + 1]  # Down or Right
                length = int(self.rng.integers(3, 7))
                track, cur = [], cell
                while (len(track) < length and not self.is_blocked(cur)
                       and cur not in protected and cur not in used):
                    track.append(cur)
                    cur = (cur[0] + d[0], cur[1] + d[1])
                if len(track) >= 3:
                    period = 2 * (len(track) - 1)
                    self.enemies.append({
                        "track": track,
                        "phase": int(self.rng.integers(period)),
                    })
                    used.update(track)
                    break

    def reset(self):
        n = self.grid_size
        while True:
            cells = self.rng.choice(n * n, size=2, replace=False)
            self.start = (int(cells[0] // n), int(cells[0] % n))
            self.goal = (int(cells[1] // n), int(cells[1] % n))
            self.obstacles = set()
            while len(self.obstacles) < self.obstacle_count:
                cell = int(self.rng.integers(n * n))
                pos = (cell // n, cell % n)
                if pos not in (self.start, self.goal):
                    self.obstacles.add(pos)

            self.dist_map = self._bfs_from_goal()
            d = self.dist_map[self.start]
            if d == -1:
                continue
            if (self.max_start_goal_dist is not None
                    and d > self.max_start_goal_dist):
                continue

            self._make_wind()
            self._make_enemies()
            self._restart()
            if self.optimal_route() is not None:   # still solvable?
                return self.get_state()

    def set_map(self, start, goal, obstacles, wind=None, enemies=None):
        """Load a given map (the game uses this to copy a map)."""
        self.start, self.goal = tuple(start), tuple(goal)
        self.obstacles = set(map(tuple, obstacles))
        self.wind = dict(wind or {})
        self.enemies = [dict(e) for e in (enemies or [])]
        self.refresh_distances()
        return self._restart()

    def map_spec(self):
        return dict(start=self.start, goal=self.goal,
                    obstacles=set(self.obstacles), wind=dict(self.wind),
                    enemies=[dict(e) for e in self.enemies])

    def _restart(self):
        n = self.grid_size
        self.position = self.start
        self.steps = 0
        self.t = 0
        self.visits = np.zeros((n, n), dtype=np.float32)
        self.visits[self.start] = 1.0
        self.path = [self.start]
        self._optimal = None
        self._build_static()
        return self.get_state()

    def refresh_distances(self):
        """Call after editing obstacles, wind or the goal by hand."""
        self.dist_map = self._bfs_from_goal()
        self._optimal = None
        if hasattr(self, "visits"):
            self._build_static()

    # ================= dynamics =================

    def is_blocked(self, pos):
        n = self.grid_size
        return (not (0 <= pos[0] < n and 0 <= pos[1] < n)
                or pos in self.obstacles)

    def enemy_pos(self, enemy, t):
        track = enemy["track"]
        period = 2 * (len(track) - 1)
        k = (enemy["phase"] + t) % period
        return track[k if k < len(track) else period - k]

    def enemy_cells(self, t):
        return {self.enemy_pos(e, t) for e in self.enemies}

    def transition(self, pos, action, t, *, follow_action=None, use_wind=True):
        """Pure function: where does `action` at tick t take the drone?

        Returns (cells_visited_this_tick, event). For a wall crash the list
        is empty. Used by step() and by the optimal-route search.
        """
        dr, dc = MOVES[action]
        new = (pos[0] + dr, pos[1] + dc)
        if action != HOVER and self.is_blocked(new):
            return [], "crash"

        path = [new]
        cur = new
        if follow_action is not None and cur != self.goal and (not use_wind or cur not in self.wind):
            next_dr, next_dc = MOVES[follow_action]
            nxt = (cur[0] + next_dr, cur[1] + next_dc)
            if self.is_blocked(nxt):
                return path, "crash"
            cur = nxt
            path.append(cur)
        seen = {cur}
        for _ in range(MAX_PUSH if use_wind else 0):  # wind chain
            if cur == self.goal or cur not in self.wind:
                break
            w = self.wind[cur]
            nxt = (cur[0] + w[0], cur[1] + w[1])
            if self.is_blocked(nxt) or nxt in seen:
                break
            cur = nxt
            path.append(cur)
            seen.add(cur)

        if self.enemies:
            now, nxt = self.enemy_cells(t), self.enemy_cells(t + 1)
            if action != HOVER and new in now and pos in nxt:  # swap
                return path[:1], "crash"
            for i, cell in enumerate(path):
                if cell in nxt:
                    return path[:i + 1], "crash"

        return path, ("goal" if cur == self.goal else "move")

    def would_crash(self, action):
        return self.transition(self.position, action, self.t)[1] == "crash"

    def step(self, action):
        """Returns (state, reward, done, info). info: event + path."""
        self.steps += 1
        path, event = self.transition(self.position, action, self.t)
        self.t += 1
        info = {"event": event, "path": path, "action": action}

        if event == "crash":
            return self.get_state(), CRASH_REWARD, True, info

        old_d = self.get_distance()
        for cell in path:
            self.visits[cell] += 1.0
        self.path.extend(path)
        self.position = path[-1]

        if event == "goal":
            return self.get_state(), GOAL_REWARD, True, info

        reward = STEP_REWARD + PROGRESS_WEIGHT * (old_d - self.get_distance())
        if self.visits[self.position] > 1:
            reward -= REVISIT_PENALTY
        if self.steps >= self.max_steps:
            info["event"] = "timeout"
            return self.get_state(), reward, True, info
        return self.get_state(), reward, False, info

    # ================= optimal route =================

    def _period(self):
        p = 1
        for e in self.enemies:
            q = 2 * (len(e["track"]) - 1)
            p = p * q // math.gcd(p, q)
        return p

    def optimal_route(self):
        """Fewest ticks to the goal, considering wind and enemy timing.

        Breadth-first search over (cell, tick mod period). Returns
        (ticks, cells) or None if the goal cannot be reached.
        """
        if self._optimal is not None:
            return self._optimal
        period = self._period()
        startk = (self.start, 0)
        parent = {startk: None}
        queue = deque([(self.start, 0, 0)])
        while queue:
            pos, t, depth = queue.popleft()
            if depth >= self.max_steps:
                continue
            for a in range(N_ACTIONS):
                path, event = self.transition(pos, a, t)
                if event == "crash":
                    continue
                key = (path[-1], (t + 1) % period)
                if key in parent:
                    continue
                parent[key] = ((pos, t % period), path)
                if event == "goal":
                    cells, k = [], key
                    while parent[k] is not None:
                        prev, seg = parent[k]
                        cells = seg + cells
                        k = prev
                    self._optimal = (depth + 1, [self.start] + cells)
                    return self._optimal
                queue.append((path[-1], t + 1, depth + 1))
        return None

    def optimal_length(self):
        route = self.optimal_route()
        return route[0] if route else -1

    def get_distance(self, pos=None):
        pos = self.position if pos is None else pos
        return int(self.dist_map[pos])

    # ================= observation =================

    def _build_static(self):
        """Padded wall / wind grids, so a window is a simple slice."""
        n, h = self.grid_size, self.VIEW // 2
        walls = np.ones((n + 2 * h, n + 2 * h), dtype=np.float32)
        walls[h:h + n, h:h + n] = 0.0
        for r, c in self.obstacles:
            walls[r + h, c + h] = 1.0
        wind = np.zeros((2, n + 2 * h, n + 2 * h), dtype=np.float32)
        for (r, c), (dr, dc) in self.wind.items():
            wind[0, r + h, c + h] = dr
            wind[1, r + h, c + h] = dc
        self._walls_pad = walls
        self._wind_pad = wind

    def _pad(self, grid):
        h = self.VIEW // 2
        return np.pad(grid, h)

    def get_state(self, position=None, visits=None, t=None):
        """Observation for `position` at tick `t` (default: the drone now).

        The optional arguments let the game ask "what would the AI do if it
        were on this cell?" for the policy heat-map.
        """
        pos = self.position if position is None else position
        visits = self.visits if visits is None else visits
        t = self.t if t is None else t
        n, v = self.grid_size, self.VIEW
        r, c = pos

        def window(padded):
            return padded[r:r + v, c:c + v]

        enemy_now = np.zeros((n, n), dtype=np.float32)
        enemy_next = np.zeros((n, n), dtype=np.float32)
        for e in self.enemies:
            enemy_now[self.enemy_pos(e, t)] = 1.0
            enemy_next[self.enemy_pos(e, t + 1)] = 1.0

        channels = [
            window(self._walls_pad),
            window(self._pad(np.minimum(visits, 3.0) / 3.0)),
            window(self._wind_pad[0]),
            window(self._wind_pad[1]),
            window(self._pad(enemy_now)),
            window(self._pad(enemy_next)),
        ]
        dr, dc = self.goal[0] - r, self.goal[1] - c
        goal = np.array([np.sign(dr), np.sign(dc), dr / (n - 1), dc / (n - 1)],
                        dtype=np.float32)
        return np.concatenate([ch.ravel() for ch in channels] + [goal]) \
            .astype(np.float32)

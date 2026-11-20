"""DroneEnvV3 - generalizes to unseen maps.

Changes compared to V2:
  1. Egocentric observation: the drone only sees a VIEW x VIEW window
     around itself (outside the map counts as a wall), plus the direction
     to the goal. The same rule ("wall on my left, goal up-right") applies
     on every map, so the network does not have to memorize 100 cells.
  2. Visit memory: a second window tells the drone which nearby cells it
     already visited. This breaks the endless back-and-forth loops that
     caused most V2 timeouts.
  3. BFS distance: get_distance() returns the real shortest-path distance
     to the goal (walking around obstacles), used for reward shaping and
     for the "optimal path" score in the game.
  4. Curriculum: obstacle_count and max_start_goal_dist can be changed
     between episodes so training starts easy and gets harder.
"""

from collections import deque

import numpy as np

MOVES = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # Up, Down, Left, Right

# Rewards
GOAL_REWARD = 10.0
CRASH_REWARD = -10.0
STEP_REWARD = -0.2
PROGRESS_WEIGHT = 1.0   # bonus per BFS step closer to the goal


class DroneEnvV3:
    VIEW = 7  # odd number, drone sits in the center

    def __init__(self, grid_size=10, obstacle_count=15, seed=42,
                 max_steps=100):
        self.grid_size = grid_size
        self.obstacle_count = obstacle_count
        self.max_start_goal_dist = None  # None = no limit
        self.max_steps = max_steps
        self.rng = np.random.default_rng(seed)
        self.reset()

    @property
    def state_size(self):
        return 2 * self.VIEW * self.VIEW + 4

    # ---------- map generation ----------

    def _bfs_from_goal(self):
        """Shortest-path distance from every free cell to the goal."""
        n = self.grid_size
        dist = np.full((n, n), -1, dtype=np.int32)
        dist[self.goal] = 0
        queue = deque([self.goal])

        while queue:
            r, c = queue.popleft()
            for dr, dc in MOVES:
                nr, nc = r + dr, c + dc
                if (0 <= nr < n and 0 <= nc < n
                        and (nr, nc) not in self.obstacles
                        and dist[nr, nc] == -1):
                    dist[nr, nc] = dist[r, c] + 1
                    queue.append((nr, nc))

        return dist

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
                continue  # goal unreachable
            if (self.max_start_goal_dist is not None
                    and d > self.max_start_goal_dist):
                continue
            break

        self.position = self.start
        self.steps = 0
        self.visits = np.zeros((n, n), dtype=np.float32)
        self.visits[self.start] = 1.0
        self.path = [self.start]
        return self.get_state()

    def set_map(self, start, goal, obstacles):
        """Load a hand-made map (used by the game / map editor)."""
        n = self.grid_size
        self.start, self.goal = tuple(start), tuple(goal)
        self.obstacles = set(map(tuple, obstacles))
        self.dist_map = self._bfs_from_goal()
        self.position = self.start
        self.steps = 0
        self.visits = np.zeros((n, n), dtype=np.float32)
        self.visits[self.start] = 1.0
        self.path = [self.start]
        return self.get_state()

    def refresh_distances(self):
        """Call after editing obstacles or the goal by hand."""
        self.dist_map = self._bfs_from_goal()

    # ---------- helpers ----------

    def get_distance(self, pos=None):
        """Real shortest-path length to the goal (-1 if unreachable)."""
        pos = self.position if pos is None else pos
        return int(self.dist_map[pos])

    def optimal_length(self):
        return self.get_distance(self.start)

    def is_blocked(self, pos):
        n = self.grid_size
        return (not (0 <= pos[0] < n and 0 <= pos[1] < n)
                or pos in self.obstacles)

    # ---------- observation ----------

    def get_state(self, position=None, visits=None):
        """Observation for `position` (defaults to the drone).

        The optional arguments let the game ask "what would the AI do if
        it were on this cell?" for the policy heat-map.
        """
        pos = self.position if position is None else position
        visits = self.visits if visits is None else visits
        n, v = self.grid_size, self.VIEW
        half = v // 2

        walls = np.ones((v, v), dtype=np.float32)    # outside = wall
        visited = np.zeros((v, v), dtype=np.float32)

        for i in range(v):
            for j in range(v):
                r, c = pos[0] - half + i, pos[1] - half + j
                if 0 <= r < n and 0 <= c < n:
                    walls[i, j] = 1.0 if (r, c) in self.obstacles else 0.0
                    visited[i, j] = min(visits[r, c], 3.0) / 3.0

        # Goal direction: the sign gives a crisp "goal is up/down/left/right"
        # signal, the scaled value tells how far away it is.
        dr = self.goal[0] - pos[0]
        dc = self.goal[1] - pos[1]
        goal_dir = np.array([
            np.sign(dr), np.sign(dc), dr / (n - 1), dc / (n - 1),
        ], dtype=np.float32)

        return np.concatenate([walls.ravel(), visited.ravel(), goal_dir])

    # ---------- dynamics ----------

    def step(self, action):
        """Returns (state, reward, done, info).

        info["event"] is one of: "move", "goal", "crash", "timeout".
        """
        dr, dc = MOVES[action]
        new_pos = (self.position[0] + dr, self.position[1] + dc)
        self.steps += 1

        if self.is_blocked(new_pos):
            return self.get_state(), CRASH_REWARD, True, {"event": "crash"}

        old_d = self.get_distance()
        self.position = new_pos
        self.visits[new_pos] += 1.0
        self.path.append(new_pos)

        if new_pos == self.goal:
            return self.get_state(), GOAL_REWARD, True, {"event": "goal"}

        reward = STEP_REWARD + PROGRESS_WEIGHT * (old_d - self.get_distance())

        if self.steps >= self.max_steps:
            return self.get_state(), reward, True, {"event": "timeout"}

        return self.get_state(), reward, False, {"event": "move"}

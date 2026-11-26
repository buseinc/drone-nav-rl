import numpy as np
from collections import deque


class DroneEnvV2:
    def __init__(self, grid_size=10, obstacle_count=15, seed=42):
        self.grid_size = grid_size
        self.obstacle_count = obstacle_count
        self.max_steps = 150
        self.rng = np.random.default_rng(seed)

        self.reset()

    def _has_path(self):
        queue = deque([self.start])
        visited = {self.start}

        while queue:
            row, col = queue.popleft()

            if (row, col) == self.goal:
                return True

            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                pos = (row + dr, col + dc)

                if (
                    0 <= pos[0] < self.grid_size
                    and 0 <= pos[1] < self.grid_size
                    and pos not in self.obstacles
                    and pos not in visited
                ):
                    visited.add(pos)
                    queue.append(pos)

        return False

    def reset(self):
        n = self.grid_size

        # Random start and goal
        cells = self.rng.choice(n * n, size=2, replace=False)

        self.start = (int(cells[0] // n), int(cells[0] % n))
        self.goal = (int(cells[1] // n), int(cells[1] % n))

        # Generate a map where the goal is reachable
        while True:
            self.obstacles = set()

            while len(self.obstacles) < self.obstacle_count:
                cell = int(self.rng.integers(n * n))
                pos = (cell // n, cell % n)

                if pos not in (self.start, self.goal):
                    self.obstacles.add(pos)

            if self._has_path():
                break

        self.position = self.start
        self.steps = 0

        return self.get_state()

    def get_state(self):
        n = self.grid_size

        # 0 = empty, 1 = obstacle
        grid = np.zeros((n, n), dtype=np.float32)

        for row, col in self.obstacles:
            grid[row, col] = 1.0

        # Flatten the map and add coordinates
        grid_features = grid.flatten()

        position = np.array(self.position, dtype=np.float32) / (n - 1)
        goal = np.array(self.goal, dtype=np.float32) / (n - 1)

        return np.concatenate([
            grid_features,
            position,
            goal
        ]).astype(np.float32)

    def step(self, action):
        moves = [
            (-1, 0),  # Up
            (1, 0),   # Down
            (0, -1),  # Left
            (0, 1)    # Right
        ]

        dr, dc = moves[action]

        new_pos = (
            self.position[0] + dr,
            self.position[1] + dc
        )

        self.steps += 1

        # Collision
        if (
            not 0 <= new_pos[0] < self.grid_size
            or not 0 <= new_pos[1] < self.grid_size
            or new_pos in self.obstacles
        ):
            return self.get_state(), -100, True

        self.position = new_pos

        # Goal reached
        if self.position == self.goal:
            return self.get_state(), 100, True

        # Time limit
        if self.steps >= self.max_steps:
            return self.get_state(), -1, True

        return self.get_state(), -1, False
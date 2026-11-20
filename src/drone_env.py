import numpy as np


class DroneEnv:
    def __init__(self):
        self.grid_size = 6

        self.start = (0, 0)
        self.goal = (5, 5)

        self.obstacles = {
            (1, 1),
            (1, 2),
            (2, 2),
            (3, 2),
            (4, 4)
        }

        self.max_steps = 60
        self.reset()

    def reset(self):
        self.position = self.start
        self.steps = 0
        return self.position

    def step(self, action):
        # 0: Up, 1: Down, 2: Left, 3: Right
        moves = [
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1)
        ]

        dx, dy = moves[action]

        new_position = (
            self.position[0] + dx,
            self.position[1] + dy
        )

        self.steps += 1

        # Check boundaries and obstacles
        if (
            not 0 <= new_position[0] < self.grid_size
            or not 0 <= new_position[1] < self.grid_size
            or new_position in self.obstacles
        ):
            return self.position, -100, True

        self.position = new_position

        if self.position == self.goal:
            return self.position, 100, True

        if self.steps >= self.max_steps:
            return self.position, -1, True

        return self.position, -1, False
"""Solo-flight powers. The race and training controllers keep standard actions."""

from src.drone_env_v4 import DroneEnvV4, HOVER, MOVES


class EquippedEnvironment(DroneEnvV4):
    def __init__(self, base, require_wind):
        self.power = None
        self.follow_action = None
        self.rode_wind = not require_wind or not base.wind
        super().__init__(seed=0, obstacle_count=0, grid_size=base.grid_size,
                         max_steps=base.max_steps)
        self.set_map(**base.map_spec())

    def transition(self, pos, action, tick):
        return super().transition(pos, action, tick, follow_action=self.follow_action,
                                  use_wind=self.power != "anchor")

    def powered_action(self, name, action, heading):
        row, col = self.position
        dr, dc = MOVES[action]
        if name == "needle" and action != HOVER:
            return action, action
        if name == "anchor" and self.rode_wind:
            if (row + dr, col + dc) in self.wind:
                return action, None
        if name == "bumble" and action == HOVER:
            previous = next((cell for cell in reversed(self.path) if cell != self.position), None)
            if previous:
                delta = (previous[0] - row, previous[1] - col)
                if delta in MOVES:
                    return MOVES.index(delta), None
        if name == "jelly" and heading is not None and action != HOVER:
            heading_dr, heading_dc = MOVES[heading]
            if dr * heading_dr + dc * heading_dc == 0:
                return heading, action
        return None

    def wind_forecasts(self):
        row, col = self.position
        for action, (dr, dc) in enumerate(MOVES[:-1]):
            if (row + dr, col + dc) not in self.wind:
                continue
            path, event = self.transition(self.position, action, self.t)
            if event != "crash" and len(path) > 1:
                yield path

    def step(self, action):
        try:
            state, reward, done, info = super().step(action)
            if info["event"] != "crash" and self.power != "anchor":
                self.rode_wind |= any(cell in self.wind for cell in info["path"][:-1])
            return state, reward, done, info
        finally:
            self.power = None
            self.follow_action = None

"""Animates a drone between ticks.

The environment is step-based: one step() = one tick. The controller calls
step() and then animates the drone along the cells it visited during that
tick (one cell for a normal move, several when wind pushes it, none for a
hover), so the drone glides instead of jumping. The final event ("goal",
"crash", "timeout") is reported when the animation ends.
"""

from src.drone_env_v4 import HOVER, MOVES

MOVE_MS = 230


def ease(t):
    """Smooth start and stop (ease-in-out)."""
    return t * t * (3 - 2 * t)


class DroneController:
    def __init__(self, env, move_ms=MOVE_MS, linear=False):
        """linear=True: constant speed, so consecutive moves flow into each
        other without slowing down at every cell (used in real-time modes).
        """
        self.env = env
        self.move_ms = move_ms
        self.linear = linear
        self.reset()

    def reset(self):
        p = tuple(map(float, self.env.position))
        self.points = [p, p]
        self.t = 1.0
        self.pending = None   # event that happens when the animation ends
        self.result = None    # final event, once the drone has landed
        self.last_action = None

    @property
    def busy(self):
        return self.t < 1.0

    @property
    def finished(self):
        return self.pending is not None or self.result is not None

    @property
    def can_move(self):
        return not self.busy and not self.finished

    def move(self, action):
        """Perform one env step and start animating it."""
        if self.finished:
            return False
        old = self.env.position
        _, _, done, info = self.env.step(action)
        path = info.get("path", [self.env.position])
        if info["event"] == "crash" and not path:
            # flew into a wall: go half-way into it, then explode
            dr, dc = MOVES[action]
            path = [(old[0] + dr * 0.45, old[1] + dc * 0.45)]
        if action == HOVER and len(path) == 1:
            path = [old]
        self.points = [tuple(map(float, old))] + \
            [tuple(map(float, p)) for p in path]
        self.t = 0.0
        self.last_action = action
        self.pending = info["event"] if done else None
        return True

    def update(self, dt):
        """Advance the animation. Returns the final event when it lands."""
        if self.t < 1.0:
            self.t = min(1.0, self.t + dt / self.move_ms)
            if self.t >= 1.0:
                return self._land()
        return None

    def sync(self, remaining_ms):
        """Drive the animation from the world clock instead of frame time:
        the current move must end exactly when the tick ends, in
        `remaining_ms`. This avoids the tiny stop at every tick boundary
        that made movement look jerky."""
        if self.t < 1.0:
            self.t = max(0.0, min(0.999, 1 - remaining_ms / self.move_ms))

    def complete(self):
        """Jump to the end of the current move (start of a new tick)."""
        if self.t < 1.0:
            self.t = 1.0
            return self._land()
        return None

    def _land(self):
        if self.pending:
            self.result, self.pending = self.pending, None
            return self.result
        return None

    def resume(self):
        """Allow flying again after a finished episode (AI Vision)."""
        self.result = self.pending = None

    def pos(self):
        """Current (row, col) as floats, following the tick's path."""
        pts = self.points
        n = len(pts) - 1
        if n <= 0:
            return pts[0]
        k = (self.t if self.linear else ease(self.t)) * n
        i = min(int(k), n - 1)
        f = k - i
        a, b = pts[i], pts[i + 1]
        return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)

"""Hand-built routes for SkyRush's Parkurlar mode."""

from dataclasses import dataclass
from math import lcm

from src.drone_env_v4 import DroneEnvV4


@dataclass(frozen=True)
class Gate:
    cell: tuple
    period: int
    first: int
    duration: int

    def open_at(self, tick):
        return (tick - self.first) % self.period < self.duration

    def opens_in(self, tick):
        return (self.first - tick) % self.period

    def closes_in(self, tick):
        return (self.first + self.duration - tick) % self.period


@dataclass(frozen=True)
class Course:
    name: str
    setting: str
    accent: tuple
    ground: tuple
    lane: tuple
    shortcut: tuple
    start: tuple
    goal: tuple
    safe_path: tuple
    fast_path: tuple
    winds: tuple = ()
    patrol: tuple = ()
    gate: Gate = None

    @property
    def safe_cells(self):
        return route_cells(self.safe_path)

    @property
    def fast_cells(self):
        return route_cells(self.fast_path)


def route_cells(points):
    cells = {points[0]}
    for (r, c), (end_r, end_c) in zip(points, points[1:]):
        dr = (end_r > r) - (end_r < r)
        dc = (end_c > c) - (end_c < c)
        while (r, c) != (end_r, end_c):
            r, c = r + dr, c + dc
            cells.add((r, c))
    return cells


NEON = Course(
    name="Neon Rooftops", setting="Midnight",
    accent=(243, 124, 204), ground=(24, 21, 48),
    lane=(47, 45, 73), shortcut=(101, 220, 230),
    start=(8, 1), goal=(3, 10),
    safe_path=((8, 1), (6, 1), (6, 3), (9, 3), (9, 10), (3, 10)),
    fast_path=((6, 3), (6, 10)),
    winds=tuple(((6, c), (0, 1)) for c in range(4, 8)),
    gate=Gate(cell=(6, 6), period=18, first=6, duration=4),
)

HARBOR = Course(
    name="Crane Harbor", setting="Sunset",
    accent=(255, 188, 113), ground=(20, 51, 63),
    lane=(57, 76, 85), shortcut=(255, 174, 91),
    start=(8, 1), goal=(3, 10),
    safe_path=((8, 1), (8, 4), (10, 4), (10, 10), (3, 10)),
    fast_path=((8, 4), (6, 4), (6, 8), (3, 8), (3, 10)),
    patrol=((4, 6), (5, 6), (6, 6), (7, 6), (8, 6)),
)

COURSES = (NEON, HARBOR)
GRID_SIZE = 12


class CourseEnvironment(DroneEnvV4):
    """Use the standard wind and patrol rules with an optional timed gate."""

    def __init__(self, course):
        self.course = course
        self.closed = None
        super().__init__(seed=0, obstacle_count=0, grid_size=GRID_SIZE)
        lanes = course.safe_cells | course.fast_cells
        obstacles = {(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)
                     if (r, c) not in lanes}
        enemies = [{"track": course.patrol, "phase": 3}] if course.patrol else []
        self.set_map(course.start, course.goal, obstacles, dict(course.winds), enemies)
        if course.gate:
            self.closed = DroneEnvV4(seed=0, obstacle_count=0, grid_size=GRID_SIZE)
            spec = self.map_spec()
            spec["obstacles"].add(course.gate.cell)
            self.closed.set_map(**spec)

    def transition(self, pos, action, t):
        if self.closed is None or self.course.gate.open_at(t):
            return super().transition(pos, action, t)
        path, event = self.closed.transition(pos, action, t)
        if self.course.gate.cell in path:
            return path, "crash"
        return path, event

    def get_state(self, position=None, visits=None, t=None):
        tick = self.t if t is None else t
        if self.closed is None or self.course.gate.open_at(tick):
            return super().get_state(position, visits, tick)
        return self.closed.get_state(
            self.position if position is None else position,
            self.visits if visits is None else visits, tick)

    def _period(self):
        period = super()._period()
        return lcm(period, self.course.gate.period) if self.closed is not None else period

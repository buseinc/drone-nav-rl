"""The pond crossing and duckling follow-the-leader rules."""

from collections import deque

from games.skyrush.farm import add
from src.drone_env_v4 import DIRS

ROWS, COLS = 12, 18
NEST = (8, 2)
DUCKLINGS = ((4, 13), (7, 13), (9, 16))
RIVER = frozenset((r, c) for r in range(ROWS) for c in range(7, 11))
BRIDGE = frozenset((2, c) for c in range(7, 11))
STONES = frozenset((8, c) for c in range(7, 11))
BUSHES = frozenset({(1, 3), (1, 13), (3, 5), (4, 4), (4, 11), (5, 4), (5, 15),
                    (6, 6), (6, 12), (7, 5), (7, 15), (9, 4), (9, 12), (10, 15)})
BLOCKED = (RIVER - BRIDGE - STONES) | BUSHES
CALM_MS, SURGE_MS, WARN_MS = 4600, 2200, 850
CYCLE_MS = CALM_MS + SURGE_MS
ORCA_LEG_MS = 3750
SPOTLIGHT_RADIUS = 0.82


def distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def walkable(cell):
    r, c = cell
    return 0 <= r < ROWS and 0 <= c < COLS and cell not in BLOCKED


def follow_step(start, target):
    if distance(start, target) <= 1:
        return target
    seen = {start}
    queue = deque([(start, start)])
    while queue:
        cell, first = queue.popleft()
        if cell == target:
            return first
        for direction in DIRS:
            neighbor = add(cell, direction)
            if neighbor not in seen and walkable(neighbor):
                seen.add(neighbor)
                queue.append((neighbor, neighbor if cell == start else first))
    return start


class DuckRescue:
    def __init__(self):
        self.leader = NEST
        self.positions = dict(enumerate(DUCKLINGS))
        self.last_bank = self.positions.copy()
        self.followers = []
        self.rescued = set()
        self.elapsed = 0
        self.detached = 0
        self.detached_by = None

    @property
    def finished(self):
        return len(self.rescued) == len(DUCKLINGS)

    @property
    def tide(self):
        phase = self.elapsed % CYCLE_MS
        if phase >= CALM_MS:
            return "surge"
        if phase >= CALM_MS - WARN_MS:
            return "warning"
        return "calm"

    @property
    def orca_row(self):
        progress = self.elapsed % (2 * ORCA_LEG_MS) / ORCA_LEG_MS
        return 2 + 8 * (1 - abs(progress - 1))

    @property
    def scan_right(self):
        return 13 if self.elapsed % (2 * ORCA_LEG_MS) >= ORCA_LEG_MS else 10

    def in_spotlight(self, cell):
        row, col = cell
        return 7 <= col <= self.scan_right and abs(row - self.orca_row) <= SPOTLIGHT_RADIUS

    def advance(self, ms):
        self.elapsed += ms
        self.check_crossing()

    def check_crossing(self):
        surge = self.tide == "surge"
        for index, duck in enumerate(self.followers):
            cell = self.positions[duck]
            spotted = self.in_spotlight(cell)
            if spotted or (surge and cell in STONES):
                self.release_tail(index, "orca" if spotted else "tide")
                return

    def call(self):
        nearby = [i for i, cell in self.positions.items()
                  if i not in self.followers and distance(self.leader, cell) <= 1]
        self.followers.extend(nearby)
        return bool(nearby)

    def release_tail(self, index, reason):
        for duck in self.followers[index:]:
            cell = self.positions[duck]
            if cell in RIVER or (reason == "orca" and self.in_spotlight(cell)):
                row, col = self.last_bank[duck]
                # Column 14 is clear all along the far bank, outside the wider sweep.
                if reason == "orca" and 11 <= col <= self.scan_right:
                    col = 14
                self.positions[duck] = self.last_bank[duck] = (row, col)
        self.detached += len(self.followers) - index
        self.detached_by = reason
        del self.followers[index:]

    def move(self, direction):
        cell = add(self.leader, direction)
        if not walkable(cell):
            return False

        target = self.leader
        self.leader = cell
        for index, duck in enumerate(self.followers):
            previous = self.positions[duck]
            destination = follow_step(previous, target)
            if destination in STONES and self.tide == "surge":
                self.release_tail(index, "tide")
                break
            self.positions[duck] = destination
            if destination not in RIVER:
                self.last_bank[duck] = destination
            target = previous

        self.check_crossing()
        if cell == NEST:
            for duck in self.followers:
                del self.positions[duck]
                del self.last_bank[duck]
            self.rescued.update(self.followers)
            self.followers.clear()
        return True

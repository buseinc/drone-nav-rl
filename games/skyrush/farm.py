"""Grid rules for the farm escape and its line-of-sight pursuer."""

from collections import deque

from src.drone_env_v4 import DIRS

ROWS, COLS = 12, 18
COOP = (9, 2)
CORN = frozenset({(2, 2), (4, 6), (2, 10), (4, 15), (7, 3), (9, 14)})
HEDGES = frozenset({(2, 5), (3, 5), (6, 8), (7, 8), (6, 13), (8, 13), (9, 16)})
FENCES = frozenset(
    {(3, c) for c in range(6, 11)} | {(6, c) for c in range(2, 7)}
    | {(8, c) for c in range(9, 13)} | {(r, 12) for r in range(2, 5)}
)
POND = frozenset({(1, 14), (1, 15), (2, 14), (2, 15), (2, 16), (3, 16)})
TREES = frozenset({(1, 1), (1, 9), (4, 2), (4, 9), (5, 15), (9, 8), (10, 4), (10, 16)})
SOLIDS = FENCES | POND | TREES
PATROL = ((2, 13), (1, 6), (5, 4), (8, 6), (10, 13), (5, 16))
SIGHT = 7


def add(cell, direction):
    return cell[0] + direction[0], cell[1] + direction[1]


def flyable(cell):
    r, c = cell
    return 0 <= r < ROWS and 0 <= c < COLS and cell not in SOLIDS


def next_step(start, goal):
    """Return the first walkable step on a shortest path."""
    seen = {start}
    queue = deque([(start, start)])
    while queue:
        cell, first = queue.popleft()
        if cell == goal:
            return first
        for direction in DIRS:
            neighbor = add(cell, direction)
            if neighbor not in seen and flyable(neighbor):
                seen.add(neighbor)
                queue.append((neighbor, neighbor if cell == start else first))
    return start


def visible(origin, target, facing):
    dr, dc = target[0] - origin[0], target[1] - origin[1]
    distance = abs(dr) + abs(dc)
    if distance <= 1:
        return True
    if dr * dr + dc * dc > SIGHT * SIGHT:
        return False
    forward = dr * facing[0] + dc * facing[1]
    sideways = abs(dr * facing[1] - dc * facing[0])
    if forward <= 0 or 3 * sideways > 5 * forward:
        return False
    if target in HEDGES and distance > 2:
        return False

    # Sample between tile centers and block gaps through two touching corners.
    span = max(abs(dr), abs(dc)) * 4
    previous = origin
    for i in range(1, span):
        r, c = round(origin[0] + dr * i / span), round(origin[1] + dc * i / span)
        if (r, c) in SOLIDS:
            return False
        if r != previous[0] and c != previous[1]:
            if (r, previous[1]) in SOLIDS and (previous[0], c) in SOLIDS:
                return False
        previous = (r, c)
    return True


class Farm:
    def __init__(self):
        self.chick = COOP
        self.orca = PATROL[0]
        self.facing = (0, -1)
        self.corn = set(CORN)
        self.patrol_index = 1
        self.last_seen = None
        self.scan_turns = 0
        self.mode = "patrol"
        self.result = None

    def can_see(self, cell):
        return visible(self.orca, cell, self.facing)

    def move_chick(self, direction):
        cell = add(self.chick, direction)
        if self.result or not flyable(cell):
            return None
        self.chick = cell
        if self.chick == self.orca:
            self.result = "caught"
        elif self.chick == COOP and not self.corn:
            self.result = "home"
        else:
            self.observe_chick()
            if self.chick in self.corn:
                self.corn.remove(self.chick)
                return "corn"
        return None

    def observe_chick(self):
        if self.can_see(self.chick):
            self.mode = "chase"
            self.last_seen = self.chick
            self.scan_turns = 3
        elif self.last_seen is not None:
            self.mode = "search"
        else:
            self.mode = "patrol"

    def move_orca(self):
        if self.result:
            return
        self.observe_chick()

        if self.mode == "search" and self.orca == self.last_seen:
            self.facing = (self.facing[1], -self.facing[0])
            self.scan_turns -= 1
            if self.scan_turns == 0:
                self.last_seen = None
            self.observe_chick()
            return

        if self.mode == "patrol" and self.orca == PATROL[self.patrol_index]:
            self.patrol_index = (self.patrol_index + 1) % len(PATROL)
        goal = self.last_seen if self.last_seen is not None else PATROL[self.patrol_index]
        cell = next_step(self.orca, goal)
        if cell != self.orca:
            self.facing = cell[0] - self.orca[0], cell[1] - self.orca[1]
            self.orca = cell
        if self.orca == self.chick:
            self.result = "caught"
        else:
            self.observe_chick()

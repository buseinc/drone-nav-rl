"""Track selection and shared course race screen."""

from functools import lru_cache

import pygame

from games.skyrush import common as ui
from games.skyrush.airframe_art import draw_airframe
from games.skyrush.courses import COURSES, CourseEnvironment
from games.skyrush.menu import TRACKS
from games.skyrush.race import RaceScene
from games.skyrush.track_art import ALERT, ORCA, PANEL, PILOT, backdrop, center, draw_board
from src.drone_env_v4 import HOVER, MOVES
from src.shared.scene import Scene

BOARD_ORIGIN = (49, 128)
BOARD_CELL = 44
SIDEBAR = pygame.Rect(618, 122, 433, 540)


@lru_cache(maxsize=2)
def preview_env(course):
    return CourseEnvironment(course)


def heading(surface, course, title, subtitle):
    ui.text(surface, title, (48, 24), ui.WHITE, "title")
    ui.text(surface, subtitle, (50, 76), course.accent, "md")


def legend(surface, label, color, x, y):
    pygame.draw.line(surface, color, (x, y + 10), (x + 17, y + 10), 3)
    ui.text(surface, label, (x + 28, y), ui.WHITE, "sm")


class TrackSelectScene(Scene):
    def __init__(self, app, selected=0):
        super().__init__(app)
        self.selected = selected

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            from games.skyrush.menu import MenuScene
            self.app.change(MenuScene(self.app, selected=TRACKS))
        elif event.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
            direction = -1 if event.key in (pygame.K_LEFT, pygame.K_a) else 1
            self.selected = (self.selected + direction) % len(COURSES)
            self.app.sound.play("click")
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.app.sound.play("go")
            self.app.change(TrackRace(self.app, self.selected))

    def draw(self, surface):
        course = COURSES[self.selected]
        surface.blit(backdrop(course), (0, 0))
        heading(surface, course, "TRACKS", "Race ORCA to the landing pad.")
        now = pygame.time.get_ticks()
        tick, elapsed = divmod(now, 550)
        env = preview_env(course)
        draw_board(surface, course, env, BOARD_ORIGIN, BOARD_CELL, now, tick, elapsed / 550)

        ui.glass(surface, SIDEBAR, PANEL, alpha=238, border=course.accent)
        for index, candidate in enumerate(COURSES):
            selected = index == self.selected
            rect = pygame.Rect(643, 148 + index * 89, 382, 75)
            accent = candidate.accent if selected else (74, 83, 109)
            ui.glass(surface, rect, (36, 38, 58), border=accent, radius=8)
            pygame.draw.rect(surface, accent, (rect.x + 1, rect.y + 10, 3, 55))
            ui.text(surface, candidate.name, (rect.x + 19, rect.y + 10),
                    ui.WHITE if selected else ui.MUTED, "lg")
            ui.text(surface, candidate.setting, (rect.x + 20, rect.y + 44), accent, "sm")

        tile = pygame.Rect(653, 348, 18, 18)
        edge = ui.lerp_color(course.lane, ui.WHITE, 0.19)
        pygame.draw.rect(surface, course.lane, tile, border_radius=3)
        pygame.draw.rect(surface, edge, tile, 1, border_radius=3)
        ui.text(surface, "Open tile", (681, 348), ui.WHITE, "sm")
        ui.text(surface, "Stay on marked tiles to avoid a crash.",
                (681, 375), ui.MUTED, "md")
        if course.gate:
            ui.text(surface, "Arrows show where the wind pushes you.",
                    (681, 425), ui.MUTED, "md")
        else:
            ui.text(surface, "The ring shows the crane's next tile.",
                    (681, 425), ui.MUTED, "md")
        ui.hint_bar(surface, [("A / D", "select track"), ("ENTER", "race"),
                              ("ESC", "main menu")], y=684)


class SafeRoutePilot:
    """A predictable opponent that commits to the outer route."""

    def __init__(self, course):
        path = course.safe_path
        self.actions = []
        for (r, c), (nr, nc) in zip(path, path[1:]):
            dr, dc = (nr > r) - (nr < r), (nc > c) - (nc < c)
            self.actions.extend([MOVES.index((dr, dc))] * (abs(nr - r) + abs(nc - c)))
        self.actions.insert(len(self.actions) // 2, HOVER)

    def act(self, env):
        return self.actions[env.steps] if env.steps < len(self.actions) else HOVER


class TrackRace(RaceScene):
    tick_ms = 340

    def __init__(self, app, track_index):
        self.track_index = track_index
        self.course = COURSES[track_index]
        super().__init__(app, arena=0, level=1, rounds=1, title=self.course.name)

    def build_envs(self):
        return {who: CourseEnvironment(self.course) for who in ("human", "ai")}

    def build_pilot(self):
        if self.course.patrol and self.app.agent.available:
            return super().build_pilot()
        return SafeRoutePilot(self.course)

    def leave(self):
        self.app.change(TrackSelectScene(self.app, selected=self.track_index))

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            retry = event.key == pygame.K_r
            confirm_result = self.phase == "round_over" and event.key in (
                pygame.K_RETURN, pygame.K_SPACE)
            if retry or confirm_result:
                self.app.change(TrackRace(self.app, self.track_index))
                return
        super().handle_event(event)

    def px(self, who):
        return center(BOARD_ORIGIN, BOARD_CELL, self.ctrl[who].pos())

    def draw(self, surface):
        now = pygame.time.get_ticks()
        course = self.course
        surface.blit(backdrop(course), (0, 0))
        heading(surface, course, self.title, course.setting)
        env = self.envs["human"]
        tick = env.t if course.gate else self.ticks
        elapsed = self.tick_clock / self.tick_ms if self.phase == "racing" else 1
        draw_board(surface, course, env, BOARD_ORIGIN, BOARD_CELL,
                   now, tick, elapsed, next_tick=env.t + 1)
        self.draw_pilots(surface)
        self.draw_status(surface, tick)

        self.fx.draw(surface)
        if self.phase == "countdown":
            count = max(1, 3 - self.timer // 1000)
            ui.big_text(surface, count, (313, 388), ui.WHITE)
        elif self.phase == "round_over":
            self.draw_result(surface)
        ui.hint_bar(surface, [("ARROWS", "fly"), ("SPACE", "hover"),
                              ("R", "retry"), ("ESC", "tracks")], y=684)

    def draw_pilots(self, surface):
        size = 30
        positions = {who: self.px(who) for who in ("human", "ai")}
        a, b = positions.values()
        overlap = abs(a[0] - b[0]) < 24 and abs(a[1] - b[1]) < 24

        for who, color, offset in (("ai", ORCA, 9), ("human", PILOT, -9)):
            controller = self.ctrl[who]
            result = self.results[who]
            if result and result["event"] == "crash":
                continue
            x, y = positions[who]
            if overlap:
                y += offset

            previous = self.envs[who].path[-6:]
            if controller.busy and len(previous) > 1:
                trail = [center(BOARD_ORIGIN, BOARD_CELL, pos) for pos in previous[:-1]]
                pygame.draw.lines(surface, ui.lerp_color(PANEL, color, 0.62),
                                  False, trail + [(x, y)], 2)
            pygame.draw.circle(surface, ui.lerp_color(PANEL, color, 0.42), (x, y), 15, 1)
            draw_airframe(surface, (x, y), size, self.airframes[who], pygame.time.get_ticks(),
                          controller.last_action)

    def draw_status(self, surface, tick):
        ui.glass(surface, SIDEBAR, PANEL, alpha=240, border=self.course.accent)
        ui.text(surface, "RACE TIME", (646, 147), self.course.accent, "sm")
        time_ms = self.timer if self.phase == "racing" else self.ticks * self.tick_ms
        ui.text(surface, f"{time_ms / 1000:05.2f}",
                (645, 178), ui.WHITE, "xl")
        ui.text(surface, "s", (820, 214), ui.MUTED, "sm")
        for index, (label, who, color) in enumerate((
                ("You", "human", PILOT), ("ORCA", "ai", ORCA))):
            y = 270 + index * 53
            legend(surface, label, color, 650, y)
            ui.text(surface, f"{self.envs[who].steps} moves",
                    (1016, y), color, "sm", right=True)
        pygame.draw.line(surface, (58, 65, 88), (648, 390), (1020, 390))

        if self.course.gate:
            gate = self.course.gate
            ui.text(surface, "WIND TUNNEL", (649, 414), self.course.shortcut, "sm")
            status, color = ((f"Open for {gate.closes_in(tick)} moves", ORCA)
                             if gate.open_at(tick) else
                             (f"Opens in {gate.opens_in(tick)} moves", PILOT))
            ui.text(surface, status, (649, 450), color, "lg")
            for index in range(gate.period):
                rect = pygame.Rect(650 + index * 20, 505, 15, 8)
                segment = ORCA if gate.open_at(index) else (61, 61, 87)
                pygame.draw.rect(surface, segment, rect, border_radius=2)
                if index == tick % gate.period:
                    pygame.draw.rect(surface, ui.WHITE, rect.inflate(4, 6), 1, border_radius=3)
        else:
            ui.text(surface, "CRANE BRIDGE", (649, 414), self.course.shortcut, "sm")
            env = self.envs["human"]
            next_cell = env.enemy_pos(env.enemies[0], env.t + 1)
            blocked = next_cell in self.course.fast_cells
            headline = "Crane crossing next" if blocked else "Next move is clear"
            ui.text(surface, headline, (649, 450), ALERT if blocked else ORCA, "lg")

    def draw_result(self, surface):
        box = pygame.Rect(216, 235, 670, 237)
        ui.glass(surface, box, PANEL, alpha=252, border=self.course.accent)
        labels = {"human": "You won!", "ai": "ORCA won", None: "Draw"}
        ui.text(surface, labels[self.winner], (box.centerx, 293), ui.WHITE, "title", center=True)
        outcome = {"crash": "crashed", "dnf": "did not finish", "timeout": "out of time"}
        times = []
        for who, label in (("human", "You"), ("ai", "ORCA")):
            result = self.results[who]
            event = result["event"]
            mark = f"{result['time'] / 1000:.2f}s" if event == "goal" else outcome[event]
            times.append(f"{label}  {mark}")
        ui.text(surface, "    /    ".join(times), (box.centerx, 355), ui.MUTED, "md", center=True)
        ui.hint_bar(surface, [("ENTER", "race again"), ("ESC", "tracks")], y=423)

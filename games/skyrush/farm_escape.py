"""Collect corn and get home before ORCA catches the chick."""

from functools import lru_cache

import pygame

from games.skyrush import common as ui
from games.skyrush import farm_art as art
from games.skyrush.farm import COLS, CORN, HEDGES, ROWS, Farm, flyable, visible
from games.skyrush.save import complete_adventure
from src.drone_env_v4 import DIRS
from src.shared.effects import Effects
from src.shared.scene import Scene

HOP_MS = 165
DRONE_MS = {"patrol": 270, "chase": 150, "search": 225}
PAPER = (246, 235, 198)
MUTED = (80, 93, 65)


@lru_cache(maxsize=12)
def sight_overlay(origin, facing):
    surface = pygame.Surface((COLS * art.CELL, ROWS * art.CELL), pygame.SRCALPHA)
    for r in range(ROWS):
        for c in range(COLS):
            if flyable((r, c)) and visible(origin, (r, c), facing):
                rect = pygame.Rect(c * art.CELL, r * art.CELL, art.CELL, art.CELL)
                pygame.draw.rect(surface, (255, 239, 143, 92), rect.inflate(-2, -2),
                                 border_radius=4)
    return surface


def interpolate(previous, current, phase):
    return tuple(a + (b - a) * phase for a, b in zip(previous, current))


class FarmEscapeScene(Scene):
    ADVENTURE_ID = "farm_escape"

    def __init__(self, app):
        super().__init__(app)
        self.farm = Farm()
        self.phase = "ready"
        self.chick_from = self.farm.chick
        self.drone_from = self.farm.orca
        self.chick_clock = HOP_MS
        self.drone_clock = 0
        self.drone_delay = 800
        self.queued = None
        self.facing = (0, 1)
        self.fx = Effects()
        self.first_clear = False

    def leave(self):
        from games.skyrush.adventures import AdventureScene
        self.app.change(AdventureScene.after_visit(self.app, self.ADVENTURE_ID, self.first_clear))

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.leave()
        elif event.key == pygame.K_r:
            self.app.change(FarmEscapeScene(self.app))
        elif self.phase == "finished" and event.key == pygame.K_RETURN:
            if self.farm.result == "home":
                self.leave()
            else:
                self.app.change(FarmEscapeScene(self.app))
        elif self.phase == "ready" and event.key == pygame.K_RETURN:
            self.phase = "active"
            self.app.sound.play("go")
        elif self.phase == "active" and event.key in ui.KEY_TO_ACTION:
            self.queued = ui.KEY_TO_ACTION[event.key]

    def update(self, dt):
        self.fx.update(dt)
        if self.phase != "active":
            return

        self.chick_clock = min(HOP_MS, self.chick_clock + dt)
        self.drone_clock += dt
        previous_mode = self.farm.mode
        if self.chick_clock >= HOP_MS:
            action = self.queued if self.queued is not None else ui.held_action()
            self.queued = None
            if action is not None and action < len(DIRS):
                self.move_chick(DIRS[action])

        if self.farm.mode != previous_mode:
            delay = DRONE_MS[self.farm.mode]
            self.drone_clock = self.drone_clock * delay / self.drone_delay
            self.drone_delay = delay

        if not self.farm.result and self.drone_clock >= self.drone_delay:
            self.drone_from = self.farm.orca
            self.farm.move_orca()
            self.drone_clock = 0
            self.drone_delay = DRONE_MS[self.farm.mode]

        if self.farm.result:
            self.phase = "finished"
            if self.farm.result == "home":
                self.first_clear = complete_adventure(self.ADVENTURE_ID)
            self.app.sound.play("goal" if self.farm.result == "home" else "lose")
        elif self.farm.mode == "chase" and previous_mode != "chase":
            self.app.sound.play("beep")

    def move_chick(self, direction):
        previous = self.farm.chick
        self.facing = direction
        result = self.farm.move_chick(direction)
        if previous != self.farm.chick:
            self.chick_from = previous
            self.chick_clock = 0
        if result == "corn":
            self.fx.burst(art.point(self.farm.chick), art.GOLD, n=13, speed=0.09,
                          life=470, size=3)
            self.app.sound.play("click")

    def draw(self, surface):
        now = pygame.time.get_ticks()
        surface.fill((40, 65, 53))
        pygame.draw.rect(surface, (51, 80, 62), (0, 0, ui.WIDTH, 122))
        pygame.draw.line(surface, (134, 152, 95), (45, 116), (1055, 116), 1)
        ui.text(surface, "Farm Escape", (43, 20), art.CREAM, "xl")
        ui.text(surface, "Collect the corn and get back to the coop before ORCA catches you.",
                (47, 85), (209, 218, 167), "md")
        frame = pygame.Rect(*art.ORIGIN, COLS * art.CELL, ROWS * art.CELL).inflate(12, 12)
        pygame.draw.rect(surface, (119, 142, 86), frame, border_radius=9)
        surface.blit(art.terrain(), art.ORIGIN)
        surface.blit(sight_overlay(self.farm.orca, self.farm.facing), art.ORIGIN)
        art.coop(surface, not self.farm.corn, now)
        for r, c in sorted(self.farm.corn):
            x, y = art.point((r, c))
            art.corn(surface, x, y - 3, now + (r + c) * 130)
        self.draw_characters(surface, now)
        self.fx.draw(surface)
        self.draw_hud(surface)
        if self.phase == "ready":
            self.message(surface, "Corn Run", "Collect six pieces of corn, then get back to the coop.",
                         "Enter  ·  Start")
        elif self.phase == "finished":
            if self.farm.result == "home":
                message = "New adventure unlocked!" if self.first_clear else "You brought all the corn home."
                self.message(surface, "Safe at Home!", message, "Enter  ·  Back to adventures")
            else:
                self.message(surface, "ORCA Caught You!",
                             "Duck behind a fence or hide in a bush.", "Enter  ·  Try again")
        ui.hint_bar(surface, [("ARROWS", "move"), ("R", "restart"), ("ESC", "adventures")], y=669)

    def draw_characters(self, surface, now):
        hop = self.chick_clock / HOP_MS if self.phase != "finished" else 1
        flight = min(1, self.drone_clock / self.drone_delay) if self.phase != "finished" else 1
        x, y = art.point(interpolate(self.chick_from, self.farm.chick, hop))
        if self.phase == "ready":
            y += 15
        hidden = self.farm.chick in HEDGES and hop > 0.7
        art.chick(surface, x, y, now, self.facing, hop, hidden)
        x, y = art.point(interpolate(self.drone_from, self.farm.orca, flight))
        art.drone(surface, x, y, self.farm.mode, now, self.farm.facing)

    def draw_hud(self, surface):
        rect = pygame.Rect(796, 145, 259, 484)
        pygame.draw.rect(surface, PAPER, rect, border_radius=13)
        pygame.draw.rect(surface, (189, 178, 120), rect, 2, border_radius=13)
        ui.text(surface, "Corn Basket", (818, 168), art.INK, "lg")
        count = len(CORN) - len(self.farm.corn)
        ui.text(surface, f"{count} / {len(CORN)}", (1035, 174), art.INK, "num", right=True)
        for i in range(len(CORN)):
            x, y = 834 + i * 37, 231
            pygame.draw.circle(surface, (222, 208, 156), (x, y), 15)
            if i < count:
                art.corn(surface, x, y, 0, 0.86)
        pygame.draw.line(surface, (209, 193, 144), (818, 268), (1033, 268), 1)
        ui.text(surface, "ORCA", (818, 289), art.INK, "lg")
        patrol = {"patrol": ("On patrol", (70, 110, 78)),
                  "chase": ("Chasing you!", (159, 65, 46)),
                  "search": ("Searching nearby", (143, 94, 43))}
        label, color = patrol[self.farm.mode]
        pygame.draw.circle(surface, color, (825, 336), 5)
        ui.text(surface, label, (840, 326), color, "sm")

        pygame.draw.line(surface, (209, 193, 144), (818, 367), (1033, 367), 1)
        if self.farm.result == "home":
            ui.text(surface, "You made it home", (818, 391), (70, 110, 78), "lg")
        elif not self.farm.corn:
            ui.text(surface, "Back to the coop!", (818, 391), (70, 110, 78), "lg")
        elif self.farm.chick in HEDGES:
            ui.text(surface, "Hiding in a bush", (818, 394), (70, 110, 78), "md")
        else:
            ui.text(surface, "ORCA sees the yellow tiles.", (818, 396), MUTED, "sm")
        ui.text(surface, "Fences block ORCA's view.", (818, 450), MUTED, "sm")
        ui.text(surface, "Bushes hide you from afar.", (818, 476), MUTED, "sm")

    @staticmethod
    def message(surface, title, description, action):
        box = pygame.Rect(133, 315, 544, 169)
        pygame.draw.rect(surface, (86, 104, 67), box.move(0, 4), border_radius=11)
        pygame.draw.rect(surface, PAPER, box, border_radius=11)
        pygame.draw.rect(surface, (220, 186, 112), box, 2, border_radius=11)
        ui.text(surface, title, (box.centerx, 352), art.INK, "title", center=True)
        ui.text(surface, description, (box.centerx, 399), MUTED, "sm", center=True)
        ui.text(surface, action, (box.centerx, 442), (126, 84, 39), "lg", center=True)

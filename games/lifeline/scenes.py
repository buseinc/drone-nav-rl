"""Lifeline skeleton: title screen and chapter select.

The chapters themselves (pickup / drop-off, fragile cargo, organ timer,
earthquake relief, co-op with ORCA) are built on top of the shared core in
src/ (DroneEnvV4, ORCA, tick world). Nothing here is used by SkyRush.
"""

import math

import pygame

from games.lifeline import common as ui
from src.shared.scene import Scene
from src.shared.world import AI_NAME

CHAPTERS = [
    {"name": "CITY COURIER", "color": (81, 220, 150),
     "story": "Learn the ropes: pick up parcels, deliver them across town."},
    {"name": "HOSPITAL RUN", "color": (255, 90, 100),
     "story": "Blood, lab samples - and one organ that cannot wait."},
    {"name": "EARTHQUAKE RELIEF", "color": (255, 180, 80),
     "story": "Roads are blocked. Camps need water, medicine, blankets."},
    {"name": "WINGMAN", "color": (65, 190, 255),
     "story": f"Share the deliveries with {AI_NAME}. You plan, it flies."},
]


class TitleScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.t = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.running = False
            else:
                self.app.sound.play("go")
                self.app.change(ChapterScene(self.app))

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        self.app.sky.draw(surf)
        intro = min(1.0, self.t / 900)
        y = 250 - (1 - intro) ** 2 * 120
        ui.draw_logo(surf, (ui.WIDTH // 2, int(y)))
        ui.text(surf, "EVERY SECOND COUNTS", (ui.WIDTH // 2, int(y) + 92),
                (255, 210, 215), "lg", center=True)
        # heartbeat line
        t = pygame.time.get_ticks()
        pts = []
        for x in range(200, ui.WIDTH - 200, 6):
            k = ((x + t / 3) % 260) / 260
            beat = 0
            if 0.40 < k < 0.45:
                beat = -40 * math.sin((k - 0.40) / 0.05 * math.pi)
            elif 0.45 < k < 0.50:
                beat = 25 * math.sin((k - 0.45) / 0.05 * math.pi)
            pts.append((x, 430 + beat))
        pygame.draw.lines(surf, (255, 90, 100), False, pts, 3)
        if self.t > 900 and (self.t // 500) % 2 == 0:
            ui.text(surf, "PRESS ANY KEY", (ui.WIDTH // 2, 520), ui.WHITE,
                    "lg", center=True)


class ChapterScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.sel = 0

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.app.change(TitleScene(self.app))
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.sel = (self.sel + 1) % len(CHAPTERS)
        elif event.key in (pygame.K_UP, pygame.K_w):
            self.sel = (self.sel - 1) % len(CHAPTERS)

    def draw(self, surf):
        self.app.sky.draw(surf, skyline=False)
        ui.text(surf, "CHAPTERS", (60, 30), ui.WHITE, "xl")
        for i, ch in enumerate(CHAPTERS):
            sel = i == self.sel
            r = pygame.Rect(60, 130 + i * 115, ui.WIDTH - 120, 100)
            ui.glass(surf, r, alpha=220 if sel else 140,
                     border=ch["color"] if sel else (60, 66, 110))
            ui.text(surf, f"{i + 1}", (r.x + 26, r.y + 22), ch["color"], "xl")
            ui.text(surf, ch["name"], (r.x + 90, r.y + 20), ch["color"], "lg")
            ui.text(surf, ch["story"], (r.x + 90, r.y + 58), ui.MUTED, "sm")
            ui.text(surf, "IN DEVELOPMENT", (r.right - 24, r.y + 38),
                    ui.DIM, "key", right=True)
        ui.hint_bar(surf, [("UP/DOWN", "choose"), ("ESC", "back")])

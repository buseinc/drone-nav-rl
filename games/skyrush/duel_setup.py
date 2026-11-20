"""Duel setup: pick an arena, ORCA's level and fog, then race."""

import math

import pygame

from games.skyrush import common as ui
from games.skyrush.save import load_leaderboard
from src.shared.scene import Scene
from src.shared.world import AI_NAME, ARENAS, LEVELS, make_env

ROWS = ["arena", "level", "fog"]


class DuelSetupScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.s = app.settings
        self.row = 0
        self.previews = [make_env(i, seed=900 + i) for i in range(len(ARENAS))]
        self.board = load_leaderboard().get("duels", {})

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k, s = event.key, self.s
        if k == pygame.K_ESCAPE:
            from games.skyrush.menu import MenuScene
            self.app.change(MenuScene(self.app, selected=1))
        elif k in (pygame.K_UP, pygame.K_w):
            self.row = (self.row - 1) % len(ROWS)
        elif k in (pygame.K_DOWN, pygame.K_s):
            self.row = (self.row + 1) % len(ROWS)
        elif k in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
            d = 1 if k in (pygame.K_RIGHT, pygame.K_d) else -1
            name = ROWS[self.row]
            if name == "arena":
                s["arena"] = (s["arena"] + d) % len(ARENAS)
            elif name == "level":
                s["level"] = (s["level"] + d) % len(LEVELS)
            else:
                s["fog"] = not s["fog"]
        elif k == pygame.K_f:
            s["fog"] = not s["fog"]
        elif k in (pygame.K_RETURN, pygame.K_SPACE):
            from games.skyrush.race import RaceScene
            self.app.sound.play("go")
            self.app.change(RaceScene(self.app, s["arena"], s["level"],
                                      s["fog"]))
            return
        else:
            return
        self.app.sound.play("click")

    def draw(self, surf):
        self.app.sky.draw(surf, skyline=False)
        t = pygame.time.get_ticks()
        ui.text(surf, "DUEL", (60, 26), ui.WHITE, "xl")
        ui.text(surf, f"Race {AI_NAME}, the neural pilot. Same speed, same "
                      "map. First to land wins.", (62, 96), ui.MUTED, "md")

        # --- arenas ---
        self.section(surf, 0, "ARENA", 140)
        for i, arena in enumerate(ARENAS):
            sel = i == self.s["arena"]
            x = 60 + i * 250
            card = pygame.Rect(x, 170 - (8 if sel else 0), 230, 250)
            ui.glass(surf, card, alpha=220 if sel else 140,
                     border=arena["color"] if sel else (60, 66, 110))
            self.preview(surf, self.previews[i], (card.x + 35, card.y + 18),
                         16)
            ui.text(surf, arena["name"], (card.x + 18, card.y + 200),
                    arena["color"] if sel else ui.MUTED, "lg")
            if sel:
                ui.text(surf, arena["tagline"], (ui.WIDTH // 2, 436),
                        ui.WHITE, "md", center=True)

        # --- ORCA level ---
        self.section(surf, 1, f"{AI_NAME} LEVEL", 470)
        for i, lvl in enumerate(LEVELS):
            sel = i == self.s["level"]
            x = 60 + i * 200
            chip = pygame.Rect(x, 498, 184, 50)
            ui.glass(surf, chip, alpha=220 if sel else 120,
                     border=ui.DRONE if sel else (60, 66, 110))
            for k in range(i + 1):   # chevrons = rank
                cx = chip.x + 22 + k * 12
                pygame.draw.lines(surf, ui.DRONE if sel else ui.DIM, False,
                                  [(cx - 5, chip.y + 30), (cx, chip.y + 20),
                                   (cx + 5, chip.y + 30)], 3)
            ui.text(surf, lvl["name"], (chip.x + 64, chip.y + 12),
                    ui.WHITE if sel else ui.MUTED, "lg")
        ui.text(surf, LEVELS[self.s["level"]]["desc"], (680, 514),
                ui.MUTED, "sm")

        # --- fog ---
        self.section(surf, 2, "FOG OF WAR", 575)
        on = self.s["fog"]
        sw = pygame.Rect(60, 602, 64, 30)
        pygame.draw.rect(surf, ui.GOAL if on else (50, 56, 86), sw,
                         border_radius=15)
        pygame.draw.circle(surf, ui.WHITE, (sw.x + (48 if on else 16),
                                            sw.centery), 11)
        ui.text(surf, "You only see the 7x7 area around your drone - "
                      f"exactly what {AI_NAME} sees.", (140, 606),
                ui.WHITE if on else ui.MUTED, "sm")

        # record for this setup
        key = f"{ARENAS[self.s['arena']]['name']} / " \
              f"{LEVELS[self.s['level']]['name']}" + (" / FOG" if on else "")
        rec = self.board.get(key)
        if rec:
            ui.text(surf, f"Your record here: {rec['human']} won, "
                          f"{rec['ai']} lost", (ui.WIDTH - 60, 40), ui.GOLD,
                    "sm", right=True)

        pulse = 0.5 + 0.5 * math.sin(t / 250)
        btn = pygame.Rect(ui.WIDTH - 260, 590, 200, 52)
        pygame.draw.rect(surf, ui.lerp_color(ui.PLAYER, ui.GOLD, pulse), btn,
                         border_radius=26)
        ui.text(surf, "TAKE OFF", btn.center, ui.SKY_TOP, "lg", center=True)
        ui.hint_bar(surf, [("UP/DOWN", "section"), ("LEFT/RIGHT", "change"),
                           ("ENTER", "take off"), ("ESC", "back")])

    def section(self, surf, idx, label, y):
        sel = self.row == idx
        if sel:
            pygame.draw.polygon(surf, ui.GOLD, [(44, y + 4), (52, y + 10),
                                                (44, y + 16)])
        ui.text(surf, label, (60, y), ui.GOLD if sel else ui.MUTED, "sm")

    @staticmethod
    def preview(surf, env, origin, cell):
        """Tiny map thumbnail."""
        for r in range(env.grid_size):
            for c in range(env.grid_size):
                p = (r, c)
                rect = pygame.Rect(origin[0] + c * cell, origin[1] + r * cell,
                                   cell - 2, cell - 2)
                color = (40, 46, 80)
                if p in env.obstacles:
                    color = ui.OBSTACLE
                elif p == env.goal:
                    color = ui.GOAL
                elif p in env.wind:
                    color = ui.WIND_ARROW
                pygame.draw.rect(surf, color, rect, border_radius=3)
        for e in env.enemies:
            for p in e["track"]:
                pygame.draw.circle(surf, ui.ENEMY, (origin[0] + p[1] * cell +
                                                    cell // 2 - 1,
                                                    origin[1] + p[0] * cell +
                                                    cell // 2 - 1), 3)

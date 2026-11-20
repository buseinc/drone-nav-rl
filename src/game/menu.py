"""Main menu: three big mode cards plus guide and quit."""

import math

import pygame

from src.game import common as ui
from src.game.scene import Scene, load_leaderboard
from src.game.world import AI_NAME

CARDS = [
    {"name": "SKY MISSIONS", "sub": "16 missions · 4 zones · boss duels",
     "color": ui.GOAL},
    {"name": "DUEL", "sub": f"Race {AI_NAME}, the neural pilot",
     "color": ui.PLAYER},
    {"name": "NEURAL LAB", "sub": f"Look inside {AI_NAME}'s mind",
     "color": ui.DRONE},
]
GUIDE, QUIT = 3, 4


class MenuScene(Scene):
    def __init__(self, app, selected=0):
        super().__init__(app)
        self.sel = selected
        self.notice = ""
        board = load_leaderboard()
        self.stars = sum(board.get("missions", {}).values())
        self.duel_wins = sum(r["human"] for r in board.get("duels",
                                                         {}).values())

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if k == pygame.K_ESCAPE:
            self.app.running = False
            return
        if k in (pygame.K_RIGHT, pygame.K_d):
            self.sel = (self.sel + 1) % 5
        elif k in (pygame.K_LEFT, pygame.K_a):
            self.sel = (self.sel - 1) % 5
        elif k in (pygame.K_DOWN, pygame.K_s):
            self.sel = GUIDE if self.sel < 3 else self.sel
        elif k in (pygame.K_UP, pygame.K_w):
            self.sel = 1 if self.sel >= 3 else self.sel
        elif k == pygame.K_g:
            self.start(GUIDE)
            return
        elif k in (pygame.K_RETURN, pygame.K_SPACE):
            self.start(self.sel)
            return
        else:
            return
        self.app.sound.play("click")

    def start(self, index):
        from src.game.duel_setup import DuelSetupScene
        from src.game.guide import GuideScene
        from src.game.missions import MissionMapScene
        from src.game.vision import VisionScene

        if index in (0, 1, 2) and not self.app.agent.available:
            self.notice = f"{AI_NAME} is not trained yet: " \
                          "python -m src.train_dqn_v4"
            return
        self.app.sound.play("go")
        scene = {0: MissionMapScene, 1: DuelSetupScene, 2: VisionScene,
                 GUIDE: GuideScene}.get(index)
        if scene:
            self.app.change(scene(self.app))
        else:
            self.app.running = False

    # ---------- drawing ----------

    def draw(self, surf):
        self.app.sky.draw(surf)
        ui.draw_logo(surf, (ui.WIDTH // 2, 92), scale=0.62)
        t = pygame.time.get_ticks()

        for i, card in enumerate(CARDS):
            sel = i == self.sel
            lift = 12 if sel else 0
            rect = pygame.Rect(70 + i * 330, 190 - lift, 300, 330)
            ui.glass(surf, rect, alpha=225 if sel else 150,
                     border=card["color"] if sel else (60, 66, 110))
            if sel:
                glow = 0.5 + 0.5 * math.sin(t / 250)
                pygame.draw.rect(surf, ui.lerp_color(card["color"], ui.WHITE,
                                                     glow * 0.4),
                                 rect.inflate(6, 6), 2, border_radius=21)
            art = pygame.Rect(rect.x + 20, rect.y + 20, 260, 180)
            pygame.draw.rect(surf, (16, 18, 42), art, border_radius=12)
            surf.set_clip(art)
            (self.art_missions, self.art_duel, self.art_lab)[i](surf, art, t)
            surf.set_clip(None)
            ui.text(surf, card["name"], (rect.x + 22, rect.y + 218),
                    card["color"] if sel else ui.WHITE, "title")
            ui.text(surf, card["sub"], (rect.x + 24, rect.y + 266),
                    ui.MUTED, "sm")
            stat = (f"{self.stars} / 48 stars" if i == 0 else
                    f"{self.duel_wins} duels won" if i == 1 else
                    "Q-values · heat-maps · live edits")
            ui.text(surf, stat, (rect.x + 24, rect.y + 292), ui.GOLD, "xs")

        for idx, label, x in ((GUIDE, "FLIGHT GUIDE", 380),
                              (QUIT, "QUIT", 620)):
            sel = idx == self.sel
            btn = pygame.Rect(x, 556, 200 if idx == GUIDE else 100, 46)
            ui.glass(surf, btn, alpha=220 if sel else 120,
                     border=ui.WHITE if sel else (60, 66, 110), radius=23)
            ui.text(surf, label, btn.center, ui.WHITE if sel else ui.MUTED,
                    "lg", center=True)

        if self.notice:
            ui.text(surf, self.notice, (ui.WIDTH // 2, 620), ui.OBSTACLE,
                    "sm", center=True)
        sound = "on" if self.app.sound.enabled else "off"
        ui.hint_bar(surf, [("ARROWS", "choose"), ("ENTER", "select"),
                           ("G", "guide"), ("M", f"sound {sound}"),
                           ("ESC", "quit")])

    # ---------- card illustrations ----------

    @staticmethod
    def art_missions(surf, r, t):
        pts = [(r.x + 30, r.bottom - 40), (r.x + 90, r.y + 110),
               (r.x + 150, r.y + 140), (r.x + 220, r.y + 50)]
        pygame.draw.lines(surf, (70, 80, 130), False, pts, 4)
        for i, p in enumerate(pts):
            pygame.draw.circle(surf, ui.GOAL if i < 3 else ui.GOLD, p, 13)
            if i < 3:
                ui.stars(surf, 3 - (i == 2), (p[0] - 18, p[1] + 24), 10)
        k = (t / 2200) % 1.0 * (len(pts) - 1)
        i = int(k)
        a, b = pts[i], pts[i + 1]
        f = k - i
        pos = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f - 24)
        ui.draw_drone(surf, (0, 0), (pos[0] - 22, pos[1] - 22), 44, ui.PLAYER)

    @staticmethod
    def art_duel(surf, r, t):
        for i, (color, side) in enumerate(((ui.PLAYER, -1), (ui.DRONE, 1))):
            bob = math.sin(t / 300 + i * 2) * 8
            x = r.centerx + side * 62 - 36
            ui.draw_drone(surf, (0, 0), (x, r.centery - 40 + bob), 72, color)
        flash = 0.5 + 0.5 * math.sin(t / 150)
        ui.text(surf, "VS", (r.centerx, r.centery - 4),
                ui.lerp_color(ui.GOLD, ui.WHITE, flash), "title", center=True)
        for k in range(6):   # speed lines
            y = r.y + 30 + k * 26
            x = (t / 3 + k * 70) % (r.width + 80) + r.x - 80
            pygame.draw.line(surf, (60, 70, 120), (x, y), (x + 40, y), 2)

    @staticmethod
    def art_lab(surf, r, t):
        cell = 30
        ox, oy = r.x + 25, r.y + 15
        for i in range(5):
            for j in range(7):
                v = 0.5 + 0.5 * math.sin(t / 600 + i * 0.9 + j * 0.6)
                rect = pygame.Rect(ox + j * cell, oy + i * cell, cell - 3,
                                   cell - 3)
                pygame.draw.rect(surf, ui.lerp_color((48, 38, 92),
                                                     (40, 150, 110), v),
                                 rect, border_radius=4)
                a = (i + j + t // 900) % 4
                ui.draw_arrow(surf, rect.center, a, 8, (220, 230, 240), 2)
        rect = pygame.Rect(ox + 3 * cell, oy + 2 * cell, cell - 3, cell - 3)
        ui.draw_drone(surf, (0, 0), (rect.x - 6, rect.y - 6), 40, ui.DRONE)

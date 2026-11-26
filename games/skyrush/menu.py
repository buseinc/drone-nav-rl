"""Main menu for SkyRush's modes, flight guide and quit."""

import math

import pygame

from games.skyrush import common as ui
from games.skyrush.mission_card import draw_mission_card
from games.skyrush.missions import MISSIONS, MissionMapScene, mission_star_total
from games.skyrush.profiles import ProfileScene, display_name
from games.skyrush.save import active_profile_name, load_leaderboard
from src.shared.scene import Scene
from src.shared.world import AI_NAME

CARDS = [
    {"name": "SKY MISSIONS", "sub": f"{len(MISSIONS)} missions · 4 zones · boss duels",
     "color": ui.GOAL},
    {"name": "DUEL", "sub": f"Race {AI_NAME} to the landing pad",
     "color": ui.PLAYER},
    {"name": "NEURAL LAB", "sub": f"See how {AI_NAME} chooses a move",
     "color": ui.DRONE},
]
GUIDE, QUIT, TRACKS, ADVENTURES, HANGAR = 3, 4, 5, 6, 7
MENU_ORDER = (0, 1, 2, TRACKS, ADVENTURES, HANGAR, GUIDE, QUIT)
PROFILE_BUTTON = pygame.Rect(835, 26, 195, 50)
HANGAR_BUTTON = pygame.Rect(497, 556, 154, 46)


class MenuScene(Scene):
    def __init__(self, app, selected=0):
        super().__init__(app)
        self.sel = selected
        self.notice = ""
        self.card_started_at = pygame.time.get_ticks()
        board = load_leaderboard()
        self.stars = mission_star_total(board.get("missions", {}))
        self.duel_wins = sum(r["human"] for r in board.get("duels",
                                                         {}).values())

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if PROFILE_BUTTON.collidepoint(event.pos):
                self.show_profiles()
            elif HANGAR_BUTTON.collidepoint(event.pos):
                self.start(HANGAR)
            return
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if k == pygame.K_ESCAPE:
            self.app.running = False
            return
        if k in (pygame.K_RIGHT, pygame.K_d, pygame.K_LEFT, pygame.K_a):
            direction = 1 if k in (pygame.K_RIGHT, pygame.K_d) else -1
            self.sel = MENU_ORDER[(MENU_ORDER.index(self.sel) + direction)
                                  % len(MENU_ORDER)]
        elif k in (pygame.K_DOWN, pygame.K_s):
            self.sel = TRACKS if self.sel < 3 else self.sel
        elif k in (pygame.K_UP, pygame.K_w):
            self.sel = 1 if self.sel >= 3 else self.sel
        elif k == pygame.K_g:
            self.start(GUIDE)
            return
        elif k == pygame.K_h:
            self.start(HANGAR)
            return
        elif k == pygame.K_p:
            self.show_profiles()
            return
        elif k in (pygame.K_RETURN, pygame.K_SPACE):
            self.start(self.sel)
            return
        else:
            return
        self.app.sound.play("click")

    def show_profiles(self):
        self.app.sound.play("click")
        self.app.change(ProfileScene(self.app, from_menu=True))

    def start(self, index):
        from games.skyrush.adventures import AdventureScene
        from games.skyrush.duel_setup import DuelSetupScene
        from games.skyrush.guide import GuideScene
        from games.skyrush.hangar import HangarScene
        from games.skyrush.tracks import TrackSelectScene
        from games.skyrush.vision import VisionScene

        if index in (0, 1, 2) and not self.app.agent.available:
            self.notice = f"{AI_NAME} is not trained yet: " \
                          "python -m src.train_dqn_v4"
            return
        self.app.sound.play("go")
        scene = {0: MissionMapScene, 1: DuelSetupScene, 2: VisionScene,
                 TRACKS: TrackSelectScene, ADVENTURES: AdventureScene, HANGAR: HangarScene,
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
            if i == 0:
                draw_mission_card(surf, art, t - self.card_started_at)
            else:
                (self.art_duel, self.art_lab)[i - 1](surf, art, t)
            surf.set_clip(None)
            ui.text(surf, card["name"], (rect.x + 22, rect.y + 218),
                    card["color"] if sel else ui.WHITE, "title")
            ui.text(surf, card["sub"], (rect.x + 24, rect.y + 266),
                    ui.MUTED, "sm")
            stat = (f"{self.stars} / {len(MISSIONS) * 3} stars" if i == 0 else
                    f"{self.duel_wins} duels won" if i == 1 else
                    "Test routes and obstacles")
            ui.text(surf, stat, (rect.x + 24, rect.y + 292), ui.GOLD, "xs")

        for idx, label, x, width, accent in (
                (TRACKS, "TRACKS", 75, 135, (248, 111, 226)),
                (ADVENTURES, "ORCA: ON THE TRAIL", 224, 259, (255, 214, 112)),
                (HANGAR, "HANGAR", HANGAR_BUTTON.x, HANGAR_BUTTON.width, (128, 221, 248)),
                (GUIDE, "FLIGHT GUIDE", 665, 197, ui.WHITE),
                (QUIT, "QUIT", 876, 149, ui.WHITE)):
            sel = idx == self.sel
            btn = pygame.Rect(x, 556, width, 46)
            featured = idx in (TRACKS, ADVENTURES, HANGAR)
            label_color = ui.WHITE if sel else accent if featured else ui.MUTED
            ui.glass(surf, btn, alpha=220 if sel else 120,
                     border=accent if sel or featured else (60, 66, 110),
                     radius=23)
            ui.text(surf, label, btn.center, label_color, "lg", center=True)

        if self.notice:
            ui.text(surf, self.notice, (ui.WIDTH // 2, 620), ui.OBSTACLE,
                    "sm", center=True)
        self.draw_profile_button(surf)
        sound = "on" if self.app.sound.enabled else "off"
        ui.hint_bar(surf, [("ARROWS", "choose"), ("ENTER", "select"),
                           ("H", "hangar"), ("M", f"sound {sound}"),
                           ("ESC", "quit")])

    def draw_profile_button(self, surf):
        rect = PROFILE_BUTTON
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        ui.glass(surf, rect, (20, 34, 59), alpha=238 if hovered else 200,
                 border=(117, 184, 206) if hovered else (69, 113, 127), radius=12)
        x, y = rect.left + 24, rect.centery
        pygame.draw.circle(surf, (31, 56, 81), (x, y), 14)
        pygame.draw.circle(surf, (163, 215, 235), (x, y - 4), 3)
        pygame.draw.arc(surf, (163, 215, 235), (x - 6, y + 1, 12, 9), 0, math.pi, 2)
        name = active_profile_name()
        label = display_name(name, rect.width - 70, "sm") if name else "Choose profile"
        ui.text(surf, "PROFILE", (rect.left + 45, rect.top + 6), ui.MUTED, "xs")
        ui.text(surf, label, (rect.left + 45, rect.top + 22), ui.WHITE, "sm")
        vx = rect.right - 15
        pygame.draw.lines(surf, ui.MUTED, False, ((vx - 4, y - 2), (vx, y + 2), (vx + 4, y - 2)), 2)

    # ---------- card illustrations ----------

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

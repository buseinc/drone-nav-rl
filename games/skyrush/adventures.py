"""The ordered adventure cards and their unlock reveal."""

import math
from dataclasses import dataclass

import pygame

from games.skyrush import common as ui
from games.skyrush import duck_art
from games.skyrush import farm_art
from games.skyrush.duck_scene import DuckRescueScene
from games.skyrush.farm_escape import FarmEscapeScene
from games.skyrush.save import load_leaderboard
from src.shared.scene import Scene

CARD_WIDTH = 304
CARDS_PER_PAGE = 3
REVEAL_MS = 1150
REVEAL_PAUSE = 260


def chick_cover(surface, center, now):
    x, y = center
    pygame.draw.circle(surface, (238, 215, 147), (x, y - 18), 65)
    pygame.draw.ellipse(surface, (125, 173, 118), (x - 228, y + 32, 385, 148))
    pygame.draw.ellipse(surface, (146, 186, 126), (x - 100, y + 44, 365, 116))
    image = pygame.Surface((72, 67), pygame.SRCALPHA)
    farm_art.chick(image, 35, 36, now, (0, 1), (now % 850) / 850)
    image = pygame.transform.smoothscale(image, (144, 134))
    surface.blit(image, image.get_rect(center=(x - 8, y + 6)))
    farm_art.corn(surface, x + 87, y + 39, now, 1.28)
    farm_art.corn(surface, x - 88, y + 46, now + 350, 1.07)


def duck_cover(surface, center, now):
    x, y = center
    pygame.draw.circle(surface, (181, 218, 187), (x - 24, y - 25), 71)
    pygame.draw.ellipse(surface, (94, 165, 174), (x - 192, y + 18, 380, 135))
    for i, offset in enumerate((-104, -26, 65, 102)):
        duck_art.lily(surface, x + offset, y + 55 + 17 * (i % 2), i % 2 == 0)
    duck_art.draw_duck(surface, (x + 50, y - 2), now, adult=True, moving=True, scale=1.64)
    duck_art.draw_duck(surface, (x - 3, y + 25), now, index=0, moving=True, scale=0.94)
    duck_art.draw_duck(surface, (x - 43, y + 37), now, index=1, moving=True, scale=0.79)
    duck_art.draw_duck(surface, (x - 79, y + 42), now, index=2, moving=True, scale=0.69)


@dataclass(frozen=True)
class Adventure:
    scene: type
    title: str
    description: tuple
    accent: tuple
    sky: tuple
    cover: object


ADVENTURES = (
    Adventure(FarmEscapeScene, "Farm Escape", ("Grab the corn, dodge ORCA", "and get back to the coop."),
              (255, 210, 126), (162, 198, 137), chick_cover),
    Adventure(DuckRescueScene, "Duckling Rescue", ("Find three ducklings and", "guide them across the river."),
              (140, 229, 208), (122, 186, 181), duck_cover),
)


class AdventureScene(Scene):
    def __init__(self, app, selected=None, reveal=None):
        super().__init__(app)
        self.completed = set(load_leaderboard().get("adventures", []))
        self.selected = selected if selected is not None else self.latest_unlocked()
        self.reveal = reveal
        self.reveal_elapsed = 0

    def unlocked(self, index):
        return all(entry.scene.ADVENTURE_ID in self.completed for entry in ADVENTURES[:index])

    def latest_unlocked(self):
        return max(index for index in range(len(ADVENTURES)) if self.unlocked(index))

    @classmethod
    def after_visit(cls, app, adventure_id, first_clear):
        current = next(index for index, entry in enumerate(ADVENTURES)
                       if entry.scene.ADVENTURE_ID == adventure_id)
        successor = current + 1
        if first_clear and successor < len(ADVENTURES):
            return cls(app, selected=successor, reveal=successor)
        return cls(app, selected=current)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        key = event.key
        if key == pygame.K_ESCAPE:
            from games.skyrush.menu import ADVENTURES as MENU_ADVENTURES, MenuScene
            self.app.change(MenuScene(self.app, selected=MENU_ADVENTURES))
        elif key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
            direction = -1 if key in (pygame.K_LEFT, pygame.K_a) else 1
            self.selected = (self.selected + direction) % len(ADVENTURES)
            self.app.sound.play("click")
        elif key in (pygame.K_RETURN, pygame.K_SPACE) and self.unlocked(self.selected):
            if self.selected == self.reveal and self.reveal_elapsed < REVEAL_MS:
                self.reveal_elapsed = REVEAL_MS
                return
            self.app.sound.play("go")
            self.app.change(ADVENTURES[self.selected].scene(self.app))

    def update(self, dt):
        if self.reveal is None:
            return
        previous = self.reveal_elapsed
        self.reveal_elapsed = min(REVEAL_MS + 500, previous + dt)
        if previous < REVEAL_PAUSE <= self.reveal_elapsed:
            self.app.sound.play("goal")

    def draw(self, surface):
        ui.draw_background(surface)
        now = pygame.time.get_ticks()
        ui.text(surface, "ORCA: On the Trail", (54, 27), ui.WHITE, "xl")
        count = sum(entry.scene.ADVENTURE_ID in self.completed for entry in ADVENTURES)
        hint = ("Pick a card to play again." if count == len(ADVENTURES)
                else "Finish one adventure to unlock the next.")
        ui.text(surface, hint, (57, 106), ui.MUTED, "md")
        ui.text(surface, f"{count} / {len(ADVENTURES)} finished", (1045, 110),
                ui.GOLD, "sm", right=True)
        pygame.draw.line(surface, (57, 62, 97), (56, 146), (1045, 146), 1)

        start = self.selected // CARDS_PER_PAGE * CARDS_PER_PAGE
        indices = range(start, min(start + CARDS_PER_PAGE, len(ADVENTURES)))
        x = (ui.WIDTH - (CARD_WIDTH + 30) * len(indices) + 30) // 2
        for index in indices:
            rect = pygame.Rect(x, 188, CARD_WIDTH, 405)
            self.draw_card(surface, rect, index, now)
            x += CARD_WIDTH + 30

        ui.hint_bar(surface, [("A / D", "select"), ("ENTER", "play"),
                              ("ESC", "main menu")], y=665)

    def draw_card(self, surface, rect, index, now):
        entry = ADVENTURES[index]
        selected = index == self.selected
        unlocked = self.unlocked(index)
        if selected:
            rect = rect.move(0, -7)
        border = entry.accent if unlocked else (130, 125, 164)
        ui.glass(surface, rect, (29, 31, 57), alpha=246,
                 border=border if selected else (65, 69, 109), radius=18)

        reveal = min(1, max(0, (self.reveal_elapsed - REVEAL_PAUSE) / (REVEAL_MS - REVEAL_PAUSE)))
        if unlocked:
            picture = pygame.Rect(rect.x + 13, rect.y + 13, rect.w - 26, 205)
            pygame.draw.rect(surface, entry.sky, picture, border_radius=11)
            clip = surface.get_clip()
            surface.set_clip(picture.clip(clip))
            entry.cover(surface, picture.center, now)
            surface.set_clip(clip)
            ui.text(surface, entry.title, (rect.x + 21, rect.y + 242), ui.WHITE, "lg")
            for row, line in enumerate(entry.description):
                ui.text(surface, line, (rect.x + 22, rect.y + 286 + row * 24), ui.MUTED, "sm")
            completed = entry.scene.ADVENTURE_ID in self.completed
            label = "Finished" if completed else "Ready to play"
            ui.text(surface, label, (rect.x + 22, rect.bottom - 44), border, "sm")

        if not unlocked or (index == self.reveal and reveal < 1):
            cover = pygame.Surface(rect.size, pygame.SRCALPHA)
            self.draw_back(cover, index)
            if unlocked:
                cover.set_alpha(round(255 * (1 - reveal)))
                cover_rect = rect.move(0, -round(26 * reveal))
            else:
                cover_rect = rect
            surface.blit(cover, cover_rect)
        if index == self.reveal and 0 < reveal < 1:
            for i in range(8):
                angle = i * math.tau / 8
                radius = reveal * 114 + 28
                point = (rect.centerx + math.cos(angle) * radius,
                         rect.y + 118 + math.sin(angle) * radius)
                ui.star(surface, point, max(3, round(9 * (1 - reveal))), color=border)

    @staticmethod
    def draw_back(surface, index):
        rect = surface.get_rect()
        pygame.draw.rect(surface, (37, 38, 67), rect, border_radius=18)
        pygame.draw.rect(surface, (100, 97, 140), rect, 1, border_radius=18)
        frame = rect.inflate(-28, -28)
        pygame.draw.rect(surface, (47, 47, 81), frame, border_radius=13)
        for i in range(8):
            angle = i * math.tau / 8
            x = round(rect.centerx + 69 * math.cos(angle))
            y = round(140 + 69 * math.sin(angle))
            pygame.draw.circle(surface, (100, 97, 140), (x, y), 2)
        pygame.draw.circle(surface, (111, 103, 148), (rect.centerx, 140), 54, 1)
        ui.text(surface, "?", (rect.centerx, 140), (203, 195, 218), "xl", center=True)
        ui.text(surface, "Mystery Card", (rect.centerx, 259), ui.WHITE, "lg", center=True)
        ui.text(surface, f"Finish Adventure {index}", (rect.centerx, 304), ui.MUTED, "sm", center=True)

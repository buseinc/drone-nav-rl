"""Inspect, unlock and equip player drones."""

import math

import pygame

from games.skyrush import common as ui
from games.skyrush.airframe_art import draw_airframe
from games.skyrush.airframes import (ANCHOR, BUMBLE, BY_KEY, CHARACTER_DRONES, CIRCUIT_STAGE_CREDITS,
                                     FINCH, FLIGHT_DRONES, JELLY, KESTREL, MISSION_STAR_CREDITS,
                                     MOTH, NEEDLE, ORBIT, PUDDLE, SPROUT,
                                     credits, equip_airframe, is_owned)
from games.skyrush.save import load_leaderboard
from src.shared.scene import Scene

BAY = pygame.Rect(54, 122, 632, 324)
DETAIL = pygame.Rect(705, 122, 341, 324)
ACTION = pygame.Rect(727, 371, 297, 43)
COLLECTIONS = (
    ("FLIGHT DRONES", pygame.Rect(54, 88, 168, 27), FLIGHT_DRONES),
    ("CHARACTER DRONES", pygame.Rect(232, 88, 210, 27), CHARACTER_DRONES),
)
SLOTS_PER_ROW = 4
SLOTS_PER_PAGE = 2 * SLOTS_PER_ROW


class HangarScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.board = load_leaderboard()
        self.tab = 0
        self.selected = self.equipped_index()
        self.notice = ""
        self.preview_start = pygame.time.get_ticks()

    @property
    def models(self):
        return COLLECTIONS[self.tab][2]

    @property
    def equipped(self):
        key = self.board.get("hangar", {}).get("equipped")
        return BY_KEY.get(key, KESTREL)

    def equipped_index(self):
        return self.models.index(self.equipped) if self.equipped in self.models else 0

    def switch_tab(self, index):
        if index != self.tab:
            self.tab = index
            self.choose(self.equipped_index())

    def slot(self, index):
        row_start = index - index % SLOTS_PER_ROW
        count = min(SLOTS_PER_ROW, len(self.models) - row_start)
        width = (992 - 14 * (SLOTS_PER_ROW - 1)) // SLOTS_PER_ROW
        left = (ui.WIDTH - (count * (width + 14) - 14)) // 2
        row = (index % SLOTS_PER_PAGE) // SLOTS_PER_ROW
        return pygame.Rect(left + (index % SLOTS_PER_ROW) * (width + 14), 462 + row * 93, width, 81)

    def choose(self, index):
        self.selected = index % len(self.models)
        self.notice = ""
        self.preview_start = pygame.time.get_ticks()
        self.app.sound.play("click")

    def activate(self):
        model = self.models[self.selected]
        if model == self.equipped:
            return
        already_owned = is_owned(self.board, model)
        if not equip_airframe(model):
            self.app.sound.play("lose")
            return
        self.board = load_leaderboard()
        self.notice = "Drone equipped" if already_owned else "Drone unlocked and equipped"
        self.app.sound.play("goal")

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, (_, rect, _) in enumerate(COLLECTIONS):
                if rect.collidepoint(event.pos):
                    self.switch_tab(index)
                    return
            if ACTION.collidepoint(event.pos):
                self.activate()
            else:
                for index in self.visible_slots():
                    if self.slot(index).collidepoint(event.pos):
                        self.choose(index)
                        break
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            from games.skyrush.menu import HANGAR, MenuScene
            self.app.change(MenuScene(self.app, selected=HANGAR))
        elif event.key in (pygame.K_LEFT, pygame.K_a):
            self.choose(self.selected - 1)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self.choose(self.selected + 1)
        elif event.key in (pygame.K_UP, pygame.K_w) and self.selected >= SLOTS_PER_ROW:
            self.choose(self.selected - SLOTS_PER_ROW)
        elif event.key in (pygame.K_DOWN, pygame.K_s) and self.selected // SLOTS_PER_ROW < (len(self.models) - 1) // SLOTS_PER_ROW:
            self.choose(min(self.selected + SLOTS_PER_ROW, len(self.models) - 1))
        elif event.key == pygame.K_TAB:
            self.switch_tab((self.tab + 1) % len(COLLECTIONS))
        elif event.key == pygame.K_RETURN:
            self.activate()

    def visible_slots(self):
        start = self.selected // SLOTS_PER_PAGE * SLOTS_PER_PAGE
        return range(start, min(start + SLOTS_PER_PAGE, len(self.models)))

    def draw(self, surf):
        now = pygame.time.get_ticks()
        model = self.models[self.selected]
        ui.draw_background(surf)
        ui.text(surf, "HANGAR", (54, 16), ui.WHITE, "xl")
        earnings = f"{MISSION_STAR_CREDITS} per mission star  /  {CIRCUIT_STAGE_CREDITS} per new Circuit stage"
        ui.text(surf, earnings, (1046, 67), ui.MUTED, "sm", right=True)
        ui.text(surf, f"{credits(self.board):,} credits", (1046, 24), ui.GOLD, "title", right=True)
        ui.text(surf, f"Equipped · {self.equipped.name}", (1046, 93), self.equipped.accent, "sm", right=True)
        for index, (label, rect, _) in enumerate(COLLECTIONS):
            selected = index == self.tab
            accent = (141, 216, 250) if index == 0 else (249, 181, 223)
            ui.glass(surf, rect, (39, 48, 79), alpha=220 if selected else 125,
                     border=accent if selected else (58, 74, 104), radius=7)
            ui.text(surf, label, rect.center, accent if selected else ui.MUTED, "key", center=True)
        self.draw_bay(surf, model, now)
        self.draw_details(surf, model)
        for index in self.visible_slots():
            self.draw_slot(surf, index, now)
        ui.hint_bar(surf, [("TAB", "collection"), ("WASD", "browse"), ("ENTER", "unlock or equip"),
                           ("ESC", "main menu")], y=665)

    def draw_bay(self, surf, model, now):
        ui.glass(surf, BAY, (19, 31, 52), alpha=248, border=(65, 88, 119), radius=15)
        x, y = BAY.centerx, 263
        for dx in range(-276, 280, 23):
            pygame.draw.line(surf, (33, 48, 71), (x + dx, BAY.top + 20), (x + dx, BAY.bottom - 25))
        for ty in range(BAY.top + 20, BAY.bottom - 25, 23):
            pygame.draw.line(surf, (33, 48, 71), (BAY.left + 35, ty), (BAY.right - 34, ty))
        for radius in (127, 109, 94):
            tint = ui.lerp_color((19, 31, 52), model.accent, 0.28 if radius == 109 else 0.20)
            pygame.draw.circle(surf, tint, (x, y), radius, 1)
        color = ui.lerp_color((19, 31, 52), model.accent, 0.72)
        for dx, dy in ((-151, -85), (-151, 85), (151, -85), (151, 85)):
            pygame.draw.line(surf, color, (x + dx, y + dy), (x + dx * 7 // 8, y + dy), 2)
        ui.text(surf, model.hardware.upper(), (77, 147), model.accent, "key")
        elapsed = now - self.preview_start
        lift = min(1, elapsed / 520)
        rise = 1 - (1 - lift) ** 3
        pulse = (elapsed % 2100) / 2100
        if model in (MOTH, ANCHOR):
            start, end = (54, 113) if model == MOTH else (77, 124)
            radius = round(start + (end - start) * pulse)
            tint = ui.lerp_color((19, 31, 52), model.accent, (1 - pulse) * 0.46)
            pygame.draw.circle(surf, tint, (x, y), radius, 2)
        dash = math.sin(math.pi * ((pulse - 0.62) / 0.30)) if 0.62 < pulse < 0.92 else 0
        offset = round(dash * 18) if model in (NEEDLE, JELLY) else -round(dash * 18) if model == BUMBLE else 0
        landed = model in (PUDDLE, SPROUT, FINCH, ORBIT) and pulse > 0.80
        if model == ORBIT and not landed:
            offset = round(math.sin(pulse * math.tau) * 12)
        draw_airframe(surf, (x + offset, y + round(21 * (1 - rise)) - 6 + (12 if landed else 0)),
                      round(210 + 19 * rise), model, now, thrust=bool(offset),
                      powered=bool(offset) or (model == ANCHOR and pulse < 0.25), landed=landed)
        self.draw_demo(surf, model, elapsed)

    @staticmethod
    def draw_demo(surf, model, now):
        if model not in (NEEDLE, MOTH, ANCHOR, BUMBLE, JELLY, SPROUT):
            return
        start = 316
        top = 398
        for index in range(3):
            y = top - 8 if model == JELLY and index == 2 else top
            tile = pygame.Rect(start + 37 * index, y, 32, 24)
            pygame.draw.rect(surf, (34, 49, 75), tile, border_radius=5)
        center = top + 12
        phase = (now // 380) % 3
        if model in (NEEDLE, BUMBLE, JELLY):
            cols = {NEEDLE: (0, 0, 2), BUMBLE: (0, 1, 0), JELLY: (0, 0, 2)}[model]
            x = start + 16 + 37 * cols[phase]
            y = center - 8 if model == JELLY and phase == 2 else center
            if phase == 2:
                route = [(start + 53, center) if model == BUMBLE else (start + 16, center)]
                if model == JELLY:
                    route.append((start + 53, center))
                route.append((x, y))
                pygame.draw.lines(surf, ui.lerp_color((34, 49, 75), model.accent, 0.60), False, route, 2)
            pygame.draw.circle(surf, model.accent, (x, y), 5)
        elif model == MOTH:
            pygame.draw.circle(surf, ui.ENEMY, (start + 16, center), 5)
            pygame.draw.rect(surf, ui.ENEMY, (start + 45, center - 8, 16, 16), 1, border_radius=3)
            pygame.draw.circle(surf, model.accent, (start + 90, center), 7 + phase, 2)
        else:
            for index in range(3):
                ui.draw_arrow(surf, (start + 16 + 37 * index, center), 3, 7, ui.WIND_ARROW, 1)
            marker = start + (90 if model == SPROUT else 53)
            pygame.draw.circle(surf, model.accent, (marker, center), 9 + phase, 2)

    def draw_details(self, surf, model):
        ui.glass(surf, DETAIL, (26, 36, 61), alpha=246, border=model.accent, radius=15)
        ui.text(surf, model.role.upper(), (727, 142), model.accent, "key")
        ui.text(surf, model.name, (725, 160), ui.WHITE, "xl")
        ui.text(surf, model.power, (728, 230), model.accent, "lg")
        for row, line in enumerate(model.description):
            ui.text(surf, line, (728, 270 + row * 22), ui.WHITE, "sm")
        if model.price:
            ui.text(surf, "Powers: solo missions and solo Circuit stages", (728, 323), ui.MUTED, "xs")
        selected = self.equipped == model
        owned = is_owned(self.board, model)
        balance = credits(self.board)
        buyable = balance >= model.price
        available = not selected and (owned or buyable)
        if not owned:
            meter = pygame.Rect(ACTION.x, 355, ACTION.width, 5)
            pygame.draw.rect(surf, (47, 61, 90), meter, border_radius=2)
            meter.width = round(meter.width * min(1, balance / model.price))
            if meter.width:
                pygame.draw.rect(surf, model.accent, meter, border_radius=2)
        pygame.draw.rect(surf, model.accent if available else (47, 61, 90), ACTION, border_radius=9)
        label = "Equipped" if selected else "Equip drone" if owned else f"Unlock for {model.price:,} credits"
        ui.text(surf, label, ACTION.center, ui.SKY_TOP if available else ui.MUTED, "md", center=True)
        if self.notice:
            ui.text(surf, self.notice, (728, 419), model.accent, "sm")
        elif not owned and not buyable:
            ui.text(surf, f"{model.price - balance:,} more credits to unlock", (728, 419), ui.MUTED, "sm")

    def draw_slot(self, surf, index, now):
        model = self.models[index]
        rect = self.slot(index)
        selected = index == self.selected
        equipped = self.equipped == model
        ui.glass(surf, rect, (28, 39, 66), alpha=237 if selected else 160,
                 border=model.accent if selected else (53, 67, 98), radius=11)
        draw_airframe(surf, (rect.left + 40, rect.centery - 3), 60, model, now)
        ui.text(surf, model.name, (rect.left + 78, rect.top + 13), ui.WHITE, "lg")
        status = "Equipped" if equipped else "Owned" if is_owned(self.board, model) else f"{model.price:,} credits"
        ui.text(surf, status, (rect.left + 78, rect.top + 46), model.accent, "sm")

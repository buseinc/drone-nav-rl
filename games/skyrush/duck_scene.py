"""Guide a line of ducklings home across a changing stream."""

import pygame

from games.skyrush import common as ui
from games.skyrush import duck_art as art
from games.skyrush.duck_rescue import CALM_MS, COLS, CYCLE_MS, DUCKLINGS, NEST, ROWS, DuckRescue, distance
from games.skyrush.save import complete_adventure
from src.drone_env_v4 import DIRS
from src.shared.effects import Effects
from src.shared.scene import Scene

STEP_MS = 170
PAPER = (250, 242, 214)
INK = (49, 69, 67)
MUTED = (72, 96, 83)


class DuckRescueScene(Scene):
    ADVENTURE_ID = "duck_rescue"

    def __init__(self, app):
        super().__init__(app)
        self.family = DuckRescue()
        self.phase = "ready"
        self.previous = self.family.positions.copy()
        self.leader_from = self.family.leader
        self.facing = {}
        self.clock = STEP_MS
        self.queued = None
        self.notice = ""
        self.notice_ms = 0
        self.notice_warning = False
        self.first_clear = False
        self.fx = Effects()

    def leave(self):
        from games.skyrush.adventures import AdventureScene
        self.app.change(AdventureScene.after_visit(self.app, self.ADVENTURE_ID, self.first_clear))

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        key = event.key
        if key == pygame.K_ESCAPE or (key == pygame.K_RETURN and self.phase == "finished"):
            self.leave()
        elif key == pygame.K_r:
            self.app.change(DuckRescueScene(self.app))
        elif key == pygame.K_RETURN and self.phase == "ready":
            self.phase = "active"
            self.app.sound.play("go")
        elif self.phase == "active":
            if key in ui.KEY_TO_ACTION:
                self.queued = ui.KEY_TO_ACTION[key]
            elif key == pygame.K_SPACE:
                if self.family.call():
                    self.app.sound.play("click")
                    self.notice = "A duckling joined you!"
                else:
                    self.notice = "Get closer to a duckling."
                self.notice_warning = False
                self.notice_ms = 1700

    def update(self, dt):
        self.fx.update(dt)
        if self.phase != "active":
            return
        family = self.family
        detached, rescued = family.detached, len(family.rescued)
        family.advance(dt)
        self.notice_ms = max(0, self.notice_ms - dt)
        self.clock = min(STEP_MS, self.clock + dt)
        if self.clock >= STEP_MS:
            action = self.queued if self.queued is not None else ui.held_action()
            self.queued = None
            if action is not None and action < len(DIRS):
                self.walk(DIRS[action])
        if family.detached != detached:
            self.notice = ("ORCA startled the ducklings!" if family.detached_by == "orca"
                           else "The current split the group!")
            self.notice_ms = 2900
            self.notice_warning = True
            self.app.sound.play("beep")
        if len(family.rescued) != rescued:
            self.fx.celebrate(art.point(family.leader), (250, 219, 125))
            self.app.sound.play("goal")
        if family.finished:
            self.first_clear = complete_adventure(self.ADVENTURE_ID)
            self.phase = "finished"

    def walk(self, direction):
        family = self.family
        old, before = family.leader, family.positions.copy()
        if not family.move(direction):
            return
        self.leader_from, self.previous = old, before
        self.clock = 0
        for index, pos in ((-1, family.leader), *family.positions.items()):
            from_pos = old if index == -1 else before[index]
            if pos[1] != from_pos[1]:
                self.facing[index] = pos[1] < from_pos[1]

    def draw(self, surface):
        now = pygame.time.get_ticks()
        surface.fill((50, 82, 79))
        pygame.draw.rect(surface, (62, 97, 90), (0, 0, ui.WIDTH, 117))
        ui.text(surface, "Duckling Rescue", (45, 22), art.CREAM, "xl")
        ui.text(surface, "Call the ducklings and lead them home. Stay out of ORCA's light.",
                (49, 85), (221, 238, 194), "md")

        frame = pygame.Rect(*art.ORIGIN, COLS * art.CELL, ROWS * art.CELL).inflate(14, 14)
        pygame.draw.rect(surface, (143, 178, 132), frame, border_radius=9)
        art.draw_river(surface, self.family.tide, now)
        art.draw_nest(surface)
        art.draw_orca_light(surface, self.family.orca_row, self.family.scan_right)
        self.draw_family(surface, now)
        art.draw_orca(surface, self.family.orca_row, now)
        self.fx.draw(surface)
        self.draw_hud(surface, now)

        if self.phase == "ready":
            self.message(surface, "Quack, Quack!", "Three ducklings are waiting across the river.", "Enter  ·  Start")
        elif self.phase == "finished":
            self.message(surface, "Everyone's Home!", "All three ducklings are safe in the nest.",
                         "Enter  ·  Back to adventures")
        ui.hint_bar(surface, [("ARROWS", "move"), ("SPACE", "call ducklings"),
                             ("R", "restart"), ("ESC", "adventures")], y=671)

    def draw_family(self, surface, now):
        family = self.family
        phase = self.clock / STEP_MS if self.phase == "active" else 1
        actors = []
        birds = [(-1, family.leader), *family.positions.items()]
        nest_x, nest_y = art.point(NEST)
        for offset, index in enumerate(sorted(family.rescued)):
            art.draw_duck(surface, (nest_x - 16 + offset * 16, nest_y + 12), now,
                          index=index, asleep=True, scale=0.62)
        for index, tile in birds:
            old = self.leader_from if index == -1 else self.previous.get(index, tile)
            if distance(old, tile) > 1:
                old = tile
            draw_tile = tuple(a + (b - a) * phase for a, b in zip(old, tile))
            x, y = art.point(draw_tile)
            if index != -1 and sum(p == tile for _, p in birds) > 1:
                x += (index - 1) * 8
                y += 5
            actors.append((y, x, index, old != tile and phase < 1))
        for y, x, index, moving in sorted(actors):
            asleep = index != -1 and index not in family.followers
            art.draw_duck(surface, (x, y), now, index=max(0, index), adult=index == -1,
                          facing_left=self.facing.get(index, False), moving=moving,
                          asleep=asleep, scale=0.98 if index == -1 else 0.73)
            if asleep:
                near = distance(family.leader, family.positions[index]) <= 1
                ui.text(surface, "SPACE" if near else "z", (x, y - 25),
                        INK if near else (73, 112, 103), "xs", center=True)

    def draw_hud(self, surface, now):
        panel = pygame.Rect(797, 134, 258, 490)
        pygame.draw.rect(surface, PAPER, panel, border_radius=15)
        pygame.draw.rect(surface, (211, 192, 136), panel, 2, border_radius=15)
        family = self.family
        ui.text(surface, "At the Nest", (820, 158), INK, "lg")
        ui.text(surface, f"{len(family.rescued)} / {len(DUCKLINGS)}", (1030, 164), INK, "num", right=True)
        for i in range(len(DUCKLINGS)):
            x = 850 + i * 65
            pygame.draw.circle(surface, (226, 215, 176), (x, 220), 21)
            if i in family.rescued:
                art.draw_duck(surface, (x, 220), now, index=i, asleep=True, scale=0.64)
        ui.text(surface, f"Following you: {len(family.followers)}", (820, 258), MUTED, "md")

        pygame.draw.line(surface, (210, 194, 148), (820, 301), (1031, 301))
        ui.text(surface, "River Current", (820, 321), INK, "lg")
        states = {"calm": ("Calm water", (60, 113, 94)),
                  "warning": ("Current rising!", (155, 103, 43)),
                  "surge": ("Strong current", (159, 76, 63))}
        label, color = states[family.tide]
        ui.text(surface, label, (820, 361), color, "md")
        track = pygame.Rect(821, 398, 209, 8)
        pygame.draw.rect(surface, (217, 190, 153), track, border_radius=4)
        pygame.draw.rect(surface, (126, 173, 148), (track.x, track.y, track.width * CALM_MS // CYCLE_MS, 8),
                         border_radius=4)
        x = track.x + track.width * (family.elapsed % CYCLE_MS) // CYCLE_MS
        pygame.draw.circle(surface, color, (x, track.centery), 6)
        ui.text(surface, "The bridge stays above water.", (820, 429), MUTED, "sm")
        ui.text(surface, "Use the stones in calm water.", (820, 453), MUTED, "sm")
        ui.text(surface, "ORCA also scans the far bank.", (820, 477), MUTED, "sm")
        if self.notice_ms:
            tone = (159, 76, 63) if self.notice_warning else MUTED
            ui.text(surface, self.notice, (820, 528), tone, "sm")
            if self.notice_warning:
                ui.text(surface, "Go back and call them again.", (820, 552), MUTED, "sm")

    @staticmethod
    def message(surface, headline, caption, action):
        box = pygame.Rect(168, 283, 480, 155)
        pygame.draw.rect(surface, (96, 126, 99), box.move(0, 5), border_radius=14)
        pygame.draw.rect(surface, PAPER, box, border_radius=14)
        pygame.draw.rect(surface, (215, 185, 129), box, 2, border_radius=14)
        ui.text(surface, headline, (box.centerx, 319), INK, "title", center=True)
        ui.text(surface, caption, (box.centerx, 365), MUTED, "md", center=True)
        ui.text(surface, action, (box.centerx, 403), (118, 86, 54), "lg", center=True)

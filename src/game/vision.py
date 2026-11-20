"""AI Vision: an interactive look inside the DQN.

Shows, live:
  * the five Q-values the network outputs for the drone's current cell,
  * the exact observation the network receives ("AI's eyes"): walls,
    visited cells, wind, enemies now and enemies on the next tick,
  * a policy heat-map: for every free cell, what the AI would do there.
The map can be edited with the mouse while the AI flies.
"""

import numpy as np
import pygame

from src.drone_env_v4 import HOVER
from src.game import common as ui
from src.game.agent import softmax
from src.game.drone_ctrl import MOVE_MS, DroneController
from src.game.effects import Effects
from src.game.scene import Scene
from src.game.world import AI_NAME, ARENAS, copy_env, make_env

CELL = 56
ORIGIN = (40, 100)
SPEEDS = [900, 550, 300, 150, 60]   # ms between AI steps
HEAT_LOW = (48, 38, 92)
HEAT_HIGH = (40, 150, 110)

# H cycles through these. Each entry: (name, explanation lines)
HEAT_MODES = [
    ("off", ["Heat-map off."]),
    ("certainty", [
        "Certainty = gap between best and 2nd-best Q.",
        "Bright: AI is sure.  Dark: AI hesitates here,",
        "this is where it is most likely to make mistakes.",
    ]),
    ("value", [
        "Value = max Q. Far cells look BETTER than near",
        "ones: every step closer pays a bonus, so far away",
        "there is more bonus left to collect.",
    ]),
]


class VisionScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        self.agent = app.agent
        self.arena = app.settings["arena"]
        self.base = make_env(self.arena)
        self.fx = Effects()
        self.speed = 2
        self.autoplay = False
        self.heat = 1   # index into HEAT_MODES
        self.show_view = True
        self.restart(new_map=False)

    # ---------- state ----------

    def restart(self, new_map):
        if new_map:
            self.base = make_env(self.arena)
        self.env = copy_env(self.base)
        self.ctrl = DroneController(self.env)
        self.done = False
        self.crashed = False
        self.status = "SPACE: one step   A: autoplay"
        self.clock = 0
        self.refresh()

    def px(self):
        return ui.cell_center(ORIGIN, CELL, self.ctrl.pos())

    def refresh(self):
        self.state = self.env.get_state()
        self.q = self.agent.q_values(self.state)
        self.probs = softmax(self.q)
        self.policy = self.agent.policy_map(self.env)

    def step(self):
        if self.done or not self.ctrl.can_move:
            return
        self.ctrl.move(int(np.argmax(self.q)))
        self.refresh()

    def land(self, event):
        self.done = True
        self.autoplay = False
        if event == "goal":
            self.fx.celebrate(self.px(), ui.DRONE)
            self.app.sound.play("goal")
        elif event == "crash":
            self.crashed = True
            self.fx.explosion(self.px())
            self.app.sound.play("crash")
            self.app.shake(10)
        self.status = {
            "goal": f"GOAL in {self.env.steps} ticks "
                    f"(best possible {self.base.optimal_length()}). "
                    "Right-click to move the goal!",
            "crash": "CRASH! Press R to retry.",
            "timeout": "TIMEOUT - the AI got stuck in a loop.",
        }[event]

    def edit(self, cell, button):
        e = self.env
        if cell is None or cell == e.position:
            return
        tracks = {c for en in e.enemies for c in en["track"]}
        if button == 1 and cell != e.goal:          # toggle wall
            if cell in e.obstacles:
                e.obstacles.remove(cell)
            elif cell in tracks:
                self.status = "Can't build on a patrol track."
                return
            else:
                e.obstacles.add(cell)
                e.wind.pop(cell, None)
        elif button == 3 and cell not in e.obstacles:   # move goal
            e.goal = cell
            if self.done and not self.crashed and e.position != e.goal:
                self.done = False       # keep flying to the new goal
                self.ctrl.resume()
                e.steps = 0
                self.status = "New goal! Watch the policy change."
        else:
            return
        e.refresh_distances()
        if e.get_distance() < 0:
            self.status = "Goal unreachable - remove a wall."
        self.refresh()

    # ---------- scene API ----------

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.edit(ui.cell_at(ORIGIN, CELL, self.env.grid_size,
                                 event.pos), event.button)
            return
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if k == pygame.K_ESCAPE:
            from src.game.menu import MenuScene
            self.app.change(MenuScene(self.app, selected=2))
        elif k == pygame.K_SPACE:
            self.autoplay = False
            self.step()
        elif k == pygame.K_a:
            self.autoplay = not self.autoplay and not self.done
        elif k in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.speed = min(len(SPEEDS) - 1, self.speed + 1)
        elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.speed = max(0, self.speed - 1)
        elif k == pygame.K_h:
            self.heat = (self.heat + 1) % len(HEAT_MODES)
        elif k == pygame.K_v:
            self.show_view = not self.show_view
        elif k == pygame.K_r:
            self.restart(new_map=False)
        elif k == pygame.K_n:
            self.restart(new_map=True)
        elif pygame.K_1 <= k <= pygame.K_4:
            self.arena = k - pygame.K_1
            self.app.settings["arena"] = self.arena
            self.restart(new_map=True)

    def update(self, dt):
        self.fx.update(dt)
        # Flight animation never takes longer than the time between steps.
        self.ctrl.move_ms = min(MOVE_MS, SPEEDS[self.speed] * 0.8)
        if self.ctrl.busy:
            self.fx.trail(self.px(), ui.lerp_color(ui.DRONE, ui.BG, 0.4))
        event = self.ctrl.update(dt)
        if event:
            self.land(event)
        if self.autoplay and not self.done:
            self.clock += dt
            if self.clock >= SPEEDS[self.speed] and self.ctrl.can_move:
                self.clock = 0
                self.step()

    # ---------- drawing ----------

    def draw(self, surf):
        ui.draw_background(surf)
        ui.text(surf, "NEURAL LAB", (40, 26), ui.DRONE, "title")
        ui.text(surf, f"Inside {AI_NAME}'s mind", (260, 40), ui.MUTED, "sm")
        for i, a in enumerate(ARENAS):     # arena tabs (keys 1-4)
            sel = i == self.arena
            r = ui.text(surf, f"{i + 1} {a['name']}",
                        (ui.WIDTH - 40 - (3 - i) * 165, 40),
                        a["color"] if sel else ui.DIM, "sm", right=True)
            if sel:
                pygame.draw.line(surf, a["color"], (r.left, r.bottom + 2),
                                 (r.right, r.bottom + 2), 2)
        self.draw_board(surf)
        self.draw_panel(surf)
        ui.text(surf, self.status, (40, 672), ui.WHITE, "md")

    def draw_board(self, surf):
        e = self.env
        colors = None
        if self.heat and self.policy:
            idx = self.heat   # 1 -> gap (certainty), 2 -> max Q (value)
            vals = {p: (v[2] if idx == 1 else v[1])
                    for p, v in self.policy.items()}
            arr = np.array(list(vals.values()))
            if idx == 1:
                # A few cells have huge gaps (e.g. next to a wall); clip at
                # the 90th percentile so the rest of the map is readable.
                lo, hi = 0.0, float(np.percentile(arr, 90))
            else:
                lo, hi = float(arr.min()), float(arr.max())
            span = (hi - lo) or 1.0
            colors = {p: ui.lerp_color(HEAT_LOW, HEAT_HIGH, (v - lo) / span)
                      for p, v in vals.items()}

        ui.draw_grid(surf, e, ORIGIN, CELL, colors)

        if self.heat:
            for p, (a, _, _) in self.policy.items():
                if p != e.position:
                    ui.draw_arrow(surf, ui.cell_center(ORIGIN, CELL, p), a,
                                  14, (210, 220, 235), 2)

        ui.draw_path(surf, e.path, ORIGIN, CELL, ui.DRONE, 4)
        ui.draw_enemies(surf, e, ORIGIN, CELL, e.t, self.ctrl.t,
                        warn=not self.done)

        if self.show_view:
            half = e.VIEW // 2
            r, c = e.position
            rect = pygame.Rect(ORIGIN[0] + (c - half) * CELL - 2,
                               ORIGIN[1] + (r - half) * CELL - 2,
                               e.VIEW * CELL + 1, e.VIEW * CELL + 1)
            board = pygame.Rect(ORIGIN[0] - 4, ORIGIN[1] - 4,
                                CELL * e.grid_size + 5,
                                CELL * e.grid_size + 5)
            surf.set_clip(board)
            pygame.draw.rect(surf, ui.GOLD, rect, 2, border_radius=8)
            surf.set_clip(None)

        if not self.crashed:
            # Q-value arrows on the drone: longer = more preferred
            center = self.px()
            best = int(np.argmax(self.q))
            for a in range(len(self.q)):
                length = 18 + 34 * float(self.probs[a])
                color = ui.GOAL if a == best else ui.MUTED
                ui.draw_arrow(surf, center, a, length, color,
                              4 if a == best else 2)
            ui.draw_drone(surf, self.ctrl.pos(), ORIGIN, CELL, ui.DRONE)
        self.fx.draw(surf)

    def draw_panel(self, surf):
        x, w = 650, 410
        ui.panel(surf, pygame.Rect(x - 18, 100, w + 20, 577))
        ui.text(surf, "WHAT THE AI THINKS", (x, 112), ui.DRONE, "lg")

        # Q-value bars
        best = int(np.argmax(self.q))
        lo, hi = float(self.q.min()), float(self.q.max())
        span = (hi - lo) or 1.0
        for a in range(len(self.q)):
            y = 146 + a * 26
            sel = a == best
            ui.text(surf, ui.ACTION_NAMES[a], (x, y),
                    ui.WHITE if sel else ui.MUTED, "md")
            frac = 0.08 + 0.92 * (self.q[a] - lo) / span
            bar = pygame.Rect(x + 80, y + 2, int(230 * frac), 17)
            pygame.draw.rect(surf, ui.GOAL if sel else ui.DIM, bar,
                             border_radius=4)
            ui.text(surf, f"{self.q[a]:7.2f}", (x + w - 8, y),
                    ui.WHITE if sel else ui.MUTED, "md", right=True)

        d = self.env.get_distance()
        ui.text(surf, f"Confidence {100 * self.probs[best]:4.1f}%   "
                      f"max Q {hi:.2f}", (x, 280), ui.WHITE, "sm")
        ui.text(surf, f"Distance to goal: {d if d >= 0 else '-'}   "
                      f"tick {self.env.steps}/{self.env.max_steps}",
                (x, 301), ui.MUTED, "sm")

        self.draw_eyes(surf, x, 330)

        lines = ["Q(s,a) = total future reward the AI expects if it",
                 "takes action a now, then keeps following its policy."]
        for i, line in enumerate(lines):
            ui.text(surf, line, (x, 482 + i * 16), ui.MUTED, "xs")
        for i, line in enumerate(HEAT_MODES[self.heat][1]):
            ui.text(surf, line, (x, 520 + i * 15), ui.GOLD, "xs")

        on = lambda flag: "on" if flag else "off"   # noqa: E731
        controls = [
            f"SPACE step   A auto ({on(self.autoplay)})   "
            f"+/- speed {self.speed + 1}/{len(SPEEDS)}",
            f"H heat-map ({HEAT_MODES[self.heat][0]})   "
            f"V view box ({on(self.show_view)})",
            "Left click: wall   Right click: move goal",
            "R restart   N new map   1-4 arena   Esc menu",
        ]
        for i, line in enumerate(controls):
            ui.text(surf, line, (x, 590 + i * 19), ui.WHITE, "xs")

    def draw_eyes(self, surf, x, y):
        """Draw the raw observation exactly as the network receives it."""
        v = self.env.VIEW
        n = v * v
        ch = {name: self.state[i * n:(i + 1) * n].reshape(v, v)
              for i, name in enumerate(self.env.CHANNELS)}
        goal = self.state[len(self.env.CHANNELS) * n:]

        ui.text(surf, f"AI'S EYES  ({len(self.state)} numbers in)", (x, y),
                ui.GOLD, "md")
        s = 18
        top = y + 26
        for i in range(v):
            for j in range(v):
                rect = pygame.Rect(x + j * s, top + i * s, s - 2, s - 2)
                if ch["walls"][i, j] > 0:
                    color = ui.OBSTACLE
                elif ch["wind_row"][i, j] or ch["wind_col"][i, j]:
                    color = ui.WIND
                else:
                    vis = ch["visited"][i, j]
                    color = ui.lerp_color(ui.EMPTY, ui.DRONE,
                                          0.25 + 0.75 * vis if vis else 0)
                pygame.draw.rect(surf, color, rect, border_radius=2)
                wr, wc = ch["wind_row"][i, j], ch["wind_col"][i, j]
                if wr or wc:
                    c = rect.center
                    pygame.draw.line(surf, ui.WIND_ARROW, c,
                                     (c[0] + wc * 6, c[1] + wr * 6), 2)
                if ch["enemy_now"][i, j]:
                    pygame.draw.circle(surf, ui.ENEMY, rect.center, 5)
                if ch["enemy_next"][i, j]:
                    pygame.draw.rect(surf, ui.ENEMY, rect, 2, border_radius=2)
        mid = v // 2
        pygame.draw.rect(surf, ui.WHITE,
                         pygame.Rect(x + mid * s, top + mid * s, s - 2,
                                     s - 2), 2, border_radius=2)

        gx = x + v * s + 18
        legend = [("red    wall", ui.OBSTACLE), ("blue   visited", ui.DRONE),
                  ("teal   wind", ui.WIND_ARROW),
                  ("dot    enemy now", ui.ENEMY),
                  ("frame  enemy next tick", ui.ENEMY)]
        for i, (label, color) in enumerate(legend):
            ui.text(surf, label, (gx, top + i * 17), color, "xs")
        ui.text(surf, f"goal: row {int(goal[0]):+d} ({goal[2]:+.2f})  "
                      f"col {int(goal[1]):+d} ({goal[3]:+.2f})",
                (gx, top + 92), ui.GOAL, "xs")
        if self.q.argmax() == HOVER:
            ui.text(surf, "AI chooses to WAIT this tick", (gx, top + 110),
                    ui.GOLD, "xs")

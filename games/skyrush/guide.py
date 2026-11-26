"""Flight Guide: every rule explained with a small live demo."""

import pygame

from src.drone_env_v4 import DroneEnvV4
from games.skyrush import common as ui
from src.shared.drone_ctrl import DroneController
from src.shared.effects import Effects
from src.shared.pathfinding import best_action
from src.shared.scene import Scene
from src.shared.world import AI_NAME, LEVELS


class Demo:
    """A tiny map flown automatically, looping forever."""

    def __init__(self, grid, start, goal, obstacles=(), wind=None,
                 enemies=None, cell=48, pilot=None, fog=False, dots=False):
        self.spec = dict(start=start, goal=goal, obstacles=set(obstacles),
                         wind=wind or {}, enemies=enemies or [])
        self.env = DroneEnvV4(seed=0, grid_size=grid, obstacle_count=0)
        self.cell, self.pilot, self.fog, self.dots = cell, pilot, fog, dots
        self.fx = Effects()
        self.restart()

    def restart(self):
        self.env.set_map(**self.spec)
        self.ctrl = DroneController(self.env, 330)
        self.optimal = self.env.optimal_route()[1]
        self.gap = 600
        self.done_for = None

    def update(self, dt, origin):
        self.fx.update(dt)
        event = self.ctrl.update(dt)
        px = ui.cell_center(origin, self.cell, self.ctrl.pos())
        if self.ctrl.busy:
            self.fx.trail(px, ui.lerp_color(ui.PLAYER, ui.BG, 0.4))
        if event:
            self.done_for = 0
            if event == "goal":
                self.fx.celebrate(px, ui.PLAYER)
            else:
                self.fx.explosion(px)
        if self.done_for is not None:
            self.done_for += dt
            if self.done_for > 1500:
                self.restart()
            return
        if self.ctrl.can_move:
            self.gap -= dt
            if self.gap <= 0:
                self.gap = 90
                action = (self.pilot.act(self.env.get_state()) if self.pilot
                          else best_action(self.env))
                self.ctrl.move(action)

    def draw(self, surf, origin):
        e, cell = self.env, self.cell
        visible = ui.view_cells(e) if self.fog else None
        ui.draw_grid(surf, e, origin, cell, visible=visible)
        ui.draw_enemies(surf, e, origin, cell, e.t, self.ctrl.t, visible)
        if self.dots:
            ui.draw_dots(surf, self.optimal, origin, cell, ui.WHITE, 4)
        ui.draw_path(surf, e.path, origin, cell,
                     ui.lerp_color(ui.PLAYER, ui.BG, 0.35), 4)
        if self.done_for is None or e.position == e.goal:
            color = ui.DRONE if self.pilot else ui.PLAYER
            ui.draw_drone(surf, self.ctrl.pos(), origin, cell, color)
        self.fx.draw(surf)


def build_pages(agent):
    D, R = (1, 0), (0, 1)
    return [
        {"title": "TAKE OFF", "color": ui.PLAYER,
         "lines": ["Hold an arrow key (or WASD) to fly.",
                   "The whole world moves on one beat: every",
                   "tick, every drone makes exactly one move.",
                   "Mashing keys won't make you faster -",
                   "a smart route will."],
         "keys": [("ARROWS", "fly"), ("SPACE", "hover")],
         "demo": Demo(6, (5, 0), (0, 5), {(3, 1), (3, 2), (1, 3), (2, 4),
                                          (4, 4)})},
        {"title": "LAND FIRST", "color": ui.GOAL,
         "lines": ["Fly to the green ring to land.",
                   "Fewer ticks = more stars:",
                   "3 stars = the best possible route",
                   "(the white dots), 2 stars = close to it.",
                   "In a duel, whoever lands first wins."],
         "stars": True,
         "demo": Demo(6, (0, 0), (5, 5), {(1, 1), (1, 2), (3, 3), (3, 4),
                                          (4, 1)}, dots=True)},
        {"title": "RIDE THE WIND", "color": ui.WIND_ARROW,
         "lines": ["Wind cells push your drone along the",
                   "arrows - several cells in a single tick.",
                   "Ride a stream as a shortcut...",
                   "...or get blown far off course."],
         "demo": Demo(6, (5, 0), (0, 5), {(2, 0), (2, 1), (2, 2), (0, 2)},
                      wind={(4, 1): R, (4, 2): R, (4, 3): R, (4, 4): R})},
        {"title": "DODGE THE PATROLS", "color": ui.ENEMY,
         "lines": ["Pink security drones patrol back and forth.",
                   "Touch one and you crash.",
                   "The pink frame shows where each one will",
                   "be on the NEXT tick. Press SPACE to hover",
                   "and let it pass."],
         "keys": [("SPACE", "hover one tick")],
         "demo": Demo(6, (5, 2), (0, 2), {(2, 0), (2, 1), (2, 3), (2, 4),
                                          (2, 5)},
                      enemies=[{"track": [(1, 0), (1, 1), (1, 2), (1, 3),
                                          (1, 4), (1, 5)], "phase": 0},
                               {"track": [(3, 0), (3, 1), (3, 2), (3, 3),
                                          (3, 4)], "phase": 5}])},
        {"title": "FOG OF WAR", "color": ui.MUTED,
         "lines": ["Turn on fog in a Duel and you only see",
                   "the 7x7 area around your drone.",
                   f"That is exactly what {AI_NAME} sees -",
                   "now it's a truly fair fight."],
         "keys": [("F", "toggle fog in duel setup")],
         "demo": Demo(10, (9, 0), (0, 9), {(7, 1), (7, 2), (5, 4), (4, 4),
                                           (2, 6), (2, 7), (6, 8), (1, 2)},
                      cell=30, fog=True)},
        {"title": f"MEET {AI_NAME}", "color": ui.DRONE,
         "lines": [f"{AI_NAME} is a neural network that taught",
                   "itself to fly in 12,000 practice flights.",
                   "Nobody programmed its route. It only got",
                   "rewards: +10 for landing, -10 for crashing,",
                   "a small bonus for getting closer."],
         "levels": True,
         "demo": Demo(8, (7, 0), (0, 7), {(5, 1), (5, 2), (5, 3), (2, 4),
                                          (3, 4), (1, 6), (6, 6)},
                      wind={(4, 5): (-1, 0), (3, 5): (-1, 0)},
                      cell=38, pilot=agent if agent.available else None)},
        {"title": "NEURAL LAB", "color": ui.DRONE,
         "lines": [f"Open the Neural Lab to see what {AI_NAME}",
                   "thinks: the value of every move, the 7x7",
                   "'eyes' it sees with, and a heat-map of its",
                   "plan. Build walls with the mouse and watch",
                   "it change its mind."],
         "lab": True},
    ]


class GuideScene(Scene):
    def __init__(self, app, page=0):
        super().__init__(app)
        self.pages = build_pages(app.agent)
        self.page = page

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if k == pygame.K_ESCAPE:
            from games.skyrush.menu import MenuScene
            self.app.change(MenuScene(self.app, selected=3))
        elif k in (pygame.K_RIGHT, pygame.K_d, pygame.K_RETURN,
                   pygame.K_SPACE):
            if self.page < len(self.pages) - 1:
                self.page += 1
                self.app.sound.play("click")
            elif k == pygame.K_RETURN:
                from games.skyrush.menu import MenuScene
                self.app.change(MenuScene(self.app, selected=0))
        elif k in (pygame.K_LEFT, pygame.K_a) and self.page > 0:
            self.page -= 1
            self.app.sound.play("click")

    def demo_origin(self, demo):
        size = demo.cell * demo.env.grid_size
        return (760 - size // 2, 360 - size // 2)

    def update(self, dt):
        demo = self.pages[self.page].get("demo")
        if demo:
            demo.update(dt, self.demo_origin(demo))

    def draw(self, surf):
        self.app.sky.draw(surf, skyline=False)
        p = self.pages[self.page]
        ui.text(surf, "FLIGHT GUIDE", (60, 30), ui.MUTED, "lg")
        ui.text(surf, f"{self.page + 1} / {len(self.pages)}",
                (ui.WIDTH - 60, 34), ui.MUTED, "md", right=True)

        left = pygame.Rect(50, 90, 440, 540)
        ui.glass(surf, left, alpha=200)
        pygame.draw.rect(surf, p["color"], (50, 90, 440, 6),
                         border_top_left_radius=18,
                         border_top_right_radius=18)
        big = ui.render(p["title"], "xl", p["color"]).get_width() <= 390
        ui.text(surf, p["title"], (78, 122 if big else 136), p["color"],
                "xl" if big else "title")
        for i, line in enumerate(p["lines"]):
            ui.text(surf, line, (80, 210 + i * 32), ui.WHITE, "md")
        y = 210 + len(p["lines"]) * 32 + 24
        for key, label in p.get("keys", []):
            box = ui.key_cap(surf, key, (80, y))
            ui.text(surf, label, (box.right + 10, y + 2), ui.MUTED, "sm")
            y += 34
        if p.get("stars"):
            for i, (n, label) in enumerate(((3, "best possible"),
                                            (2, "within 25%"),
                                            (1, "landed"))):
                ui.stars(surf, n, (94, y + 12 + i * 34), 20, total=3)
                ui.text(surf, label, (210, y + 2 + i * 34), ui.MUTED, "sm")
        if p.get("levels"):
            for i, lvl in enumerate(LEVELS):
                ui.text(surf, lvl["name"], (80, y + i * 30), ui.DRONE, "lg")
                ui.text(surf, lvl["desc"], (200, y + 4 + i * 30), ui.MUTED,
                        "xs")

        right = pygame.Rect(530, 90, 520, 540)
        ui.glass(surf, right, alpha=120)
        demo = p.get("demo")
        if demo:
            demo.draw(surf, self.demo_origin(demo))
        elif p.get("lab"):
            from games.skyrush.menu import MenuScene
            art = pygame.Rect(560, 200, 460, 300)
            surf.set_clip(right)
            MenuScene.art_lab(surf, art.inflate(-100, -60),
                              pygame.time.get_ticks())
            surf.set_clip(None)
            ui.text(surf, "Q-values  ·  7x7 eyes  ·  heat-map",
                    (right.centerx, 560), ui.MUTED, "sm", center=True)

        # page dots
        for i in range(len(self.pages)):
            c = ui.WHITE if i == self.page else ui.DIM
            pygame.draw.circle(surf, c, (ui.WIDTH // 2 - (len(self.pages) - 1)
                                         * 12 + i * 24, 652),
                               6 if i == self.page else 4)
        last = self.page == len(self.pages) - 1
        ui.hint_bar(surf, [("LEFT/RIGHT", "page"),
                           ("ENTER", "start flying" if last else "next"),
                           ("ESC", "menu")])

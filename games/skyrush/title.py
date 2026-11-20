"""Title screen: night sky, skyline, drones racing past, SKYRUSH logo."""

import math
import random

import pygame

from games.skyrush import common as ui
from src.shared.effects import Effects
from src.shared.scene import Scene


class Flyby:
    """A drone crossing the screen on a gentle wave, leaving a trail."""

    def __init__(self, rnd, delay=0):
        self.rnd = rnd
        self.reset(delay)

    def reset(self, delay=0):
        r = self.rnd
        self.dir = r.choice((-1, 1))
        self.x = -80 - delay if self.dir == 1 else ui.WIDTH + 80 + delay
        self.y = r.randrange(140, 560)
        self.speed = r.uniform(0.25, 0.45)
        self.size = r.randrange(34, 62)
        self.color = r.choice((ui.PLAYER, ui.DRONE, ui.DRONE))
        self.phase = r.random() * 6.28

    def update(self, dt, fx):
        self.x += self.dir * self.speed * dt
        y = self.y + math.sin(self.x / 90 + self.phase) * 14
        fx.trail((self.x, y), ui.lerp_color(self.color, ui.SKY_TOP, 0.5))
        if self.x < -120 or self.x > ui.WIDTH + 120:
            self.reset(self.rnd.randrange(0, 600))
        return y

    def draw(self, surf, y):
        s = self.size
        ui.draw_drone(surf, (0, 0), (self.x - s // 2, y - s // 2), s,
                      self.color)


class TitleScene(Scene):
    def __init__(self, app):
        super().__init__(app)
        rnd = random.Random(3)
        self.flybys = [Flyby(rnd, i * 300) for i in range(4)]
        self.fx = Effects()
        self.ys = [f.y for f in self.flybys]
        self.t = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.running = False
            else:
                from games.skyrush.menu import MenuScene
                self.app.sound.play("go")
                self.app.change(MenuScene(self.app))

    def update(self, dt):
        self.t += dt
        self.fx.update(dt)
        self.ys = [f.update(dt, self.fx) for f in self.flybys]

    def draw(self, surf):
        self.app.sky.draw(surf)
        self.fx.draw(surf)
        for f, y in zip(self.flybys, self.ys):
            f.draw(surf, y)

        intro = min(1.0, self.t / 900)
        y = 250 - (1 - intro) ** 2 * 120
        ui.draw_logo(surf, (ui.WIDTH // 2, int(y)))
        ui.text(surf, "OUTFLY THE MACHINE", (ui.WIDTH // 2, int(y) + 92),
                (200, 210, 255), "lg", center=True)

        if self.t > 900 and (self.t // 500) % 2 == 0:
            ui.text(surf, "PRESS ANY KEY TO TAKE OFF", (ui.WIDTH // 2, 520),
                    ui.WHITE, "lg", center=True)
        ui.text(surf, "A reinforcement learning drone game",
                (ui.WIDTH // 2, ui.HEIGHT - 28), (120, 120, 170), "xs",
                center=True)

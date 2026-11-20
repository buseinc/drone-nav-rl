"""Window, main loop, scene switching, screen shake and sound."""

import random

import pygame

from games.skyrush import common as ui
from src.shared.agent import Agent
from src.shared.sound import Sounds
from games.skyrush.title import TitleScene


class App:
    FPS = 60

    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        pygame.display.set_caption("SkyRush")
        self.screen = pygame.display.set_mode((ui.WIDTH, ui.HEIGHT))
        # Scenes draw on the canvas; the canvas is blitted with an offset
        # while the screen shakes.
        self.canvas = pygame.Surface((ui.WIDTH, ui.HEIGHT))
        self.clock = pygame.time.Clock()
        ui.init_fonts()
        self.sky = ui.Sky()
        self.agent = Agent()
        self.sound = Sounds()
        self.settings = {"arena": 0, "level": 1, "fog": False}
        self.shake_time = 0
        self.shake_power = 0
        self.running = True
        self.scene = TitleScene(self)

    def change(self, scene):
        self.scene = scene

    def shake(self, power=10, ms=350):
        self.shake_power, self.shake_time = power, ms

    def run(self):
        while self.running:
            dt = min(self.clock.tick(self.FPS), 50)   # no huge jumps
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                    self.sound.enabled = not self.sound.enabled
                else:
                    self.scene.handle_event(event)
            self.scene.update(dt)
            self.scene.draw(self.canvas)

            offset = (0, 0)
            if self.shake_time > 0:
                self.shake_time -= dt
                p = int(self.shake_power * max(0, self.shake_time) / 350) + 1
                offset = (random.randint(-p, p), random.randint(-p, p))
            self.screen.fill(ui.BG)
            self.screen.blit(self.canvas, offset)
            pygame.display.flip()
        pygame.quit()

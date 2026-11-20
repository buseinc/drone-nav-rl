"""Particles: trails, explosions and goal bursts."""

import math
import random

import pygame


class Effects:
    def __init__(self):
        self.particles = []   # [x, y, vx, vy, life, max_life, color, size]
        self.rings = []       # [x, y, age, duration, color, max_radius]

    def trail(self, pos, color):
        self.particles.append([pos[0], pos[1], 0.0, 0.0, 350, 350, color,
                               5])

    def burst(self, pos, color, n=30, speed=0.25, life=700, size=5):
        for _ in range(n):
            ang = random.uniform(0, 2 * math.pi)
            v = speed * random.uniform(0.3, 1.0)
            ln = life * random.uniform(0.6, 1.0)
            self.particles.append([pos[0], pos[1], math.cos(ang) * v,
                                   math.sin(ang) * v, ln, ln, color,
                                   size * random.uniform(0.6, 1.2)])

    def explosion(self, pos):
        self.burst(pos, (255, 200, 90), n=25, speed=0.30, life=600)
        self.burst(pos, (240, 90, 80), n=25, speed=0.18, life=900, size=6)
        self.ring(pos, (255, 150, 90), 500, 50)

    def celebrate(self, pos, color):
        self.burst(pos, color, n=35, speed=0.22, life=800)
        self.ring(pos, color, 700, 70)
        self.ring(pos, (240, 244, 250), 500, 40)

    def ring(self, pos, color, duration, radius):
        self.rings.append([pos[0], pos[1], 0, duration, color, radius])

    def update(self, dt):
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[2] *= 0.97
            p[3] *= 0.97
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        for r in self.rings:
            r[2] += dt
        self.rings = [r for r in self.rings if r[2] < r[3]]

    def draw(self, surf):
        for x, y, _, _, life, max_life, color, size in self.particles:
            rad = max(1, int(size * life / max_life))
            pygame.draw.circle(surf, color, (int(x), int(y)), rad)
        for x, y, age, dur, color, radius in self.rings:
            k = age / dur
            width = max(1, int(4 * (1 - k)))
            pygame.draw.circle(surf, color, (int(x), int(y)),
                               int(8 + radius * k), width)

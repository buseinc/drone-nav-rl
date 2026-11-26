"""Illustrated tiles and animated characters for the farm."""

import math
import random
from functools import lru_cache

import pygame

from games.skyrush import common as ui
from games.skyrush.farm import COLS, COOP, FENCES, HEDGES, POND, ROWS, TREES

CELL = 40
ORIGIN = (45, 147)
CREAM = (255, 247, 216)
INK = (42, 59, 45)
GOLD = (255, 192, 76)
ALERT = (230, 105, 80)


def point(cell, origin=ORIGIN):
    return (round(origin[0] + (cell[1] + 0.5) * CELL),
            round(origin[1] + (cell[0] + 0.5) * CELL))


def grass(surface, x, y, color):
    pygame.draw.lines(surface, color, False, [(x - 4, y - 3), (x, y), (x + 4, y - 5)], 1)


def shrub(surface, x, y, dark, light, scale=1):
    radius = round(12 * scale)
    pygame.draw.ellipse(surface, (66, 112, 77), (x - radius - 6, y + 2, 2 * radius + 12, 12))
    for dx, dy in ((-8, 0), (0, -7), (8, 0)):
        spot = (x + round(dx * scale), y + round(dy * scale))
        pygame.draw.circle(surface, dark, spot, radius)
        pygame.draw.circle(surface, light, (spot[0] - 2, spot[1] - 3), radius - 3)


def fence(surface, cell):
    x, y = point(cell, (0, 0))
    r, c = cell
    rail = (156, 97, 58)
    shine = (209, 149, 88)
    vertical = (r - 1, c) in FENCES or (r + 1, c) in FENCES
    for offset in (-6, 5):
        if vertical:
            limits = ((x + offset, y - CELL // 2), (x + offset, y + CELL // 2))
        else:
            limits = ((x - CELL // 2, y + offset), (x + CELL // 2, y + offset))
        pygame.draw.line(surface, rail, *limits, 6)
        pygame.draw.line(surface, shine, *limits, 2)
    pygame.draw.rect(surface, (136, 83, 53), (x - 4, y - 13, 8, 26), border_radius=2)
    pygame.draw.rect(surface, (241, 175, 99), (x - 4, y - 13, 8, 7), border_radius=2)


@lru_cache(maxsize=1)
def terrain():
    surface = pygame.Surface((COLS * CELL, ROWS * CELL))
    rng = random.Random(94)
    for r in range(ROWS):
        for c in range(COLS):
            cell = (r, c)
            x, y = point(cell, (0, 0))
            rect = pygame.Rect(c * CELL, r * CELL, CELL, CELL)
            shade = ((143, 180, 105), (149, 185, 109), (155, 190, 113))[(c + r * 2) % 3]
            pygame.draw.rect(surface, shade, rect)
            if r in (5, 10) or (c in (1, 11) and 2 < r < 10):
                pygame.draw.rect(surface, (201, 188, 132), rect.inflate(-1, -4), border_radius=6)
            for _ in range(3):
                dx, dy = (rng.randint(-17, 17) for _ in range(2))
                if rng.random() < 0.23:
                    pygame.draw.circle(surface, rng.choice(((250, 226, 152), (245, 216, 198))),
                                       (x + dx, y + dy), 2)
                else:
                    grass(surface, x + dx, y + dy, (122, 158, 90))
            if cell in POND:
                pygame.draw.rect(surface, (58, 122, 125), rect)
                pygame.draw.rect(surface, (96, 166, 155), rect.inflate(-2, -2), border_radius=5)
                pygame.draw.arc(surface, (159, 202, 175), rect.inflate(-18, -24), 0.1, 2.7, 2)
            if cell in HEDGES:
                shrub(surface, x, y, (66, 115, 68), (97, 149, 77), 0.76)
                pygame.draw.circle(surface, (255, 220, 169), (x - 4, y - 4), 2)
    for cell in sorted(FENCES):
        fence(surface, cell)
    for cell in sorted(TREES):
        x, y = point(cell, (0, 0))
        pygame.draw.rect(surface, (121, 84, 55), (x - 4, y, 8, 16), border_radius=2)
        shrub(surface, x, y - 5, (62, 112, 67), (102, 153, 73))
    return surface


def coop(surface, unlocked, now):
    x, y = point(COOP)
    if unlocked:
        pulse = 0.5 + 0.5 * math.sin(now / 180)
        radius = 21 + round(pulse * 4)
        pygame.draw.circle(surface, (242, 237, 157), (x, y), radius, 2)
    pygame.draw.ellipse(surface, (120, 143, 82), (x - 23, y + 8, 46, 15))
    pygame.draw.rect(surface, (234, 184, 112), (x - 17, y - 15, 34, 30), border_radius=3)
    pygame.draw.polygon(surface, (155, 80, 49), [(x - 23, y - 13), (x, y - 32), (x + 23, y - 13)])
    pygame.draw.lines(surface, (218, 125, 77), False,
                      [(x - 23, y - 13), (x, y - 32), (x + 23, y - 13)], 3)
    color = (89, 128, 68) if unlocked else (134, 89, 58)
    pygame.draw.rect(surface, color, (x - 7, y - 8, 14, 24), border_radius=5)
    pygame.draw.circle(surface, CREAM if unlocked else GOLD, (x + 3, y + 4), 2)


@lru_cache(maxsize=2)
def corn_icon(scale):
    icon = pygame.Surface((28, 32), pygame.SRCALPHA)
    pygame.draw.ellipse(icon, (124, 79, 44), (7, 2, 14, 23))
    pygame.draw.ellipse(icon, GOLD, (8, 3, 12, 21))
    for row in range(4):
        for col in range(2):
            pygame.draw.circle(icon, (255, 231, 146), (12 + col * 4, 7 + row * 4), 2)
    pygame.draw.polygon(icon, (80, 126, 65), [(5, 12), (16, 27), (10, 28)])
    pygame.draw.polygon(icon, (104, 155, 71), [(23, 13), (12, 25), (14, 29), (19, 26)])
    if scale != 1:
        icon = pygame.transform.smoothscale(icon, (round(28 * scale), round(32 * scale)))
    return icon


def corn(surface, x, y, now=0, scale=1.0):
    icon = corn_icon(scale)
    surface.blit(icon, icon.get_rect(center=(x, y + round(math.sin(now / 275) * 3))))


def chick(surface, x, y, now, facing, movement, hidden=False):
    """A soft squash-and-stretch hop, foot poses and occasional blink."""
    step = math.sin(math.pi * movement)
    heading = -1 if facing[1] < 0 else 1
    bob = round(step * 8 + math.sin(now / 270))
    pygame.draw.ellipse(surface, (113, 143, 78), (x - 13, y + 9, 26, 10))
    feet = round(step * 5)
    for side in (-1, 1):
        px = x + side * 6 + side * feet
        pygame.draw.line(surface, (194, 116, 57), (px - 2, y + 11 - bob),
                         (px + 4, y + 12 - bob), 3)
    cy = y - bob
    body = pygame.Rect(0, 0, round(35 - step * 3), round(32 + step * 4))
    body.center = (x, cy)
    pygame.draw.ellipse(surface, (159, 104, 53), body.inflate(2, 2))
    pygame.draw.ellipse(surface, (255, 222, 102), body)
    pygame.draw.ellipse(surface, (255, 237, 147), (x - 7, cy - 12, 15, 19))
    wing = (x - heading * 10, cy + 5 + round(step * 2))
    pygame.draw.ellipse(surface, (240, 174, 70), (wing[0] - 6, wing[1] - 4, 12, 8))
    pygame.draw.lines(surface, (208, 135, 53), False,
                      [(x - 5, cy - 14), (x - 6, cy - 21), (x + 1, cy - 16),
                       (x + 4, cy - 20), (x + 6, cy - 15)], 2)
    eye = (x + heading * 8, cy - 6)
    if now % 3100 < 105:
        pygame.draw.line(surface, INK, (eye[0] - 2, eye[1]), (eye[0] + 2, eye[1]), 2)
    else:
        pygame.draw.circle(surface, INK, eye, 3)
        pygame.draw.circle(surface, CREAM, (eye[0] - 1, eye[1] - 1), 1)
    pygame.draw.circle(surface, (248, 164, 100), (eye[0] - heading * 3, cy + 2), 3)
    nose = x + heading * 14
    pygame.draw.polygon(surface, (224, 128, 52),
                        [(nose, cy - 3), (nose + heading * 9, cy + 1), (nose, cy + 4)])
    if hidden:
        for dx in (-9, 0, 8):
            pygame.draw.ellipse(surface, (93, 148, 72), (x + dx - 5, y + 4, 10, 11))


def drone(surface, x, y, mode, now, facing):
    accent = ALERT if mode == "chase" else GOLD if mode == "search" else (126, 222, 215)
    pygame.draw.ellipse(surface, (106, 132, 80), (x - 17, y + 6, 34, 11))
    y -= 6 + round(math.sin(now / 152) * 2)
    ui.draw_drone(surface, (0, 0), (x - 24, y - 24), 50, accent)
    light = (x + facing[1] * 11, y + facing[0] * 11)
    pygame.draw.circle(surface, INK, light, 6)
    pygame.draw.circle(surface, accent, light, 4)

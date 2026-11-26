"""Pastel river scenery and hand-drawn duck animation."""

import math
import random
from functools import lru_cache

import pygame

from games.skyrush import common as ui
from games.skyrush.duck_rescue import (BRIDGE, BUSHES, COLS, NEST, RIVER, ROWS,
                                      SPOTLIGHT_RADIUS, STONES)
from games.skyrush.farm_art import drone

CELL = 40
ORIGIN = (47, 139)
CREAM = (255, 247, 222)
INK = (48, 64, 64)
WATER = (107, 186, 189)
LEAF = (101, 156, 105)
PALETTE = ((252, 213, 112), (255, 227, 147), (251, 196, 116))


def point(cell, origin=ORIGIN):
    return (round(origin[0] + (cell[1] + 0.5) * CELL),
            round(origin[1] + (cell[0] + 0.5) * CELL))


def oval(surface, color, center, size):
    rect = pygame.Rect(0, 0, *size)
    rect.center = center
    pygame.draw.ellipse(surface, color, rect)


def lily(surface, x, y, bloom):
    pygame.draw.ellipse(surface, (67, 142, 143), (x - 10, y - 4, 20, 11))
    pygame.draw.ellipse(surface, (134, 180, 120), (x - 10, y - 6, 19, 10))
    pygame.draw.polygon(surface, (106, 185, 188), [(x, y), (x + 9, y - 5), (x + 10, y)])
    if bloom:
        for dx, dy in ((0, -5), (-4, -2), (4, -2), (0, 2)):
            pygame.draw.circle(surface, (245, 192, 207), (x + dx, y + dy), 4)
        pygame.draw.circle(surface, (253, 230, 147), (x, y - 1), 2)


@lru_cache(maxsize=1)
def terrain():
    board = pygame.Surface((COLS * CELL, ROWS * CELL))
    rng = random.Random(29)
    for row in range(ROWS):
        for col in range(COLS):
            cell = row, col
            x, y = point(cell, (0, 0))
            rect = pygame.Rect(col * CELL, row * CELL, CELL, CELL)
            if cell in RIVER:
                water = ((113, 193, 192), WATER, (97, 176, 185), (110, 190, 191))[col - 7]
                pygame.draw.rect(board, water, rect)
                if col in (7, 10):
                    px = rect.left if col == 7 else rect.right - 4
                    pygame.draw.rect(board, (163, 215, 188), (px, rect.y, 4, CELL))
                if cell not in BRIDGE | STONES and rng.random() < 0.32:
                    lily(board, x + rng.randint(-9, 9), y, rng.random() < 0.52)
                continue

            shade = ((169, 202, 135), (174, 205, 141), (178, 208, 145))[(row + col * 2) % 3]
            pygame.draw.rect(board, shade, rect)
            if row in (2, 8):
                pygame.draw.rect(board, (224, 210, 161), rect.inflate(0, -11), border_radius=7)
            for _ in range(3):
                dx, dy = rng.randint(-16, 16), rng.randint(-16, 16)
                if rng.random() < 0.37:
                    color = rng.choice(((253, 231, 155), (251, 217, 216), (249, 241, 213)))
                    pygame.draw.circle(board, color, (x + dx, y + dy), 2)
                else:
                    pygame.draw.line(board, (142, 181, 116), (x + dx, y + dy),
                                     (x + dx + 2, y + dy - 4), 1)
            if cell in BUSHES:
                oval(board, (135, 169, 111), (x, y + 9), (33, 17))
                for bx, by in ((-7, 0), (0, -7), (8, 0)):
                    pygame.draw.circle(board, (80, 128, 99), (x + bx, y + by), 11)
                    pygame.draw.circle(board, LEAF, (x + bx - 1, y + by - 2), 9)
                pygame.draw.circle(board, (251, 191, 190), (x + 4, y - 5), 3)

    for tile in sorted(BRIDGE):
        x, y = point(tile, (0, 0))
        pygame.draw.rect(board, (131, 104, 80), (x - 20, y - 15, 40, 34))
        for dx in (-16, -6, 4, 14):
            pygame.draw.rect(board, (215, 179, 129), (x + dx - 4, y - 14, 9, 28),
                             border_radius=2)
        for dy in (-15, 14):
            pygame.draw.line(board, (249, 213, 158), (x - 20, y + dy), (x + 20, y + dy), 3)
    return board


def draw_river(surface, tide, now):
    surface.blit(terrain(), ORIGIN)
    x0 = ORIGIN[0] + 7 * CELL
    for i in range(12):
        x = x0 + 10 + i * 43 % 139
        y = ORIGIN[1] + (i * 61 + now // (8 if tide == "surge" else 26)) % (ROWS * CELL - 10)
        row = (y - ORIGIN[1]) // CELL
        if row not in (2, 8):
            pygame.draw.arc(surface, (154, 211, 208), (x - 7, y, 15, 7), 0.12, 2.99, 1)
    for tile in STONES:
        x, y = point(tile)
        surge = tide == "surge"
        oval(surface, (87, 148, 155), (x, y + 6), (34, 25))
        oval(surface, (139, 182, 174) if surge else (217, 211, 171), (x, y), (33, 23))
        oval(surface, (179, 207, 193) if surge else (241, 233, 191), (x, y - 3), (22, 12))
        if surge or (tide == "warning" and now % 380 < 190):
            pygame.draw.arc(surface, (229, 248, 230), (x - 16, y - 2, 32, 14), 0.1, 2.9, 2)


@lru_cache(maxsize=2)
def spotlight(columns):
    beam = pygame.Surface((columns * CELL, round(2 * SPOTLIGHT_RADIUS * CELL)), pygame.SRCALPHA)
    pygame.draw.rect(beam, (252, 232, 148, 84), beam.get_rect(), border_radius=7)
    pygame.draw.rect(beam, (255, 244, 187, 140), beam.get_rect(), 2, border_radius=7)
    return beam


def draw_orca_light(surface, row, right):
    beam = spotlight(right - 7 + 1)
    surface.blit(beam, beam.get_rect(center=point((row, (7 + right) / 2))))


def draw_orca(surface, row, now):
    x, y = point((row, 8.5))
    drone(surface, x, y, "search", now, (0, 0))


def draw_nest(surface):
    x, y = point(NEST)
    oval(surface, (135, 170, 112), (x, y + 8), (47, 28))
    oval(surface, (163, 112, 71), (x, y), (43, 28))
    oval(surface, (232, 183, 116), (x, y - 2), (39, 24))
    oval(surface, (194, 145, 90), (x, y - 2), (27, 14))
    for dx in (-13, -6, 5, 11):
        pygame.draw.line(surface, (255, 220, 151), (x + dx - 3, y + 6), (x + dx, y + 10), 2)


@lru_cache(maxsize=256)
def duck_sprite(color, adult, facing_left, gait, blinking, asleep):
    canvas = pygame.Surface((96, 88), pygame.SRCALPHA)
    outline = (139, 100, 74)
    ivory = (255, 244, 218)
    peach = (246, 169, 142)
    hop = (0, 3, 6, 3)[gait]
    oval(canvas, (236, 153, 87), (34 - hop, 72 - hop), (18, 8))
    oval(canvas, (222, 132, 70), (55 + hop, 73), (19, 8))
    body = (43, 55 - hop)
    pygame.draw.polygon(canvas, outline, [(23, 52 - hop), (10, 44 - hop), (13, 61 - hop), (28, 68 - hop)])
    pygame.draw.polygon(canvas, color, [(23, 56 - hop), (13, 48 - hop), (16, 60 - hop), (28, 66 - hop)])
    oval(canvas, outline, body, (62, 34))
    oval(canvas, color, (body[0], body[1] - 1), (59, 31))
    wing = ui.lerp_color(color, (189, 125, 74), 0.23)
    oval(canvas, wing, (33, 57 - hop), (28, 16))
    oval(canvas, ui.lerp_color(color, ivory, 0.44), (33, 54 - hop), (23, 11))
    y = 34 - hop
    oval(canvas, outline, (66, y), (43, 43))
    oval(canvas, color, (66, y - 1), (40, 40))
    oval(canvas, ui.lerp_color(color, ivory, 0.66), (61, y - 11), (17, 9))
    pygame.draw.lines(canvas, outline, False, [(58, y - 19), (57, y - 26), (65, y - 22), (67, y - 25)], 2)
    oval(canvas, (221, 129, 77), (85, y + 6), (20, 11))
    oval(canvas, (253, 179, 103), (85, y + 4), (18, 7))
    oval(canvas, peach, (68, y + 8), (12, 7))
    if blinking or asleep:
        pygame.draw.arc(canvas, INK, (68, y - 6, 12, 8), 0, math.pi, 2)
    else:
        oval(canvas, INK, (74, y - 3), (7, 10))
        pygame.draw.circle(canvas, CREAM, (75, y - 5), 2)
    if adult:
        pygame.draw.polygon(canvas, (116, 165, 150), [(63, y + 15), (80, y + 21), (71, y + 31)])
        pygame.draw.circle(canvas, (231, 222, 174), (70, y + 20), 2)
    return pygame.transform.flip(canvas, facing_left, False)


def draw_duck(surface, position, now, *, index=0, adult=False, facing_left=False,
              moving=False, asleep=False, scale=1.0):
    x, y = position
    bob = round(math.sin(now / 210 + index * 3) * 2)
    gait = now // 65 % 4 if moving else 0
    color = CREAM if adult else PALETTE[index % len(PALETTE)]
    sprite = duck_sprite(color, adult, facing_left, gait, (now + index * 441) % 2800 < 125, asleep)
    size = round(48 * scale), round(44 * scale)
    image = pygame.transform.smoothscale(sprite, size)
    oval(surface, (126, 156, 115), (x, y + round(12 * scale)), (round(34 * scale), round(10 * scale)))
    surface.blit(image, image.get_rect(center=(x, y + bob - round(4 * scale))))

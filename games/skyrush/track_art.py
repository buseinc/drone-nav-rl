"""Top-down artwork and hazard markers for Parkurlar."""

import math
import random
from functools import lru_cache

import pygame

from games.skyrush import common as ui
from games.skyrush.courses import GRID_SIZE, NEON


PILOT = (255, 212, 129)
ORCA = (113, 229, 251)
PANEL = (14, 20, 33)
ALERT = (255, 137, 120)


@lru_cache(maxsize=2)
def backdrop(course):
    surface = pygame.Surface((ui.WIDTH, ui.HEIGHT))
    top, bottom = ((9, 12, 27), (35, 23, 55)) if course == NEON else (
        (14, 29, 42), (67, 47, 52))
    for y in range(ui.HEIGHT):
        color = ui.lerp_color(top, bottom, y / ui.HEIGHT)
        pygame.draw.line(surface, color, (0, y), (ui.WIDTH, y))
    for x in range(0, ui.WIDTH, 80):
        pygame.draw.line(surface, ui.lerp_color(top, bottom, 0.38),
                         (x, 0), (x + 360, ui.HEIGHT))
    return surface


def paint_building(surface, rect, accent, rng):
    side = rect.inflate(-5, -5).move(2, 2)
    roof = side.move(-4, -5)
    pygame.draw.rect(surface, (12, 12, 27), side, border_radius=2)
    pygame.draw.rect(surface, (48, 39, 71), roof, border_radius=2)
    pygame.draw.line(surface, ui.lerp_color((67, 52, 95), accent, 0.38),
                     roof.topleft, roof.topright, 2)
    vent = roof.inflate(-roof.width // 2, -roof.height // 2)
    pygame.draw.rect(surface, (33, 28, 53), vent, border_radius=2)
    if rng.random() > 0.35:
        pygame.draw.line(surface, ui.lerp_color(accent, (37, 34, 58), 0.35),
                         (roof.left + 4, roof.bottom - 3), (roof.right - 5, roof.bottom - 3), 2)


def paint_container(surface, rect, color):
    shadow = rect.move(2, 4)
    pygame.draw.rect(surface, (18, 34, 45), shadow, border_radius=2)
    pygame.draw.rect(surface, color, rect, border_radius=2)
    pygame.draw.line(surface, ui.lerp_color(color, ui.WHITE, 0.28),
                     rect.topleft, rect.topright, 2)
    for x in range(rect.left + 4, rect.right - 3, 6):
        pygame.draw.line(surface, ui.lerp_color(color, (25, 44, 55), 0.32),
                         (x, rect.top + 3), (x, rect.bottom - 2))


def paint_quay(surface, cell):
    quay = pygame.Rect(0, 5 * cell + cell // 8, GRID_SIZE * cell, 7 * cell)
    pygame.draw.rect(surface, (32, 54, 61), quay)
    pygame.draw.line(surface, (94, 109, 103), quay.topleft, quay.topright, 3)
    for x in range(cell // 5, quay.right, cell // 2):
        pygame.draw.line(surface, (55, 60, 58), (x, quay.top), (x + 6, quay.top + 8), 2)


def paint_ship(surface, cell):
    hull = pygame.Rect(cell, cell + cell // 4, 9 * cell + cell // 4, cell * 2)
    points = [(hull.left + cell // 3, hull.top), (hull.right - cell, hull.top),
              (hull.right, hull.centery), (hull.right - cell, hull.bottom),
              (hull.left + cell // 3, hull.bottom), (hull.left, hull.centery)]
    pygame.draw.polygon(surface, (13, 35, 46), [(x + 3, y + 5) for x, y in points])
    pygame.draw.polygon(surface, (95, 96, 92), points)
    pygame.draw.polygon(surface, (166, 143, 115), points, 2)
    deck = hull.inflate(-cell * 2, -cell // 2)
    pygame.draw.rect(surface, (47, 68, 73), deck, border_radius=3)
    for row in range(2):
        for col in range(6):
            color = ((129, 83, 74), (103, 128, 122), (171, 124, 81))[(row + col) % 3]
            cargo = pygame.Rect(deck.x + col * cell + cell // 3,
                                deck.y + row * (cell * 2 // 3) + 4,
                                cell - 4, cell // 2)
            paint_container(surface, cargo, color)
    bridge = pygame.Rect(hull.right - cell * 2, hull.y + cell // 2, cell, cell)
    pygame.draw.rect(surface, (163, 158, 132), bridge, border_radius=3)
    pygame.draw.rect(surface, (39, 75, 89), bridge.inflate(-9, -14), border_radius=3)


def paint_neon_towers(surface, cell, accent, rng):
    for col, width, height in ((1, 2, 3), (4, 3, 2), (8, 2, 3)):
        tower = pygame.Rect(col * cell, cell // 3, width * cell, height * cell)
        paint_building(surface, tower, accent, rng)
        roof = tower.inflate(-20, -23)
        for x in range(roof.left, roof.right - 4, 10):
            pygame.draw.line(surface, (77, 57, 110), (x, roof.top), (x, roof.bottom))
        sign = pygame.Rect(roof.left, roof.bottom - 14, roof.width, 12)
        for grow, amount in ((10, 0.13), (4, 0.3), (0, 0.72)):
            pygame.draw.rect(surface, ui.lerp_color((43, 34, 65), accent, amount),
                             sign.inflate(grow, grow), border_radius=3)


@lru_cache(maxsize=4)
def terrain(course, cell):
    size = GRID_SIZE * cell
    surface = pygame.Surface((size, size))
    surface.fill(course.ground)
    rng = random.Random(740)
    safe, fast = course.safe_cells, course.fast_cells
    air = safe | fast
    patrol = set(course.patrol)
    if course != NEON:
        paint_quay(surface, cell)
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            pos = (row, col)
            rect = pygame.Rect(col * cell, row * cell, cell, cell)
            if pos in air or pos in patrol:
                continue
            if course == NEON:
                if (row * 3 + col * 5) % 8 <= 4:
                    paint_building(surface, rect.inflate(-5, -5), course.accent, rng)
                elif row < 5:
                    pygame.draw.rect(surface, (33, 28, 55), rect.inflate(-8, -8), 1)
            else:
                if row >= 5 and (row + col * 3) % 7 <= 3:
                    color = ((131, 80, 66), (74, 107, 105), (159, 116, 75))[(row + col) % 3]
                    paint_container(surface, rect.inflate(-6, -cell // 2), color)
                else:
                    for _ in range(3):
                        x = rect.x + rng.randrange(max(1, cell - 12))
                        y = rect.y + rng.randrange(cell)
                        shade = rng.choice(((35, 69, 78), (28, 59, 70), (46, 80, 84)))
                        pygame.draw.line(surface, shade, (x, y), (x + 9, y))
    if course == NEON:
        paint_neon_towers(surface, cell, course.accent, rng)
    else:
        paint_ship(surface, cell)

    edge = ui.lerp_color(course.lane, ui.WHITE, 0.19)
    for row, col in air:
        rect = pygame.Rect(col * cell, row * cell, cell, cell).inflate(-4, -4)
        pygame.draw.rect(surface, course.lane, rect, border_radius=4)
        pygame.draw.rect(surface, edge, rect, 1, border_radius=4)
        x, y = center((0, 0), cell, (row, col))
        pygame.draw.circle(surface, edge, (x, y), 1)
    return surface


def center(origin, cell, pos):
    row, col = pos
    return (round(origin[0] + (col + 0.5) * cell),
            round(origin[1] + (row + 0.5) * cell))


def draw_board(surface, course, env, origin, cell, now, tick=0, elapsed=1,
               next_tick=None):
    size = GRID_SIZE * cell
    frame = pygame.Rect(*origin, size, size).inflate(12, 12)
    pygame.draw.rect(surface, PANEL, frame, border_radius=8)
    pygame.draw.rect(surface, ui.lerp_color(PANEL, course.accent, 0.58),
                     frame, 1, border_radius=8)
    surface.blit(terrain(course, cell), origin)
    ox, oy = origin
    if course == NEON:
        for index in range(36):
            x = ox + 8 + (index * 131 - now // 7) % (size - 16)
            y = oy + (index * 73 + now // 3) % (size - 10)
            if ((y - oy) // cell, (x - ox) // cell) in env.obstacles:
                pygame.draw.aaline(surface, (62, 58, 90), (x, y), (x - 4, y + 9))
    else:
        for index in range(12):
            x = ox + 10 + (index * 59 + now // 44) % (size - 22)
            y = oy + cell // 2 + (index % 3) * 7
            pygame.draw.line(surface, (57, 90, 94), (x, y), (x + 9, y))
    for pos, direction in course.winds:
        if course.gate and pos == course.gate.cell:
            continue
        rect = pygame.Rect(0, 0, cell, cell)
        rect.center = center(origin, cell, pos)
        ui.draw_wind(surface, rect, direction, now)

    start = center(origin, cell, course.start)
    pygame.draw.circle(surface, PANEL, start, int(cell * 0.36))
    pygame.draw.circle(surface, PILOT, start, int(cell * 0.33), 2)
    ui.text(surface, "S", start, PILOT, "key", center=True)
    ui.draw_landing_tile(surface, ui.cell_rect(origin, cell, course.goal),
                         0.5 + 0.5 * math.sin(now / 250))

    if course.gate:
        gate = course.gate
        color = ORCA if gate.open_at(tick) else PILOT if gate.opens_in(tick) <= 2 else ALERT
        x, y = center(origin, cell, gate.cell)
        post = max(3, cell // 7)
        for dy in (-1, 1):
            pygame.draw.circle(surface, color, (x, y + dy * (cell // 3)), post)
        if not gate.open_at(tick):
            pygame.draw.line(surface, PANEL, (x, y - cell // 3), (x, y + cell // 3), post + 4)
            pygame.draw.line(surface, color, (x, y - cell // 3), (x, y + cell // 3), post)
        else:
            pygame.draw.line(surface, color, (x - post, y), (x + post, y), 2)

    for enemy in env.enemies:
        top, bottom = (center(origin, cell, enemy["track"][index]) for index in (0, -1))
        pygame.draw.line(surface, PANEL, top, bottom, 5)
        pygame.draw.line(surface, ALERT, top, bottom, 1)
        was = env.enemy_pos(enemy, max(0, tick - 1))[0]
        row, col = env.enemy_pos(enemy, tick)
        x, y = center(origin, cell, (was + (row - was) * elapsed, col))
        pygame.draw.line(surface, (111, 85, 77), (bottom[0] + cell // 3, bottom[1]),
                         (x, y), 2)
        pygame.draw.rect(surface, ALERT, (x - 6, y - 5, 12, 10), border_radius=2)
        target_tick = tick + 1 if next_tick is None else next_tick
        target = center(origin, cell, env.enemy_pos(enemy, target_tick))
        pygame.draw.circle(surface, ALERT, target, int(cell * 0.33), 2)

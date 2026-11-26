"""Landing pad and replay drawing for the classic duel."""

import math

import pygame

from games.skyrush import common as ui
from games.skyrush.airframe_art import draw_airframe

REPLAY_TICK_MS = 650
PHOTO_HOLD_MS = 950


def draw_pad(surface, origin, cell, goal, position, accent, now, touchdown=None):
    rect = ui.cell_rect(origin, cell, goal)
    center = rect.center
    edge = ui.lerp_color((54, 126, 130), accent, 0.65)
    pygame.draw.rect(surface, (19, 40, 49), rect, border_radius=6)
    pygame.draw.rect(surface, edge, rect, 1, border_radius=6)
    ui.draw_landing_mark(surface, center, cell, (191, 239, 221))

    distance = sum(abs(a - b) for a, b in zip(goal, position))
    approaching = distance <= 2.05
    sweep = now // 90 % 8
    for index in range(8):
        angle = index * math.tau / 8
        radius = cell * 0.38
        point = (round(center[0] + radius * math.cos(angle)),
                 round(center[1] + radius * math.sin(angle)))
        lit = touchdown is not None or approaching and (sweep - index) % 8 < 3
        if lit:
            pygame.draw.circle(surface, ui.lerp_color(accent, ui.WHITE, 0.55),
                               point, max(1, round(cell * 0.045)))

    if touchdown is not None and touchdown < 460:
        progress = touchdown / 460
        ring = ui.lerp_color(accent, (31, 49, 60), progress)
        pygame.draw.circle(surface, ring, center, round(cell * (0.30 + 0.52 * progress)), 2)


def draw_landing_drone(surface, origin, cell, position, airframe, descent, direction=None):
    """Settle the sprite onto the pad while preserving its grid position."""
    x, y = ui.cell_center(origin, cell, position)
    if descent is None:
        draw_airframe(surface, (x, y), cell, airframe, pygame.time.get_ticks(), direction)
        return
    descent = descent * descent * (3 - 2 * descent)
    size = round(cell * (1 - descent * 0.24))
    wing_center = y + round(cell * (0.08 * descent - 0.17 * math.sin(math.pi * descent)))
    draw_airframe(surface, (x, wing_center), size, airframe, pygame.time.get_ticks(), direction,
                  landed=descent == 1.0)


def replay_frame(moves, tick_ms, elapsed):
    """Replay recorded controller paths, including a late start within a tick."""
    step = min(len(moves) - 1, int(elapsed // REPLAY_TICK_MS))
    phase = min(1.0, (elapsed - step * REPLAY_TICK_MS) / REPLAY_TICK_MS)
    points, duration = moves[step]
    progress = max(0.0, 1 - (1 - phase) * tick_ms / duration)
    path_index = (len(points) - 1) * progress
    index = min(len(points) - 2, int(path_index))
    position = pygame.Vector2(points[index]).lerp(points[index + 1], path_index - index)
    descent = progress if step == len(moves) - 1 else None
    return position, descent

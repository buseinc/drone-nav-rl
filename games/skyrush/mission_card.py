"""Animated flight through the stops on the Sky Missions menu card."""

import math
from functools import lru_cache

import pygame

from games.skyrush import common as ui

SKY = (13, 23, 45)
DIM_ROUTE = (49, 68, 99)
START = (6, 126)
STOPS = ((35, 120), (95, 77), (158, 116), (222, 59))
COLORS = ((100, 236, 190), (107, 209, 252), (220, 144, 246), (255, 215, 121))
FLIGHT_MS = 500
STOP_MS = 320
LEG_MS = FLIGHT_MS + STOP_MS
HOLD_MS = 1050
FADE_MS = 320
CYCLE_MS = len(STOPS) * LEG_MS + HOLD_MS + FADE_MS


@lru_cache(maxsize=2)
def backdrop(size):
    surface = pygame.Surface(size, pygame.SRCALPHA)
    w, h = size
    for y in range(h):
        color = ui.lerp_color((14, 29, 54), (25, 19, 48), y / h)
        pygame.draw.line(surface, color, (0, y), (w, y))
    for x in range(15, w, 19):
        for y in range(15, h, 19):
            pygame.draw.circle(surface, (43, 53, 78), (x, y), 1)
    for x, y in ((49, 38), (140, 43), (187, 28), (241, 106), (76, 157)):
        pygame.draw.line(surface, (59, 77, 109), (x - 2, y), (x + 2, y))
        pygame.draw.line(surface, (59, 77, 109), (x, y - 2), (x, y + 2))
    mask = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=11)
    return surface, mask


def star_progress(arrival_age, index):
    return max(0, min(1, (arrival_age - 30 - 73 * index) / 105))


def draw_stop(surface, center, accent, age):
    x, y = center
    arrival_glow = max(0, 1 - age / 450) if age >= 0 else 0
    edge = accent if age >= 0 else ui.lerp_color(SKY, accent, 0.30)
    if age >= 0:
        for radius, amount in ((18, 0.13), (14, 0.24)):
            pygame.draw.circle(surface, ui.lerp_color(SKY, accent, amount), (x, y), radius)
    pygame.draw.circle(surface, (20, 32, 53), (x, y), 11)
    pygame.draw.circle(surface, edge, (x, y), 11, 2)
    if age >= 0:
        pygame.draw.circle(surface, ui.lerp_color(edge, ui.WHITE, 0.52), (x, y), 5)
    else:
        pygame.draw.circle(surface, edge, (x, y), 3)
    if arrival_glow:
        pygame.draw.circle(surface, ui.lerp_color(SKY, accent, arrival_glow * 0.75), (x, y),
                           round(13 + 13 * (1 - arrival_glow)), 1)

    for index in range(3):
        position = (x + (index - 1) * 15, y + 24)
        phase = star_progress(age, index)
        ui.star(surface, position, 10, filled=False)
        if phase > 0:
            pop = math.sin(math.pi * phase)
            tint = ui.lerp_color(ui.GOLD, ui.WHITE, pop * 0.55)
            ui.star(surface, position, round(10 + 6 * pop), color=tint)


def draw_mission_card(surf, rect, elapsed):
    background, mask = backdrop(rect.size)
    surface = background.copy()
    time = elapsed % CYCLE_MS
    leg = min(len(STOPS) - 1, time // LEG_MS)
    leg_age = time - leg * LEG_MS
    flight = min(1, leg_age / FLIGHT_MS)
    eased = flight * flight * (3 - 2 * flight)
    route = (START, *STOPS)
    current = pygame.Vector2(route[leg]).lerp(route[leg + 1], eased)

    pygame.draw.lines(surface, DIM_ROUTE, False, route, 2)
    for index in range(leg + 1):
        end = route[index + 1] if index < leg else current
        accent = COLORS[index]
        pygame.draw.line(surface, ui.lerp_color(SKY, accent, 0.28), route[index], end, 6)
        pygame.draw.aaline(surface, accent, route[index], end)

    for index, (position, accent) in enumerate(zip(STOPS, COLORS)):
        age = time - index * LEG_MS - FLIGHT_MS
        draw_stop(surface, position, accent, age)
        if index == len(STOPS) - 1:
            face = ui.SKY_TOP if age >= 0 else (23, 34, 56)
            pygame.draw.circle(surface, face, position, 8)
            ui.draw_landing_mark(surface, position, 23, accent if age >= 0 else (144, 131, 109))

    hover = 14 + 8 * math.sin(math.pi * flight) + math.sin(time / 145) * 1.5
    # Draw the wake along the active segment, behind the animated drone.
    for index in range(5, 0, -1):
        trail = pygame.Vector2(route[leg]).lerp(route[leg + 1], max(0, eased - index * 0.075))
        if eased > index * 0.075 and flight < 1:
            pygame.draw.circle(surface, ui.lerp_color(SKY, COLORS[leg], 1 - index * 0.15),
                               (round(trail.x), round(trail.y - hover)), 2)
    ui.draw_drone(surface, (0, 0), (current.x - 16, current.y - hover - 16), 35, ui.PLAYER)

    fade = max(0, (time - (CYCLE_MS - FADE_MS)) / FADE_MS)
    if fade:
        overlay = background.copy()
        overlay.set_alpha(round(255 * fade))
        surface.blit(overlay, (0, 0))
    surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surf.blit(surface, rect)

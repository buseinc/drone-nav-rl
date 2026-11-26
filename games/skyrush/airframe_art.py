"""Top-down airframes with separate carbon arms, motors and shell panels."""

import math
from functools import lru_cache

import pygame

from games.skyrush import common as ui

ROTOR_LAYOUT = {
    "kestrel": ((-20, -18), (20, -18), (-21, 19), (21, 19)),
    "pip": ((-22, -19), (22, -19), (-22, 19), (22, 19)),
    "puddle": ((-25, 4), (25, 4), (-17, 19), (17, 19)),
    "bumble": ((-24, -11), (24, -11), (-23, 14), (23, 14)),
    "jelly": ((-23, -16), (23, -16), (-23, 7), (23, 7)),
    "sprout": ((-24, -12), (24, -12), (-23, 18), (23, 18)),
    "finch": ((-26, -6), (26, -6), (-19, 16), (19, 16)),
    "orbit": ((-25, -12), (25, -12), (-24, 16), (24, 16)),
    "needle": ((-15, -23), (15, -23), (-24, 16), (24, 16)),
    "moth": ((-21, -16), (21, -16), (-21, 16), (21, 16)),
    "anchor": ((-24, -19), (24, -19), (-24, 19), (24, 19)),
    "orca": ((-22, -17), (22, -17), (-19, 21), (19, 21)),
}
SHELLS = {
    "kestrel": ((-8, -20), (8, -20), (13, -10), (11, 14), (5, 20), (-5, 20), (-11, 14), (-13, -10)),
    "needle": ((0, -27), (8, -16), (10, 8), (21, 17), (8, 20), (0, 15), (-8, 20), (-21, 17), (-10, 8), (-8, -16)),
    "moth": ((-7, -21), (7, -21), (13, -13), (16, 9), (10, 19), (-10, 19), (-16, 9), (-13, -13)),
    "anchor": ((-12, -20), (12, -20), (18, -12), (18, 12), (12, 22), (-12, 22), (-18, 12), (-18, -12)),
    "orca": ((-12, -18), (12, -18), (17, -7), (8, 22), (-8, 22), (-17, -7)),
}
HOVER_MOTION = {
    "kestrel": (3, 2, 660),
    "pip": (7, 4, 260),
    "puddle": (10, 4, 310),
    "bumble": (8, 3, 220),
    "jelly": (4, 4, 560),
    "sprout": (5, 3, 510),
    "finch": (5, 4, 410),
    "orbit": (5, 3, 470),
    "needle": (8, 5, 380),
    "moth": (5, 3, 590),
    "anchor": (3, 2, 860),
    "orca": (3, 2, 700),
}

CHARACTERS = ("puddle", "bumble", "jelly", "sprout", "finch", "orbit")
HEADING_ANGLES = {1: 180, 2: 90, 3: -90}


def draw_oval(surface, point, color, x, y, width, height):
    left, top = point(x, y)
    right, bottom = point(x + width, y + height)
    pygame.draw.ellipse(surface, color, (left, top, right - left, bottom - top))


def character_shell(surface, point, scale, key, shell):
    def oval(color, x, y, width, height):
        draw_oval(surface, point, color, x, y, width, height)

    if key == "puddle":
        oval((141, 85, 36), -18, -12, 36, 37)
        oval(shell, -17, -14, 34, 36)
        oval((255, 231, 137), -15, -13, 30, 29)
        oval((255, 222, 114), -14, -24, 28, 25)
        oval((255, 238, 155), -12, -23, 24, 20)
        oval((233, 121, 41), -7, -8, 14, 8)
        oval((255, 171, 78), -7, -9, 14, 6)
    elif key == "bumble":
        oval((87, 61, 55), -17, -24, 34, 47)
        oval(shell, -15, -23, 30, 44)
        for y, width in ((-4, 29), (7, 26)):
            oval((86, 63, 73), -width / 2, y, width, 8)
        oval((255, 221, 125), -13, -22, 26, 21)
        for side in (-1, 1):
            pygame.draw.aaline(surface, (242, 191, 107), point(side * 7, -19), point(side * 13, -28))
            pygame.draw.circle(surface, (255, 225, 157), point(side * 13, -28), max(2, round(2.5 * scale)))
    elif key == "jelly":
        oval((118, 79, 167), -22, -25, 44, 35)
        oval((205, 167, 245), -21, -24, 42, 30)
        oval((189, 142, 231), -19, -15, 38, 22)
        oval((236, 212, 255), -15, -22, 20, 5)
        for x in (-8, 0, 8):
            oval((215, 182, 253), x - 3, 0, 6, 10)
    elif key == "sprout":
        oval((55, 111, 100), -18, -15, 36, 38)
        oval(shell, -16, -16, 32, 36)
        oval((198, 244, 211), -14, -13, 28, 26)
        oval((231, 255, 231), -8, -11, 11, 4)
        pygame.draw.aaline(surface, (60, 138, 101), point(0, -12), point(0, -25))
    elif key == "finch":
        pygame.draw.polygon(surface, (52, 112, 156),
                            [point(-10, 13), point(10, 13), point(8, 31), point(0, 27), point(-8, 31)])
        oval((52, 112, 156), -17, -13, 34, 37)
        oval(shell, -16, -13, 32, 35)
        oval((255, 210, 157), -11, -7, 22, 26)
    else:
        for side in (-1, 1):
            oval((87, 102, 123), side * 20 - 5, -9, 10, 21)
            oval((255, 149, 89), side * 21 - 3, -6, 6, 15)
        oval((80, 98, 124), -21, -25, 42, 48)
        oval(shell, -19, -24, 38, 44)
        oval((255, 254, 250), -15, -23, 27, 9)
        oval((92, 177, 192), -17, -16, 34, 29)
        oval((22, 59, 82), -15, -14, 30, 24)
        oval((35, 101, 118), -14, -12, 28, 13)
        oval((189, 233, 238), -10, -12, 13, 2)
        oval((105, 128, 159), -10, 14, 20, 4)
        oval((255, 162, 103), -4, 14, 8, 4)


def character_animation(image, local, scale, airframe, now, thrust, powered, landed, turn_look):
    key = airframe.key
    wave = math.sin(now / (43 if key == "bumble" else 130))
    look = round(math.sin(now / 445) * 5) if key == "finch" else 0
    if key == "puddle":
        for side in (-1, 1):
            foot_y = 28 if landed else 18 + (wave * 2 * side)
            x = side * 7
            foot = [local(x - 2, foot_y - 5), local(x - 5, foot_y + 2),
                    local(x, foot_y + 3), local(x + 5, foot_y + 2), local(x + 2, foot_y - 5)]
            pygame.draw.polygon(image, (241, 137, 59), foot)
            draw_oval(image, local, (245, 181, 62), side * 8 - 5, 6 + wave * side, 10, 9)
    elif key == "bumble":
        spread = 5 * wave
        for side in (-1, 1):
            wing = [local(side * x, y) for x, y in ((13, -4), (22 + spread, -7), (32, 2), (25, 11), (14, 8))]
            pygame.draw.polygon(image, (217, 242, 252), wing)
            pygame.draw.aalines(image, (149, 191, 221), True, wing)
            pygame.draw.aaline(image, (163, 204, 229), wing[0], wing[2])
    elif key == "jelly":
        extension = 9 if powered else 5 if thrust else 0
        for x in (-13, -5, 5, 13):
            tail = [local(x + math.sin(now / 125 + x / 4 + segment) * segment,
                          6 + segment * (4 + extension / 4)) for segment in range(5)]
            pygame.draw.lines(image, (145, 99, 202), False, tail, max(1, round(3 * scale)))
            pygame.draw.aalines(image, airframe.accent, False, tail)
    elif key == "finch":
        spread = 16 if landed else 28 + wave * 4
        for side in (-1, 1):
            wing = [local(side * x, y) for x, y in ((10, -3), (spread, -10),
                    (spread - 1, 5), (spread - 5, 13), (11, 13))]
            pygame.draw.polygon(image, (84, 172, 205), wing)
            pygame.draw.aalines(image, (147, 221, 234), False, wing)
            for start, end in (((12, 2), (spread - 4, -2)), ((12, 7), (spread - 5, 5))):
                pygame.draw.aaline(image, (53, 128, 168), local(side * start[0], start[1]),
                                   local(side * end[0], end[1]))
        draw_oval(image, local, (111, 194, 224), look - 13, -25, 26, 24)
        draw_oval(image, local, (245, 236, 209), look - 9, -19, 18, 15)
        pygame.draw.polygon(image, (247, 169, 91),
                            [local(look - 3, -10), local(look + 3, -10), local(look, -5)])
    elif key == "orbit":
        glance = turn_look if turn_look is not None else math.sin(now / 460) * 3
        for side in (-1, 1):
            eye = local(side * 5 + glance, -3)
            pygame.draw.circle(image, (42, 145, 154), eye, max(2, round(3.3 * scale)))
            pygame.draw.circle(image, airframe.accent, eye, max(1, round(2 * scale)))
            if landed:
                x = side * 9
                pygame.draw.line(image, (145, 162, 183), local(x, 18), local(x, 28),
                                 max(1, round(2.5 * scale)))
                draw_oval(image, local, (238, 131, 73), x - 5, 26, 10, 5)
                draw_oval(image, local, (255, 204, 156), x - 4, 26, 7, 1.8)
        return
    elif landed:
        for petal in range(5):
            angle = petal * math.tau / 5
            at = local(5 * math.cos(angle), -21 + 5 * math.sin(angle))
            pygame.draw.circle(image, (255, 205, 219), at, max(1, round(4 * scale)))
        pygame.draw.circle(image, (255, 212, 106), local(0, -21), max(1, round(3 * scale)))
    else:
        bend = wave * 2 + (3 if thrust else 0)
        for side in (-1, 1):
            leaf = [local(side * x, y + bend) for x, y in ((0, -19), (3, -28), (14, -32), (10, -23))]
            pygame.draw.polygon(image, (100, 211, 130), leaf)
            pygame.draw.aaline(image, (185, 251, 155), leaf[0], leaf[2])

    eye_y = -13 if key in ("puddle", "bumble", "finch") else -5
    ink = (72, 49, 82) if key != "sprout" else (46, 101, 83)
    for x in (look - 6, look + 6):
        if (now + 480) % 2900 < 125:
            pygame.draw.aaline(image, ink, local(x - 2, eye_y), local(x + 2, eye_y))
        else:
            pygame.draw.circle(image, ink, local(x, eye_y), max(1, round(2.15 * scale)))
            if scale > 1:
                pygame.draw.circle(image, ui.WHITE, local(x - 0.6, eye_y - 0.7), round(scale))
    if key not in ("puddle", "finch"):
        pygame.draw.aalines(image, ink, False, [local(-2, eye_y + 4), local(0, eye_y + 5), local(2, eye_y + 4)])


@lru_cache(maxsize=40)
def chassis(airframe, size):
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    scale = size / 72

    def point(x, y):
        return round((36 + x) * scale), round((36 + y) * scale)

    def line(color, a, b, width):
        pygame.draw.line(surface, color, point(*a), point(*b), max(1, round(width * scale)))

    shell, accent = airframe.shell, airframe.accent
    for x, y in ROTOR_LAYOUT[airframe.key]:
        sx = 1 if x > 0 else -1
        sy = 1 if y > 0 else -1
        joint = (sx * 6, sy * 7)
        line((15, 20, 31), joint, (x, y), 9)
        line((73, 83, 103), joint, (x, y), 5)
        line(ui.lerp_color(accent, shell, 0.42), (x - sx * 4, y - sy * 4), (x, y), 5)
        motor = point(x, y)
        pygame.draw.circle(surface, (35, 42, 56), motor, max(2, round(6 * scale)))
        if airframe.key in CHARACTERS:
            pygame.draw.circle(surface, accent, motor, max(2, round(9 * scale)), max(1, round(2 * scale)))
        elif airframe.key == "pip":
            for petal in range(5):
                angle = petal * math.tau / 5
                tip = point(x + 6 * math.cos(angle), y + 6 * math.sin(angle))
                pygame.draw.circle(surface, (252, 182, 214) if sy < 0 else (221, 170, 250),
                                   tip, max(2, round(5 * scale)))
            pygame.draw.circle(surface, (86, 57, 91), motor, max(2, round(6 * scale)))
        elif airframe.key in ("moth", "anchor"):
            radius = 11 if airframe.key == "moth" else 9
            pygame.draw.circle(surface, ui.lerp_color(shell, accent, 0.46), motor,
                               max(2, round(radius * scale)), max(1, round(2 * scale)))

    if airframe.key in CHARACTERS:
        character_shell(surface, point, scale, airframe.key, shell)
        return surface
    if airframe.key == "pip":
        for bounds, color in (((-19, -24, 19, 24), (92, 45, 79)),
                              ((-17, -22, 17, 21), shell),
                              ((-15, -21, 15, 15), (255, 196, 222)),
                              ((-9, -19, 4, -14), (255, 231, 242))):
            a, b, c, d = bounds
            left, top = point(a, b)
            right, bottom = point(c, d)
            pygame.draw.ellipse(surface, color, (left, top, right - left, bottom - top))
        for x in (-11, 11):
            pygame.draw.circle(surface, (245, 135, 181), point(x, 0), max(1, round(3.3 * scale)))
        return surface

    outline = [point(x, y) for x, y in SHELLS[airframe.key]]
    pygame.draw.polygon(surface, (24, 29, 43), outline)
    inner = [point(x * 0.86, y * 0.90) for x, y in SHELLS[airframe.key]]
    pygame.draw.polygon(surface, shell, inner)
    pygame.draw.aalines(surface, ui.lerp_color(shell, ui.WHITE, 0.43), True, inner)
    line(ui.lerp_color(shell, (16, 22, 34), 0.48), (-5, -9), (-5, 10), 3)
    for y in (0, 4, 8):
        line(ui.lerp_color(shell, (15, 22, 37), 0.50), (0, y), (6, y), 1.5)
    line(accent, (-4, -12), (4, -12), 4)
    pygame.draw.circle(surface, (15, 24, 41), point(0, -17), max(1, round(3 * scale)))
    pygame.draw.circle(surface, ui.lerp_color(accent, ui.WHITE, 0.62), point(0, -18),
                       max(1, round(1.4 * scale)))
    dark = ui.lerp_color(shell, (16, 22, 34), 0.68)
    steel = ui.lerp_color(shell, ui.WHITE, 0.52)
    for x in (-1, 1):
        if airframe.key == "needle":
            pod = [point(x * a, b) for a, b in ((8, 0), (14, 3), (20, 16), (10, 16))]
            pygame.draw.polygon(surface, dark, pod)
            line(steel, (x * 10, 1), (x * 16, 13), 1)
            line(accent, (x * 12, 14), (x * 17, 14), 2)
        elif airframe.key == "moth":
            line(dark, (x * 12, -8), (x * 12, 11), 6)
            line(accent, (x * 14, -5), (x * 14, 6), 1)
            line(steel, (x * 8, -11), (x * 11, -17), 2)
        elif airframe.key == "anchor":
            vane = [point(x * a, b) for a, b in ((10, -12), (18, -7), (17, 13), (10, 17))]
            pygame.draw.polygon(surface, dark, vane)
            line(steel, (x * 13, -9), (x * 13, 12), 2)
            for y in (-6, 1, 8):
                line(accent, (x * 13, y), (x * 17, y + 2), 1)
        for y in (-7, 13):
            pygame.draw.circle(surface, steel, point(x * 7, y), max(1, round(scale * 0.9)))
    return surface


def draw_airframe(surface, center, size, airframe, now, direction=None, *,
                  thrust=False, powered=False, landed=False, turn_from=None, turn_progress=1):
    size = round(size)
    image = chassis(airframe, size).copy()
    scale = size / 72
    glow = (1 + math.sin(now / 125)) / 2
    roll, lift, cadence = HOVER_MOTION[airframe.key]
    wave = 0 if landed else math.sin(now / cadence)
    facing = HEADING_ANGLES.get(direction, 0)
    turn_look = None
    if airframe.key == "orbit" and turn_from is not None and not landed:
        start = HEADING_ANGLES.get(turn_from, 0)
        change = (facing - start + 180) % 360 - 180
        ease = turn_progress * turn_progress * (3 - 2 * turn_progress)
        facing = start + change * ease
        turn_look = math.copysign(4.5 * (1 - turn_progress), -change) if change else 0
    for index, (x, y) in enumerate(ROTOR_LAYOUT[airframe.key]):
        px, py = (36 + x) * scale, (36 + y) * scale
        angle = now / 22 * (-1 if index % 2 else 1) + index
        for offset, tint in ((-0.55, (79, 104, 136)), (0, (199, 217, 235))):
            dx, dy = math.cos(angle + offset) * scale * 8, math.sin(angle + offset) * scale * 8
            pygame.draw.aaline(image, tint, (px - dx, py - dy), (px + dx, py + dy))
        pygame.draw.circle(image, (224, 234, 243), (round(px), round(py)), max(1, round(scale * 1.5)))

    def local(x, y):
        return round((36 + x) * scale), round((36 + y) * scale)

    light = ui.lerp_color(airframe.shell, airframe.accent, 0.42 + glow * 0.58)
    if airframe.key in CHARACTERS:
        character_animation(image, local, scale, airframe, now, thrust, powered, landed, turn_look)
    elif airframe.key == "pip":
        ink = (83, 44, 76)
        for x in (-6, 6):
            if now % 2700 < 145:
                pygame.draw.aaline(image, ink, local(x - 2, -6), local(x + 2, -6))
            else:
                pygame.draw.circle(image, ink, local(x, -6), max(1, round(2.3 * scale)))
                if size >= 60:
                    pygame.draw.circle(image, ui.WHITE, local(x - 0.6, -7), max(1, round(0.75 * scale)))
        pygame.draw.aalines(image, ink, False, [local(-3, -2), local(0, 0), local(3, -2)])
        heart = ui.lerp_color((207, 57, 121), (255, 140, 191), glow)
        for x in (-2.7, 2.7):
            pygame.draw.circle(image, heart, local(x, 8), max(1, round(3.4 * scale)))
        pygame.draw.polygon(image, heart, [local(-6, 9), local(6, 9), local(0, 16)])
    elif airframe.key == "needle":
        for x in (-14, 14):
            length = 6 + 6 * glow + (5 if powered else 0)
            flame = [local(x - 2, 16), local(x + 2, 16), local(x, 16 + length)]
            pygame.draw.polygon(image, light, flame)
    elif airframe.key == "moth":
        radar = local(0, 3)
        pygame.draw.circle(image, (27, 23, 44), radar, max(2, round(7 * scale)))
        pygame.draw.circle(image, light, radar, max(2, round(6 * scale)), max(1, round(scale)))
        sweep = now / 230
        tip = local(5 * math.cos(sweep), 3 + 5 * math.sin(sweep))
        pygame.draw.aaline(image, light, radar, tip)
    elif airframe.key == "anchor":
        for side in (-1, 1):
            x = side * 17
            spread = 5 if powered else 1 + glow * 2
            vane = [local(x, -7), local(x + side * spread, -2),
                    local(x + side * spread, 10), local(x, 14)]
            pygame.draw.polygon(image, (36, 54, 49), vane)
            pygame.draw.aalines(image, light, False, vane)
    else:
        pygame.draw.circle(image, light, local(0, 13), max(1, round(scale * 1.6)))

    if airframe.key == "jelly" and not landed:
        expanded = 1 + 0.07 * wave
        image = pygame.transform.smoothscale(image, (round(size / expanded), round(size * expanded)))
    image = pygame.transform.rotozoom(image, facing + roll * wave, 1 - (0.035 if thrust else 0))
    hover = 0 if landed else round(scale * lift * math.sin(now / cadence + 1.2))
    drift = round(scale * 3 * math.sin(now / 220)) if airframe.key == "bumble" and not landed else 0
    shadow = pygame.Rect(0, 0, round(size * (0.55 + 0.05 * wave)), max(3, round(size * 0.13)))
    shadow.center = center[0], center[1] + round(size * 0.32)
    pygame.draw.ellipse(surface, (12, 17, 29), shadow)
    surface.blit(image, image.get_rect(center=(center[0] + drift, center[1] - hover)))

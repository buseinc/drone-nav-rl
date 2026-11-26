"""Shared colors, fonts and drawing helpers for every game mode."""

import math

import pygame

from src.drone_env_v4 import MOVES

WIDTH, HEIGHT = 1100, 720

BG = (11, 16, 29)
PANEL = (25, 35, 55)
PANEL_LIGHT = (38, 52, 78)
EMPTY = (33, 45, 66)
EMPTY_EDGE = (41, 55, 79)
FOG = (17, 23, 38)
OBSTACLE = (224, 91, 94)
OBSTACLE_DARK = (150, 52, 62)
DRONE = (65, 190, 255)      # AI drone
PLAYER = (255, 170, 70)     # human drone
GOAL = (81, 220, 150)
WHITE = (240, 244, 250)
MUTED = (155, 170, 190)
DIM = (90, 102, 125)
GOLD = (255, 214, 90)
WIND = (36, 74, 98)
WIND_ARROW = (120, 210, 240)
ENEMY = (235, 70, 160)

ACTION_NAMES = ["UP", "DOWN", "LEFT", "RIGHT", "HOVER"]
KEY_TO_ACTION = {
    pygame.K_UP: 0, pygame.K_DOWN: 1, pygame.K_LEFT: 2, pygame.K_RIGHT: 3,
    pygame.K_w: 0, pygame.K_s: 1, pygame.K_a: 2, pygame.K_d: 3,
}

_FONTS = {}
_TEXT_CACHE = {}

DISPLAY = "bahnschrift,segoeuiblack,arialblack,arial"
BODY = "segoeuisemibold,segoeui,arial"
MONO = "consolas,couriernew"


def init_fonts():
    _FONTS.update({
        "logo": pygame.font.SysFont(DISPLAY, 132, bold=True),
        "huge": pygame.font.SysFont(DISPLAY, 120, bold=True),
        "xl": pygame.font.SysFont(DISPLAY, 60, bold=True),
        "title": pygame.font.SysFont(DISPLAY, 36, bold=True),
        "lg": pygame.font.SysFont(DISPLAY, 25, bold=True),
        "md": pygame.font.SysFont(BODY, 19),
        "sm": pygame.font.SysFont(BODY, 16),
        "xs": pygame.font.SysFont(BODY, 13),
        "num": pygame.font.SysFont(MONO, 19, bold=True),
        "cell": pygame.font.SysFont(DISPLAY, 18, bold=True),
        "key": pygame.font.SysFont(DISPLAY, 15, bold=True),
    })


def render(s, font, color):
    """Cached text rendering (most labels are the same every frame)."""
    key = (s, font, color)
    img = _TEXT_CACHE.get(key)
    if img is None:
        if len(_TEXT_CACHE) > 3000:
            _TEXT_CACHE.clear()
        img = _FONTS[font].render(s, True, color)
        _TEXT_CACHE[key] = img
    return img


def text(surf, s, pos, color=WHITE, font="md", center=False, right=False):
    img = render(str(s), font, tuple(color))
    rect = img.get_rect()
    if center:
        rect.center = pos
    elif right:
        rect.topright = pos
    else:
        rect.topleft = pos
    surf.blit(img, rect)
    return rect


def big_text(surf, s, center, color, scale=1.0, alpha=255, font="huge"):
    """Scaled, semi-transparent text, for countdowns and banners."""
    img = _FONTS[font].render(str(s), True, color)
    if scale != 1.0:
        w, h = img.get_size()
        img = pygame.transform.smoothscale(
            img, (max(1, int(w * scale)), max(1, int(h * scale))))
    img.set_alpha(int(max(0, min(255, alpha))))
    surf.blit(img, img.get_rect(center=center))


def panel(surf, rect, color=PANEL, radius=14):
    pygame.draw.rect(surf, color, rect, border_radius=radius)


def lerp_color(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


SKY_TOP = (8, 12, 30)
SKY_BOTTOM = (36, 24, 70)
_BG_CACHE = {}


def _gradient(size, top, bottom):
    key = (size, top, bottom)
    if key not in _BG_CACHE:
        w, h = size
        s = pygame.Surface(size)
        for y in range(h):
            pygame.draw.line(s, lerp_color(top, bottom, y / h), (0, y),
                             (w, y))
        _BG_CACHE[key] = s
    return _BG_CACHE[key]


def draw_background(surf, sky=None):
    """Night-sky gradient; with `sky` also stars and drifting clouds."""
    if sky is None:
        surf.blit(_gradient((WIDTH, HEIGHT), BG, (20, 18, 44)), (0, 0))
    else:
        sky.draw(surf)


class Sky:
    """Animated sky shared by the menu screens: stars, clouds, skyline."""

    def __init__(self, seed=7):
        import random
        rnd = random.Random(seed)
        self.stars = [(rnd.randrange(WIDTH), rnd.randrange(HEIGHT * 2 // 3),
                       rnd.random() * 6.28, rnd.choice((1, 1, 2)))
                      for _ in range(110)]
        self.clouds = [[rnd.randrange(-200, WIDTH), rnd.randrange(60, 520),
                        rnd.uniform(0.006, 0.02), rnd.randrange(120, 300),
                        rnd.randrange(14, 30)] for _ in range(9)]
        self.skyline = []
        x = 0
        while x < WIDTH:
            w = rnd.randrange(30, 80)
            h = rnd.randrange(40, 150)
            self.skyline.append((x, w, h, [(rnd.randrange(4, w - 6),
                                            rnd.randrange(8, h - 6))
                                           for _ in range(w * h // 400)]))
            x += w + rnd.randrange(0, 8)
        self._cloud = {}

    def _cloud_img(self, w, alpha):
        key = (w, alpha)
        if key not in self._cloud:
            h = w // 3
            img = pygame.Surface((w, h), pygame.SRCALPHA)
            for i, (fx, fy, fr) in enumerate(((0.3, 0.6, 0.28),
                                              (0.55, 0.45, 0.33),
                                              (0.75, 0.62, 0.24),
                                              (0.5, 0.7, 0.3))):
                pygame.draw.ellipse(img, (150, 140, 220, alpha),
                                    pygame.Rect(int(w * (fx - fr)),
                                                int(h * (fy - fr * 1.2)),
                                                int(w * fr * 2),
                                                int(h * fr * 2.2)))
            self._cloud[key] = img
        return self._cloud[key]

    def draw(self, surf, skyline=True):
        t = pygame.time.get_ticks()
        surf.blit(_gradient((WIDTH, HEIGHT), SKY_TOP, SKY_BOTTOM), (0, 0))
        for x, y, ph, size in self.stars:
            b = 0.55 + 0.45 * math.sin(t / 700 + ph)
            surf.fill(lerp_color(SKY_TOP, WHITE, b), (x, y, size, size))
        for c in self.clouds:
            x = (c[0] + t * c[2]) % (WIDTH + 400) - 300
            surf.blit(self._cloud_img(c[3], c[4]), (x, c[1]))
        if skyline:
            base = HEIGHT
            for x, w, h, windows in self.skyline:
                pygame.draw.rect(surf, (14, 12, 34), (x, base - h, w, h))
                for wx, wy in windows:
                    if (wx * 7 + wy * 3 + t // 1500) % 9 == 0:
                        continue
                    surf.fill((70, 60, 120), (x + wx, base - h + wy, 3, 3))


_LOGO = {}


def _logo_surfaces(scale):
    """Gradient-filled logo text and its soft glow (built once)."""
    if scale not in _LOGO:
        img = _FONTS["logo"].render("SKYRUSH", True, WHITE)
        if scale != 1.0:
            img = pygame.transform.smoothscale(
                img, (int(img.get_width() * scale),
                      int(img.get_height() * scale)))
        w, h = img.get_size()
        fill = pygame.Surface((w, h), pygame.SRCALPHA)
        fill.blit(_gradient((w, h), (120, 230, 255), (255, 120, 200)), (0, 0))
        fill.blit(img, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        # Glow: pad with transparent space, shrink and grow again = blur
        # that fades out softly instead of ending in a hard rectangle.
        pad = 70
        padded = pygame.Surface((w + 2 * pad, h + 2 * pad), pygame.SRCALPHA)
        padded.blit(img, (pad, pad))
        pw, ph = padded.get_size()
        small = pygame.transform.smoothscale(padded, (max(1, pw // 14),
                                                      max(1, ph // 14)))
        glow = pygame.transform.smoothscale(small, (pw, ph))
        glow.fill((80, 170, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
        _LOGO[scale] = (fill, glow)
    return _LOGO[scale]


def draw_logo(surf, center, scale=1.0):
    """SKYRUSH with a gradient fill, pulsing glow and speed lines."""
    t = pygame.time.get_ticks()
    fill, glow = _logo_surfaces(scale)
    w, h = fill.get_size()
    rect = fill.get_rect(center=center)
    glow.set_alpha(150 + int(60 * math.sin(t / 500)))
    surf.blit(glow, glow.get_rect(center=center))
    # speed lines on the left
    for i in range(5):
        y = rect.top + h * (0.25 + i * 0.13)
        length = 60 + 50 * ((i * 37 + t // 40) % 7) / 7
        pygame.draw.line(surf, lerp_color(SKY_TOP, (120, 230, 255), 0.6),
                         (rect.left - 20 - length, y), (rect.left - 20, y), 3)
    surf.blit(fill, rect)
    return rect


def key_cap(surf, label, pos, active=True):
    """A small keyboard-key badge, e.g. [ENTER]."""
    img = render(label, "key", WHITE if active else DIM)
    rect = img.get_rect()
    box = pygame.Rect(pos[0], pos[1], rect.width + 16, 24)
    pygame.draw.rect(surf, (44, 52, 86) if active else (30, 34, 56), box,
                     border_radius=6)
    pygame.draw.rect(surf, (90, 104, 150) if active else (50, 56, 80), box, 1,
                     border_radius=6)
    surf.blit(img, img.get_rect(center=box.center))
    return box


def hint_bar(surf, items, y=None):
    """Bottom row of key hints: [(key, label), ...], centered."""
    y = HEIGHT - 38 if y is None else y
    widths = []
    for k, label in items:
        cap = render(k, "key", WHITE).get_width() + 24 if k else 0
        widths.append(cap + render(label, "sm", MUTED).get_width() + 26)
    x = (WIDTH - sum(widths)) // 2
    for (k, label), w in zip(items, widths):
        lx = key_cap(surf, k, (x, y)).right + 8 if k else x
        text(surf, label, (lx, y + 2), MUTED, "sm")
        x += w


def glass(surf, rect, color=(30, 34, 70), alpha=200, radius=18,
          border=(80, 90, 150)):
    """Semi-transparent panel."""
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(s, (*color, alpha), s.get_rect(), border_radius=radius)
    surf.blit(s, rect.topleft)
    if border:
        pygame.draw.rect(surf, border, rect, 1, border_radius=radius)


# ---------- grid geometry ----------

def cell_rect(origin, cell, pos):
    r, c = pos
    return pygame.Rect(origin[0] + c * cell, origin[1] + r * cell,
                       cell - 3, cell - 3)


def cell_center(origin, cell, pos):
    """Pixel center of a cell. pos may be fractional (animation)."""
    r, c = pos
    return (int(round(origin[0] + c * cell + (cell - 3) / 2)),
            int(round(origin[1] + r * cell + (cell - 3) / 2)))


def cell_at(origin, cell, grid_size, mouse):
    """Grid cell under the mouse, or None."""
    c = (mouse[0] - origin[0]) // cell
    r = (mouse[1] - origin[1]) // cell
    if 0 <= r < grid_size and 0 <= c < grid_size:
        return (int(r), int(c))
    return None


def view_cells(env, pos=None):
    """Cells inside the AI's VIEW x VIEW window around `pos`."""
    r0, c0 = env.position if pos is None else pos
    half = env.VIEW // 2
    return {(r, c) for r in range(r0 - half, r0 + half + 1)
            for c in range(c0 - half, c0 + half + 1)}


# ---------- drawing ----------

def draw_landing_mark(surf, center, size, color):
    """Draw the same landing ring on the board and in the map preview."""
    pygame.draw.circle(surf, color, center, max(2, round(size * 0.30)),
                       max(1, round(size * 0.075)))


def draw_landing_tile(surf, rect, pulse):
    fill = lerp_color((26, 112, 93), (36, 152, 122), pulse)
    pygame.draw.rect(surf, fill, rect, border_radius=7)
    draw_landing_mark(surf, rect.center, rect.width, (232, 255, 242))


def draw_grid(surf, env, origin, cell, cell_colors=None, visible=None):
    """Board with obstacles and goal.

    cell_colors: optional {cell: color} for empty cells (heat-maps).
    visible: optional set of cells; everything else is hidden in fog.
    """
    size = cell * env.grid_size
    frame = pygame.Rect(origin[0] - 10, origin[1] - 10, size + 17, size + 17)
    pygame.draw.rect(surf, PANEL, frame, border_radius=14)

    ticks = pygame.time.get_ticks()
    pulse = 0.5 + 0.5 * math.sin(ticks / 250)

    for r in range(env.grid_size):
        for c in range(env.grid_size):
            pos = (r, c)
            rect = cell_rect(origin, cell, pos)
            hidden = visible is not None and pos not in visible

            if pos == env.goal:
                draw_landing_tile(surf, rect, pulse)
            elif hidden:
                pygame.draw.rect(surf, FOG, rect, border_radius=6)
            elif pos in env.obstacles:
                # Simple 3D block: dark base + lighter top
                pygame.draw.rect(surf, OBSTACLE_DARK, rect, border_radius=6)
                top = rect.inflate(-6, -6).move(0, -3)
                pygame.draw.rect(surf, OBSTACLE, top, border_radius=5)
            elif pos in getattr(env, "wind", {}):
                base = (cell_colors or {}).get(pos)
                color = lerp_color(base, WIND, 0.6) if base else WIND
                pygame.draw.rect(surf, color, rect, border_radius=6)
                draw_wind(surf, rect, env.wind[pos], ticks)
            else:
                color = (cell_colors or {}).get(pos, EMPTY)
                pygame.draw.rect(surf, color, rect, border_radius=6)
                if not cell_colors:
                    pygame.draw.rect(surf, EMPTY_EDGE, rect, 1,
                                     border_radius=6)


def draw_wind(surf, rect, direction, ticks):
    """Two chevrons sliding in the wind direction."""
    dr, dc = direction
    size = rect.width * 0.16
    for k in range(2):
        phase = ((ticks / 600.0) + k * 0.5) % 1.0
        off = (phase - 0.5) * rect.width * 0.7
        cx = rect.centerx + dc * off
        cy = rect.centery + dr * off
        tip = (cx + dc * size, cy + dr * size)
        back = (cx - dc * size, cy - dr * size)
        p1 = (back[0] - dr * size, back[1] + dc * size)
        p2 = (back[0] + dr * size, back[1] - dc * size)
        alpha = 1 - abs(phase - 0.5) * 2
        color = lerp_color(WIND, WIND_ARROW, alpha)
        pygame.draw.lines(surf, color, False, [p1, tip, p2], 3)


def draw_enemies(surf, env, origin, cell, tick, progress, visible=None,
                 warn=True, warn_tick=None):
    """Enemy drones gliding from tick-1 to tick, plus a warning on the
    cells they will occupy on the next tick (the AI's enemy_next input).
    """
    if not getattr(env, "enemies", None):
        return
    for e in env.enemies:
        track = e["track"]
        if visible is not None and not any(c in visible for c in track):
            continue
        a, b = track[0], track[-1]
        pygame.draw.line(surf, lerp_color(ENEMY, BG, 0.75),
                         cell_center(origin, cell, a),
                         cell_center(origin, cell, b), 6)

    next_tick = tick + 1 if warn_tick is None else warn_tick
    for e in env.enemies:
        nxt = env.enemy_pos(e, next_tick)
        if warn and (visible is None or nxt in visible):
            rect = cell_rect(origin, cell, nxt).inflate(-4, -4)
            pygame.draw.rect(surf, ENEMY, rect, 2, border_radius=6)

    k = progress    # constant speed: patrols glide without stopping
    for e in env.enemies:
        p0 = env.enemy_pos(e, tick - 1) if tick > 0 else env.enemy_pos(e, 0)
        p1 = env.enemy_pos(e, tick)
        pos = (p0[0] + (p1[0] - p0[0]) * k, p0[1] + (p1[1] - p0[1]) * k)
        if visible is not None and (round(pos[0]), round(pos[1])) \
                not in visible:
            continue
        draw_enemy(surf, pos, origin, cell)


def draw_enemy(surf, pos, origin, cell):
    cx, cy = cell_center(origin, cell, pos)
    r = int(cell * 0.3)
    angle = pygame.time.get_ticks() / 200.0
    pts = []
    for i in range(12):
        a = angle + i * math.pi / 6
        rad = r if i % 2 == 0 else r * 0.62
        pts.append((cx + math.cos(a) * rad, cy + math.sin(a) * rad))
    pygame.draw.polygon(surf, ENEMY, pts)
    pygame.draw.circle(surf, (60, 10, 40), (cx, cy), int(r * 0.45))
    pygame.draw.circle(surf, WHITE, (cx, cy), max(2, int(r * 0.18)))


def draw_path(surf, path, origin, cell, color, width=4):
    if len(path) > 1:
        pts = [cell_center(origin, cell, p) for p in path]
        pygame.draw.lines(surf, color, False, pts, width)


def draw_dots(surf, path, origin, cell, color, radius=4):
    """Dotted line, used for the optimal route."""
    for p in path:
        pygame.draw.circle(surf, color, cell_center(origin, cell, p), radius)


def draw_drone(surf, pos, origin, cell, color):
    """Quad-copter with spinning rotors. pos may be fractional."""
    cx, cy = cell_center(origin, cell, pos)
    off = int(cell * 0.25)
    rotor = max(4, int(cell * 0.15))
    angle = pygame.time.get_ticks() / 30.0

    # shadow
    shadow = pygame.Rect(0, 0, int(cell * 0.7), int(cell * 0.22))
    shadow.center = (cx + 3, cy + int(cell * 0.36))
    pygame.draw.ellipse(surf, (8, 11, 20), shadow)

    for i, (dx, dy) in enumerate([(-1, -1), (1, -1), (-1, 1), (1, 1)]):
        p = (cx + dx * off, cy + dy * off)
        pygame.draw.line(surf, color, (cx, cy), p, 3)
        pygame.draw.circle(surf, lerp_color(color, BG, 0.6), p, rotor)
        a = angle * (1 if i % 2 else -1)
        bx, by = math.cos(a) * rotor, math.sin(a) * rotor
        pygame.draw.line(surf, WHITE, (p[0] - bx, p[1] - by),
                         (p[0] + bx, p[1] + by), 2)
    pygame.draw.circle(surf, color, (cx, cy), max(5, int(cell * 0.17)))
    pygame.draw.circle(surf, WHITE, (cx, cy), max(2, int(cell * 0.07)))


def draw_arrow(surf, center, action, length, color, width=3):
    if action == 4:    # hover: a small ring instead of an arrow
        pygame.draw.circle(surf, color, center, max(4, int(length * 0.4)),
                           width)
        return
    dr, dc = MOVES[action]
    x, y = center
    tip = (x + dc * length, y + dr * length)
    head = max(4.0, length * 0.45)
    base = (tip[0] - dc * head, tip[1] - dr * head)
    # perpendicular of screen direction (dc, dr) is (-dr, dc)
    p1 = (base[0] - dr * head * 0.6, base[1] + dc * head * 0.6)
    p2 = (base[0] + dr * head * 0.6, base[1] - dc * head * 0.6)
    pygame.draw.line(surf, color, center, base, width)
    pygame.draw.polygon(surf, color, [tip, p1, p2])


def star(surf, center, size, filled=True, color=GOLD):
    cx, cy = center
    pts = []
    for k in range(10):
        ang = -math.pi / 2 + k * math.pi / 5
        rad = size / 2 if k % 2 == 0 else size / 4.5
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    if filled:
        pygame.draw.polygon(surf, color, pts)
    else:
        pygame.draw.polygon(surf, DIM, pts, 2)


def stars(surf, count, pos, size=26, total=3):
    """Draw `total` stars, `count` of them filled."""
    for i in range(total):
        star(surf, (pos[0] + i * (size + 8), pos[1]), size, i < count)


def star_rating(event, steps, optimal):
    """1 star: reached the goal, 2: within 25% of optimal, 3: optimal."""
    if event != "goal":
        return 0
    if steps <= optimal:
        return 3
    if steps <= optimal * 1.25:
        return 2
    return 1


def held_action():
    """Direction key currently held down, or None."""
    keys = pygame.key.get_pressed()
    for k, a in KEY_TO_ACTION.items():
        if keys[k]:
            return a
    return None

"""Sky Missions: hand-tuned levels in 4 zones, with stars and unlocks.

Every zone ends with a boss duel against ORCA. Maps are generated from
fixed seeds, so every player gets exactly the same missions.
"""

import pygame

from src.drone_env_v4 import DroneEnvV4, HOVER, MOVES
from games.skyrush import common as ui
from games.skyrush.airframe_art import draw_airframe
from games.skyrush.airframes import ANCHOR, BUMBLE, JELLY, MOTH, SPROUT, equipped_airframe
from games.skyrush.flight_equipment import EquippedEnvironment
from src.shared.drone_ctrl import DroneController
from src.shared.effects import Effects
from games.skyrush.save import load_leaderboard, save_leaderboard
from src.shared.scene import Scene
from src.shared.world import AI_NAME, ARENAS, GRACE, LEVELS, TICK, copy_env, \
    make_env

ZONE_MISSIONS = [
    ((0, "First Flight", "Fly to the green landing ring."),
     (1, "Tight Corners", "Slow down before tight turns."),
     (2, "The Maze", "Find a way around the walls.")),
    ((0, "Breeze", "Check the arrows before crossing."),
     (5, "The Hook", "Let the wind carry you around a corner."),
     (4, "Wind Switch", "Ride two winds in opposite directions.")),
    ((0, "Night Watch", "Check where the patrol is going."),
     (4, "Patrol Rhythm", "Time your moves between two patrols."),
     (5, "Follow the Guard", "Slip behind the patrol as it moves away.")),
    ((0, "Thunder", "Watch where the wind pushes you."),
     (1, "Eye of the Storm", "Use the wind and avoid the patrols."),
     (2, "Chaos", "Plan your next turn before moving.")),
]
BOSS_LEVEL = next(index for index, level in enumerate(LEVELS) if level["name"] == "LEGEND")
ZONE_TIPS = [
    ["Hold a direction to keep flying.",
     "Use fewer moves to earn more stars."],
    ["Wind pushes you in the direction of the arrows.",
     "It can move you several tiles at once."],
    ["The pink box shows the patrol's next tile.",
     "Press Space to wait in place."],
    ["Wind can push you into a patrol.",
     "Look two moves ahead."],
]
ZONE_HAZARDS = ("Walls and turns", "Wind currents", "Moving patrols", "Wind and patrols")
MAP_ROWS = tuple(pygame.Rect(54, 139 + row * 105, 626, 91) for row in range(len(ARENAS) + 1))
CIRCUIT_BUTTON = MAP_ROWS[-1]
TAKEOFF_BUTTON = pygame.Rect(728, CIRCUIT_BUTTON.centery - 21, 295, 42)
WIND_SWITCH = (1, 4)
PATROL_RHYTHM = (2, 4)
THE_HOOK = (1, 5)
FOLLOW_THE_GUARD = (2, 5)
RETIRED_PREREQUISITES = {"1-5": "1-2", "2-4": "2-1", "2-5": "2-2"}

_CACHE = {}
_AGENT = []

# Seeds found by the search in mission_env() (takes ~10 s), stored so the
# mission map opens instantly. Delete an entry to search again.
MISSION_SEEDS = {
    (0, 0): 5004, (0, 1): 5027, (0, 2): 5038, (0, 3): 5056,
    (1, 0): 5105, (1, 3): 5173,
    # The old Patrol Zone boss map let Legend match the shortest route.
    (2, 0): 5207, (2, 3): 7638,
    (3, 0): 5302, (3, 1): 5311, (3, 2): 5402, (3, 3): 5372,
}


def boss_is_beatable(env):
    """Legend must land, with a faster route available to the player."""
    if not _AGENT:
        from src.shared.agent import Agent
        _AGENT.append(Agent())
    agent = _AGENT[0]
    if not agent.available:
        return True
    e = copy_env(env)
    done, info = False, {}
    while not done:
        _, _, done, info = e.step(agent.act(e.get_state()))
    return info["event"] == "goal" and e.steps > env.optimal_length()


def wind_switch_env():
    """Fly east on the lower current, turn north, then ride the upper current west."""
    walls = {(6, c) for c in range(8)} | {(3, c) for c in range(7)}
    walls |= {(8, 3), (8, 4), (5, 4), (5, 5), (4, 2), (5, 2)}
    wind = {(7, c): (0, 1) for c in range(2, 8)}
    wind.update({(2, c): (0, -1) for c in range(4, 8)})
    env = DroneEnvV4(seed=0, obstacle_count=0)
    env.set_map(start=(8, 1), goal=(1, 2), obstacles=walls, wind=wind)
    return env


def patrol_rhythm_env():
    """Two opposing sweeps guard the inside route; the east edge is clear."""
    walls = {(6, c) for c in range(9) if c != 3}
    walls.update((3, c) for c in range(9) if c != 6)
    patrols = [
        {"track": [(5, c) for c in range(1, 8)], "phase": 5},
        {"track": [(4, c) for c in range(8, 1, -1)], "phase": 0},
    ]
    env = DroneEnvV4(seed=0, obstacle_count=0)
    env.set_map(start=(8, 1), goal=(1, 6), obstacles=walls, enemies=patrols)
    return env


def hook_env():
    """A single wind stream carries a drone east and then north in one move."""
    walls = {(6, c) for c in range(1, 7)} | {(3, c) for c in range(1, 7) if c != 4}
    walls |= {(8, 4), (8, 5), (5, 2), (4, 5)}
    wind = {(7, c): (0, 1) for c in range(2, 7)}
    wind.update({(row, 7): (-1, 0) for row in range(5, 8)})
    env = DroneEnvV4(seed=0, obstacle_count=0)
    env.set_map(start=(8, 0), goal=(1, 5), obstacles=walls, wind=wind)
    return env


def follow_the_guard_env():
    """Wait in the entry bay, follow the patrol east, and leave before it turns."""
    walls = {(6, c) for c in range(10) if c not in (0, 2, 5)}
    walls |= {(4, c) for c in range(10) if c not in (0, 4, 7)}
    walls |= {(7, 1), (7, 5), (3, 4)}
    patrol = {"track": [(5, c) for c in range(2, 9)], "phase": 8}
    env = DroneEnvV4(seed=0, obstacle_count=0)
    env.set_map(start=(7, 2), goal=(1, 7), obstacles=walls, enemies=[patrol])
    return env


AUTHORED_MAPS = {
    WIND_SWITCH: wind_switch_env, PATROL_RHYTHM: patrol_rhythm_env,
    THE_HOOK: hook_env, FOLLOW_THE_GUARD: follow_the_guard_env,
}


def mission_env(zone, idx):
    """Deterministic map for a mission (cached).

    Long flights usually mean big detours - exactly where ORCA is weakest
    (it only sees 7x7 cells). Boss maps give Legend a finish and leave
    the player a faster route.
    """
    key = (zone, idx)
    if key in AUTHORED_MAPS and key not in _CACHE:
        _CACHE[key] = AUTHORED_MAPS[key]()
    if key not in _CACHE and key in MISSION_SEEDS:
        _CACHE[key] = make_env(zone, seed=MISSION_SEEDS[key],
                               obstacles=10 + 2 * idx)
    if key not in _CACHE:
        boss = idx == 3
        obstacles = 10 + 2 * idx
        min_len = 9 + 2 * idx + zone     # later missions = longer flights
        if boss:
            min_len -= 3
        seed = 5000 + zone * 100 + idx * 10
        best = None
        for tries in range(150):
            env = make_env(zone, seed=seed + tries, obstacles=obstacles)
            if boss and not boss_is_beatable(env):
                continue
            if best is None or env.optimal_length() > best.optimal_length():
                best = env
            if env.optimal_length() >= min_len:
                break
        _CACHE[key] = best
    return _CACHE[key]


def mission_list():
    out = []
    for z, names in enumerate(ZONE_MISSIONS):
        for number, (i, name, brief) in enumerate(names, start=1):
            out.append({"zone": z, "idx": i, "name": name, "boss": False,
                        "id": f"{z}-{i}", "number": number, "brief": brief})
        out.append({"zone": z, "idx": 3, "boss": True, "id": f"{z}-3", "number": 4,
                    "name": f"BOSS: {AI_NAME} {LEVELS[BOSS_LEVEL]['name']}",
                    "brief": f"Reach the pad before {AI_NAME}."})
    return out


MISSIONS = mission_list()
MISSIONS_BY_ZONE = tuple(tuple(i for i, mission in enumerate(MISSIONS)
                               if mission["zone"] == zone)
                         for zone in range(len(ZONE_MISSIONS)))


def mission_star_total(prog):
    return sum(prog.get(mission["id"], 0) for mission in MISSIONS)


def save_stars(mission_id, stars):
    board = load_leaderboard()
    m = board.setdefault("missions", {})
    if stars > m.get(mission_id, 0):
        m[mission_id] = stars
        save_leaderboard(board)


def unlocked(i, prog):
    if i == 0 or prog.get(MISSIONS[i]["id"], 0) > 0:
        return True
    previous = MISSIONS[i - 1]["id"]
    # A replaced mission still counts toward any unlock it already earned.
    retired = RETIRED_PREREQUISITES.get(previous)
    return prog.get(previous, 0) > 0 or prog.get(retired, 0) > 0


# ====================== mission map ======================

class MissionMapScene(Scene):
    def __init__(self, app, selected=None):
        super().__init__(app)
        board = load_leaderboard()
        self.prog = board.get("missions", {})
        self.circuit_best = board.get("circuit_best", 0)
        self.circuit_notice = None
        if selected is None:   # first unfinished mission
            selected = next((i for i, m in enumerate(MISSIONS)
                             if self.prog.get(m["id"], 0) == 0
                             and unlocked(i, self.prog)), 0)
        self.sel = selected

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if CIRCUIT_BUTTON.collidepoint(event.pos):
                self.launch_circuit()
            elif TAKEOFF_BUTTON.collidepoint(event.pos):
                self.launch()
            else:
                for zone, nodes in enumerate(MISSIONS_BY_ZONE):
                    for position, index in enumerate(nodes):
                        x, y = self.node_center(zone, position)
                        if pygame.Rect(x - 33, y - 23, 66, 61).collidepoint(event.pos):
                            self.move(index - self.sel)
                            return
            return
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if k == pygame.K_ESCAPE:
            from games.skyrush.menu import MenuScene
            self.app.change(MenuScene(self.app, selected=0))
        elif k in (pygame.K_RIGHT, pygame.K_d):
            self.move(1)
        elif k in (pygame.K_LEFT, pygame.K_a):
            self.move(-1)
        elif k in (pygame.K_DOWN, pygame.K_s):
            self.move_zone(1)
        elif k in (pygame.K_UP, pygame.K_w):
            self.move_zone(-1)
        elif k in (pygame.K_RETURN, pygame.K_SPACE):
            self.launch()
        elif k == pygame.K_c:
            self.launch_circuit()

    def launch_circuit(self):
        if not self.prog.get(MISSIONS[-1]["id"], 0):
            self.app.sound.play("lose")
            return
        from games.skyrush.circuit import start_circuit
        self.app.sound.play("go")
        start_circuit(self.app)

    def move(self, d):
        n = self.sel + d
        if 0 <= n < len(MISSIONS):
            self.sel = n
            self.app.sound.play("click")

    def move_zone(self, direction):
        zone = MISSIONS[self.sel]["zone"]
        neighbor = zone + direction
        if 0 <= neighbor < len(MISSIONS_BY_ZONE):
            position = MISSIONS_BY_ZONE[zone].index(self.sel)
            row = MISSIONS_BY_ZONE[neighbor]
            target = row[-1] if MISSIONS[self.sel]["boss"] else row[min(position, len(row) - 2)]
            self.move(target - self.sel)

    def launch(self):
        m = MISSIONS[self.sel]
        if not unlocked(self.sel, self.prog):
            self.app.sound.play("lose")
            return
        self.app.sound.play("go")
        if m["boss"]:
            from games.skyrush.race import RaceScene
            env = mission_env(m["zone"], 3)
            index = self.sel

            def on_exit(app, winner, stars):
                if winner == "human":
                    save_stars(m["id"], max(1, stars))
                app.change(MissionMapScene(app, index))

            self.app.change(RaceScene(
                self.app, m["zone"], BOSS_LEVEL, fog=False,
                rounds=1, map_env=copy_env(env), on_exit=on_exit,
                title=m["name"]))
        else:
            self.app.change(MissionScene(self.app, self.sel))

    @staticmethod
    def node_center(zone, position):
        count = len(MISSIONS_BY_ZONE[zone])
        return 341 + round(position * 269 / (count - 1)), MAP_ROWS[zone].top + 32

    @staticmethod
    def draw_lock(surf, center, color, size):
        x, y = center
        pygame.draw.circle(surf, color, (x, y - size // 4), size // 3, max(1, size // 10))
        lock = pygame.Rect(x - size // 2, y, size, size * 2 // 3)
        pygame.draw.rect(surf, color, lock, border_radius=max(2, size // 7))

    def draw(self, surf):
        ui.draw_background(surf)
        ui.text(surf, "SKY MISSIONS", (54, 25), ui.WHITE, "xl")
        cleared = sum(self.prog.get(m["id"], 0) > 0 for m in MISSIONS)
        ui.text(surf, f"{cleared} / {len(MISSIONS)} missions cleared", (57, 93), ui.MUTED, "md")

        total = mission_star_total(self.prog)
        r = ui.text(surf, f"{total} / {len(MISSIONS) * 3}",
                    (1046, 60), ui.GOLD, "title", right=True)
        ui.star(surf, (r.left - 22, r.centery), 23)
        pygame.draw.line(surf, (58, 70, 102), (55, 125), (1047, 125))

        for zone, arena in enumerate(ARENAS):
            self.draw_zone(surf, zone, arena["color"])
        self.draw_info(surf)
        circuit_open = self.prog.get(MISSIONS[-1]["id"], 0) > 0
        self.draw_circuit(surf, circuit_open)
        if self.circuit_notice:
            ui.text(surf, self.circuit_notice, (ui.WIDTH // 2, 665), ui.GOLD, "sm", center=True)
        controls = [("WASD", "select"), ("ENTER", "start mission")]
        if circuit_open:
            controls.append(("C", "start circuit"))
        controls.append(("ESC", "main menu"))
        ui.hint_bar(surf, controls)

    def draw_circuit(self, surf, is_open):
        row = CIRCUIT_BUTTON
        accent = (178, 174, 255) if is_open else ui.MUTED
        hovered = is_open and row.collidepoint(pygame.mouse.get_pos())
        border = ui.lerp_color(ui.PANEL, accent, 0.75 if hovered else 0.52) if is_open else (52, 63, 97)
        fill = (39, 38, 78) if is_open else (29, 38, 64)
        ui.glass(surf, row, fill, alpha=242 if is_open else 155, border=border, radius=13)
        pygame.draw.rect(surf, accent, (row.x + 1, row.y + 15, 3, row.height - 30), border_radius=2)

        self.draw_circuit_route(surf, row, accent, border, is_open)

        ui.text(surf, "ENDLESS CIRCUIT", (row.centerx, row.centery - 12), accent, "title", center=True)
        if is_open:
            detail = f"Best run · {self.circuit_best:,} cleared" if self.circuit_best else "New courses every run"
        else:
            detail = "Beat the final boss to unlock"
        ui.text(surf, detail, (row.centerx, row.centery + 18), ui.MUTED, "sm", center=True)

        button = pygame.Rect(row.right - 147, row.centery - 21, 128, 42)
        fill = ui.lerp_color(accent, ui.WHITE, 0.18) if hovered else accent
        pygame.draw.rect(surf, fill if is_open else (48, 58, 85), button, border_radius=9)
        ui.text(surf, "Start run" if is_open else "Locked", button.center,
                ui.SKY_TOP if is_open else ui.MUTED, "md", center=True)

    def draw_circuit_route(self, surf, row, accent, border, is_open):
        preview = pygame.Rect(row.left + 19, row.centery - 27, 120, 54)
        background = (20, 26, 49)
        pygame.draw.rect(surf, background, preview, border_radius=10)
        pygame.draw.rect(surf, border, preview, 1, border_radius=10)
        points = [(preview.left + x, preview.top + y)
                  for x, y in ((14, 39), (34, 18), (58, 33), (80, 17), (103, 17))]
        route_color = ui.lerp_color(background, accent, 0.54 if is_open else 0.25)
        pygame.draw.lines(surf, route_color, False, points, 2)
        for point in points[:-1]:
            pygame.draw.circle(surf, background, point, 4)
            pygame.draw.circle(surf, route_color, point, 4, 1)
        ui.draw_landing_mark(surf, points[-1], 14, accent if is_open else route_color)
        if is_open:
            step, elapsed = divmod(pygame.time.get_ticks(), 380)
            index = step % (len(points) - 1)
            x, y = points[index]
            nx, ny = points[index + 1]
            dot = (round(x + (nx - x) * elapsed / 380), round(y + (ny - y) * elapsed / 380))
            pygame.draw.circle(surf, accent, dot, 4)
        else:
            pygame.draw.circle(surf, background, preview.center, 15)
            self.draw_lock(surf, (preview.centerx, preview.centery - 2), accent, 13)

    def draw_zone(self, surf, zone, accent):
        nodes = MISSIONS_BY_ZONE[zone]
        active = self.sel in nodes
        row = MAP_ROWS[zone]
        ui.glass(surf, row, (29, 38, 64), alpha=242 if active else 155,
                 border=ui.lerp_color(ui.PANEL, accent, 0.52) if active else (52, 63, 97), radius=13)
        pygame.draw.rect(surf, accent, (row.x + 1, row.y + 15, 3, row.height - 30), border_radius=2)
        ui.text(surf, ARENAS[zone]["name"], (row.x + 19, row.y + 13), accent, "lg")
        ui.text(surf, ZONE_HAZARDS[zone], (row.x + 21, row.y + 47), ui.MUTED, "sm")

        for position, index in enumerate(nodes):
            x, y = self.node_center(zone, position)
            if position + 1 < len(nodes):
                next_x, _ = self.node_center(zone, position + 1)
                link = accent if self.prog.get(MISSIONS[index]["id"], 0) else (56, 68, 98)
                pygame.draw.line(surf, link, (x, y), (next_x, y), 2)

        for position, index in enumerate(nodes):
            x, y = self.node_center(zone, position)
            self.draw_node(surf, index, (x, y), accent)

    def draw_node(self, surf, index, center, accent):
        m = MISSIONS[index]
        is_open = unlocked(index, self.prog)
        selected = index == self.sel
        earned = self.prog.get(m["id"], 0)
        tone = ui.GOLD if m["boss"] else accent
        face = pygame.Rect(0, 0, 66 if m["boss"] else 37, 36)
        face.center = center
        fill = tone if selected and is_open else (25, 32, 53)
        edge = tone if is_open else (79, 92, 122)
        pygame.draw.rect(surf, (29, 38, 64), face.inflate(9, 9), border_radius=13)
        if selected:
            pygame.draw.rect(surf, ui.WHITE, face.inflate(8, 8), 1, border_radius=13)
        pygame.draw.rect(surf, fill, face, border_radius=9)
        pygame.draw.rect(surf, edge, face, 1, border_radius=9)
        label = "BOSS" if m["boss"] else str(m["number"])
        fg = ui.SKY_TOP if selected and is_open else tone if is_open else ui.MUTED
        ui.text(surf, label, center, fg, "key" if m["boss"] else "cell", center=True)
        x, y = center
        if is_open:
            ui.stars(surf, earned, (x - 19, y + 37), 11)
        else:
            self.draw_lock(surf, (x, y + 35), ui.DIM, 10)

    def draw_info(self, surf):
        from games.skyrush.duel_setup import DuelSetupScene

        m = MISSIONS[self.sel]
        zone = m["zone"]
        accent = ui.GOLD if m["boss"] else ARENAS[zone]["color"]
        box = pygame.Rect(704, MAP_ROWS[0].top, 343, CIRCUIT_BUTTON.bottom - MAP_ROWS[0].top)
        ui.glass(surf, box, (25, 34, 58), alpha=246, radius=15,
                 border=ui.lerp_color(ui.PANEL, accent, 0.6))
        label = "BOSS RACE" if m["boss"] else f"MISSION {zone + 1}-{m['number']}"
        ui.text(surf, label, (728, 156), accent, "key")
        title = f"{AI_NAME} · {LEVELS[BOSS_LEVEL]['name']}" if m["boss"] else m["name"]
        ui.text(surf, title, (727, 177), ui.WHITE, "title")
        ui.text(surf, m["brief"], (728, 225), ui.MUTED, "sm")

        is_open = unlocked(self.sel, self.prog)
        frame = pygame.Rect(728, 253, 295, 162)
        pygame.draw.rect(surf, (16, 24, 43), frame, border_radius=9)
        if is_open:
            env = mission_env(zone, m["idx"])
            cell = 14
            origin = (frame.centerx - env.grid_size * cell // 2, frame.top + 12)
            DuelSetupScene.preview(surf, env, origin, cell)
            for pos, direction in env.wind.items():
                ui.draw_arrow(surf, ui.cell_center(origin, cell, pos),
                              MOVES.index(direction), 4, ui.SKY_TOP, 1)
            ui.text(surf, "S", ui.cell_center(origin, cell, env.start), ui.PLAYER,
                    "xs", center=True)
            ui.text(surf, "S  Start", (795, 430), ui.MUTED, "xs", center=True)
            ui.draw_landing_mark(surf, (852, 430), 18, ui.GOAL)
            ui.text(surf, "Landing pad", (907, 430), ui.MUTED, "xs", center=True)
            best = env.optimal_length()
            for i, (count, description) in enumerate((
                    (1, "Win the race" if m["boss"] else "Land safely"),
                    (2, f"{int(best * 1.25)} moves or fewer"),
                    (3, f"{best} moves or fewer"))):
                y = 457 + i * 27
                ui.stars(surf, count, (736, y + 7), 11, total=count)
                ui.text(surf, description, (800, y), ui.WHITE, "sm")
        else:
            self.draw_lock(surf, (frame.centerx, 314), ui.MUTED, 31)
            ui.text(surf, "Mission locked", (frame.centerx, 371), ui.WHITE, "lg", center=True)
            previous = MISSIONS[self.sel - 1]
            name = f"{ARENAS[previous['zone']]['name']} boss" if previous["boss"] else previous["name"]
            ui.text(surf, "Complete this mission first", (box.centerx, 453), ui.MUTED, "sm", center=True)
            ui.text(surf, name, (box.centerx, 482), ui.WHITE, "md", center=True)

        color = accent if is_open else (48, 58, 85)
        pygame.draw.rect(surf, color, TAKEOFF_BUTTON, border_radius=9)
        action = "Race ORCA" if m["boss"] else "Start mission"
        ui.text(surf, action if is_open else "Locked", TAKEOFF_BUTTON.center,
                ui.SKY_TOP if is_open else ui.MUTED, "lg", center=True)


# ====================== mission flight ======================

CELL = 54
ORIGIN = (60, 118)


class FlightScene(Scene):
    require_wind = False

    def __init__(self, app, base):
        super().__init__(app)
        self.base = base
        self.airframe = equipped_airframe()
        self.fx = Effects()
        self.retry()

    def retry(self):
        self.env = EquippedEnvironment(self.base, self.require_wind)
        self.ctrl = DroneController(self.env, TICK, linear=True)
        self.opt_ticks, self.optimal = self.env.optimal_route()
        self.event = None
        self.started = False
        self.waiting = False
        self.tick_clock = 0
        self.ticks = 0
        self.queued = None
        self.end_timer = 0
        self.stars = 0
        self.armed = False
        self.charges = self.airframe.charges
        self.powered_move = False
        self.turn_from = None
        self.heading = None

    def px(self):
        return ui.cell_center(ORIGIN, CELL, self.ctrl.pos())

    def flight_key(self, k):
        if k == pygame.K_q and not self.event and self.charges:
            self.armed = not self.armed
            self.app.sound.play("click")
            return
        if self.event is None and (k in ui.KEY_TO_ACTION or k == pygame.K_SPACE):
            self.queued = ui.KEY_TO_ACTION.get(k, HOVER)
            if not self.started:
                self.started = True
                self.tick()

    def fly(self, action, duration):
        self.ctrl.move_ms = max(40, duration)
        power = self.env.powered_action(self.airframe.key, action, self.heading) if self.armed else None
        self.powered_move = power is not None
        if power:
            action, self.env.follow_action = power
            self.env.power = self.airframe.key
            self.armed = False
            self.charges -= 1
            self.fx.burst(self.px(), self.airframe.accent, n=12, speed=0.10, life=300, size=3)
        if action != HOVER:
            heading = action if self.env.follow_action is None else self.env.follow_action
            self.turn_from = self.heading if self.heading != heading else None
            self.heading = heading
            self.app.sound.play("move")
        else:
            self.turn_from = None
        self.ctrl.move(action)

    def finish(self, event):
        if self.event:
            return
        self.event = event
        if event == "goal":
            self.fx.celebrate(self.px(), ui.PLAYER)
            self.app.sound.play("goal")
            self.stars = ui.star_rating(event, self.env.steps, self.opt_ticks)
        else:
            self.fx.explosion(self.px())
            self.app.sound.play("crash")
            self.app.shake(12)

    def tick(self):
        if self.waiting:
            self.waiting = False
            self.powered_move = False
            self.turn_from = None
            self.ctrl.move(HOVER)
        ev = self.ctrl.complete()
        if ev:
            self.finish(ev)
        if self.event:
            return
        self.ticks += 1
        action = self.queued if self.queued is not None else ui.held_action()
        self.queued = None
        if action is None:
            self.waiting = True
        else:
            self.fly(action, TICK)

    def update(self, dt):
        self.fx.update(dt)
        if self.ctrl.busy:
            self.fx.trail(self.px(), ui.lerp_color(self.airframe.accent, ui.BG, 0.4))
        if self.event:
            self.end_timer += dt
            self.ctrl.update(dt)
            return
        if self.waiting and self.tick_clock <= GRACE:
            a = self.queued if self.queued is not None else ui.held_action()
            if a is not None:
                self.queued = None
                self.waiting = False
                self.fly(a, TICK - self.tick_clock)
        if self.started:
            self.tick_clock += dt
            while self.tick_clock >= TICK and self.event is None:
                self.tick_clock -= TICK
                self.tick()
            self.ctrl.sync(TICK - self.tick_clock)

    # ---------- drawing ----------

    def draw_flight(self, surf, reveal_solution=False):
        e = self.env
        ui.draw_grid(surf, e, ORIGIN, CELL)
        progress = min(1.0, self.tick_clock / TICK) if self.started else 1.0
        ui.draw_enemies(surf, e, ORIGIN, CELL, self.ticks, progress,
                        warn=self.event is None, warn_tick=e.t + 1)
        ui.draw_path(surf, e.path, ORIGIN, CELL,
                     ui.lerp_color(self.airframe.accent, ui.BG, 0.35), 4)
        if reveal_solution and self.event and self.optimal:
            ui.draw_dots(surf, self.optimal, ORIGIN, CELL, ui.WHITE, 5)
        if self.airframe == MOTH and self.event is None:
            for enemy in e.enemies:
                future = ui.cell_center(ORIGIN, CELL, e.enemy_pos(enemy, e.t + 2))
                pygame.draw.circle(surf, MOTH.accent, future, 20, 2)
        elif self.airframe == SPROUT and self.event is None:
            for path in e.wind_forecasts():
                points = [ui.cell_center(ORIGIN, CELL, cell) for cell in path]
                for (x, y), (nx, ny) in zip(points, points[1:]):
                    for step in (1, 2, 3):
                        dot = (x + (nx - x) * step // 4, y + (ny - y) * step // 4)
                        pygame.draw.circle(surf, SPROUT.accent, dot, 2)
                pygame.draw.rect(surf, SPROUT.accent,
                                 ui.cell_rect(ORIGIN, CELL, path[-1]).inflate(-13, -13),
                                 2, border_radius=8)
        if self.event != "crash":
            moving = self.ctrl.busy
            draw_airframe(surf, self.px(), CELL - 2, self.airframe, pygame.time.get_ticks(), self.heading,
                          thrust=moving and self.ctrl.last_action != HOVER,
                          powered=moving and self.powered_move, landed=self.event == "goal",
                          turn_from=self.turn_from if moving else None, turn_progress=self.ctrl.t)
        self.fx.draw(surf)

    def draw_equipment(self, surf):
        model = self.airframe
        ui.text(surf, model.name.upper(), (660, 594), model.accent, "key")
        if model == MOTH:
            ui.text(surf, "Purple shows two moves ahead", (660, 619), ui.MUTED, "sm")
        elif model == SPROUT:
            ui.text(surf, "Green dots show where nearby wind leads", (660, 619), ui.MUTED, "sm")
        elif model.charges:
            ui.text(surf, f"{self.charges}/{model.charges} charges", (1056, 594), ui.MUTED, "key", right=True)
            if not self.charges:
                status = "No charges left"
            elif model == ANCHOR and not self.env.rode_wind:
                status = "Ride a current before using the brake"
            elif self.armed:
                status = {
                    ANCHOR: "Armed for the next wind tile",
                    BUMBLE: "Press Space to go back one tile",
                    JELLY: "Turn left or right from your heading",
                }.get(model, "Armed for the next move")
            else:
                status = f"Q  Arm {model.power.lower()}"
            ui.text(surf, status, (660, 619), ui.MUTED, "sm")


class MissionScene(FlightScene):
    def __init__(self, app, index):
        self.index = index
        self.mission = MISSIONS[index]
        self.arena = ARENAS[self.mission["zone"]]
        super().__init__(app, mission_env(self.mission["zone"], self.mission["idx"]))

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if k == pygame.K_ESCAPE:
            self.app.change(MissionMapScene(self.app, self.index))
        elif k == pygame.K_r:
            self.retry()
        elif self.event and k in (pygame.K_RETURN, pygame.K_SPACE):
            nxt = self.index + 1
            if self.stars and nxt < len(MISSIONS):
                MissionMapScene(self.app, nxt).launch()
            else:
                self.retry()
        else:
            self.flight_key(k)

    def finish(self, event):
        previous = self.event
        super().finish(event)
        if not previous and event == "goal":
            save_stars(self.mission["id"], self.stars)

    def draw(self, surf):
        ui.draw_background(surf)
        m = self.mission
        ui.text(surf, f"{m['zone'] + 1}-{m['number']}", (60, 30),
                self.arena["color"], "title")
        ui.text(surf, m["name"].upper(), (130, 30), ui.WHITE, "title")
        ui.text(surf, self.arena["name"], (62, 74), ui.MUTED, "sm")
        self.draw_flight(surf, reveal_solution=True)
        self.draw_hud(surf)
        if self.event and self.end_timer > 500:
            self.draw_result(surf)

    def draw_hud(self, surf):
        x = 660
        box = pygame.Rect(x - 20, 108, 420, 300)
        ui.glass(surf, box, alpha=170)
        ui.text(surf, "MOVES", (x, 126), ui.MUTED, "sm")
        ui.text(surf, str(self.env.steps), (x, 146), ui.WHITE, "xl")
        best = self.opt_ticks
        rows = [(3, f"{best} moves"), (2, f"{int(best * 1.25)} moves"),
                (1, "land")]
        for i, (n, label) in enumerate(rows):
            y = 240 + i * 46
            reached = self.env.steps <= (best if n == 3 else best * 1.25) \
                if n > 1 else True
            ui.stars(surf, n, (x + 14, y + 14), 22, total=n)
            ui.text(surf, label, (x + 110, y), ui.WHITE if reached
                    else ui.DIM, "lg")
        if not self.started:
            ui.text(surf, "Press a direction to take off", (x, 420),
                    ui.GOLD, "md")
        tip = pygame.Rect(x - 20, 470, 420, 96)
        ui.glass(surf, tip, alpha=120, border=self.arena["color"])
        ui.text(surf, "TIP", (x, 482), self.arena["color"], "key")
        key = self.mission["zone"], self.mission["idx"]
        tips = ZONE_TIPS[self.mission["zone"]]
        if key == PATROL_RHYTHM:
            tips = ("Wait for each pink box to move past you.",
                    "The far right lane avoids both patrols.")
        elif key == THE_HOOK:
            tips = ("The wind turns at the bend.", "Enter it from the left to ride the whole stream.")
        elif key == FOLLOW_THE_GUARD:
            tips = ("Wait below the lane until the guard heads right.",
                    "Follow it, then leave the lane before it turns.")
        for i, line in enumerate(tips):
            ui.text(surf, line, (x, 506 + i * 24), ui.WHITE, "sm")
        self.draw_equipment(surf)
        ui.hint_bar(surf, [("ARROWS", "fly"), ("SPACE", "hover"),
                           ("R", "retry"), ("ESC", "missions")])

    def draw_result(self, surf):
        overlay = pygame.Surface((ui.WIDTH, ui.HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 8, 20, 170))
        surf.blit(overlay, (0, 0))
        box = pygame.Rect(ui.WIDTH // 2 - 260, 190, 520, 300)
        ui.glass(surf, box, alpha=235)
        cx = box.centerx
        if self.event == "goal":
            ui.text(surf, "MISSION COMPLETE", (cx, 236), ui.GOAL, "title",
                    center=True)
            # stars pop in one by one
            shown = min(self.stars, int((self.end_timer - 500) / 350) + 1)
            ui.stars(surf, shown, (cx - 70, 305), 54)
            ui.text(surf, f"{self.env.steps} moves  ·  best possible "
                          f"{self.opt_ticks}", (cx, 360), ui.WHITE, "md",
                    center=True)
            nxt = self.index + 1 < len(MISSIONS)
            ui.hint_bar(surf, [("ENTER", "next mission" if nxt else "again"),
                               ("R", "retry"), ("ESC", "missions")], y=440)
        else:
            title = "CRASHED" if self.event == "crash" else "OUT OF TIME"
            ui.text(surf, title, (cx, 250), ui.OBSTACLE, "xl", center=True)
            ui.text(surf, "White dots show the best route.", (cx, 330),
                    ui.MUTED, "md", center=True)
            ui.hint_bar(surf, [("R", "retry"), ("ESC", "missions")], y=440)

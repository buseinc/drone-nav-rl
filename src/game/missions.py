"""Sky Missions: 16 hand-tuned levels in 4 zones, with stars and unlocks.

Every zone ends with a boss duel against ORCA. Maps are generated from
fixed seeds, so every player gets exactly the same missions.
"""

import math

import pygame

from src.drone_env_v4 import HOVER
from src.game import common as ui
from src.game.drone_ctrl import DroneController
from src.game.effects import Effects
from src.game.scene import Scene, load_leaderboard, save_leaderboard
from src.game.world import AI_NAME, ARENAS, GRACE, LEVELS, TICK, copy_env, \
    make_env

ZONE_MISSIONS = [
    ["First Flight", "Tight Corners", "The Maze"],
    ["Breeze", "Crosswind", "Jet Stream"],
    ["Night Watch", "Two Guards", "Rush Hour"],
    ["Thunder", "Eye of the Storm", "Chaos"],
]
BOSS_LEVEL = [0, 1, 1, 2]     # ORCA level for each zone's boss duel
ZONE_TIPS = [
    ["Hold a direction to keep flying.",
     "Fewer ticks = more stars."],
    ["Wind pushes you along the arrows,",
     "several cells in one tick. Ride it!"],
    ["Pink frame = where a patrol will be",
     "next tick. SPACE = hover and wait."],
    ["Wind can push you INTO a patrol.",
     "Look two moves ahead."],
]

_CACHE = {}
_AGENT = []

# Seeds found by the search in mission_env() (takes ~10 s), stored so the
# mission map opens instantly. Delete an entry to search again.
MISSION_SEEDS = {
    (0, 0): 5004, (0, 1): 5027, (0, 2): 5038, (0, 3): 5056,
    (1, 0): 5105, (1, 1): 5126, (1, 2): 5143, (1, 3): 5173,
    (2, 0): 5207, (2, 1): 5242, (2, 2): 5270, (2, 3): 5258,
    (3, 0): 5302, (3, 1): 5311, (3, 2): 5402, (3, 3): 5372,
}


def nova_lands(env):
    """Can ORCA (at full skill) fly this map? Bosses must be real fights."""
    if not _AGENT:
        from src.game.agent import Agent
        _AGENT.append(Agent())
    agent = _AGENT[0]
    if not agent.available:
        return True
    e = copy_env(env)
    done, info = False, {}
    while not done:
        _, _, done, info = e.step(agent.act(e.get_state()))
    return info["event"] == "goal"


def mission_env(zone, idx):
    """Deterministic map for a mission (cached).

    Long flights usually mean big detours - exactly where ORCA is weakest
    (it only sees 7x7 cells). So boss maps are also required to be maps
    ORCA can actually fly, otherwise the duel would be a free win.
    """
    key = (zone, idx)
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
            if boss and not nova_lands(env):
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
        for i, name in enumerate(names):
            out.append({"zone": z, "idx": i, "name": name, "boss": False,
                        "id": f"{z}-{i}"})
        out.append({"zone": z, "idx": 3, "boss": True, "id": f"{z}-3",
                    "name": f"BOSS: {AI_NAME} {LEVELS[BOSS_LEVEL[z]]['name']}"})
    return out


MISSIONS = mission_list()


def progress():
    return load_leaderboard().get("missions", {})


def save_stars(mission_id, stars):
    board = load_leaderboard()
    m = board.setdefault("missions", {})
    if stars > m.get(mission_id, 0):
        m[mission_id] = stars
        save_leaderboard(board)


def unlocked(i, prog):
    return i == 0 or prog.get(MISSIONS[i - 1]["id"], 0) > 0


# ====================== mission map ======================

class MissionMapScene(Scene):
    def __init__(self, app, selected=None):
        super().__init__(app)
        self.prog = progress()
        if selected is None:   # first unfinished mission
            selected = next((i for i, m in enumerate(MISSIONS)
                             if self.prog.get(m["id"], 0) == 0
                             and unlocked(i, self.prog)), 0)
        self.sel = selected

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if k == pygame.K_ESCAPE:
            from src.game.menu import MenuScene
            self.app.change(MenuScene(self.app, selected=0))
        elif k in (pygame.K_RIGHT, pygame.K_d):
            self.move(1)
        elif k in (pygame.K_LEFT, pygame.K_a):
            self.move(-1)
        elif k in (pygame.K_DOWN, pygame.K_s):
            self.move(4)
        elif k in (pygame.K_UP, pygame.K_w):
            self.move(-4)
        elif k in (pygame.K_RETURN, pygame.K_SPACE):
            self.launch()

    def move(self, d):
        n = self.sel + d
        if 0 <= n < len(MISSIONS):
            self.sel = n
            self.app.sound.play("click")

    def launch(self):
        m = MISSIONS[self.sel]
        if not unlocked(self.sel, self.prog):
            self.app.sound.play("lose")
            return
        self.app.sound.play("go")
        if m["boss"]:
            from src.game.race import RaceScene
            env = mission_env(m["zone"], 3)
            index = self.sel

            def on_exit(app, winner, stars):
                if winner == "human":
                    save_stars(m["id"], max(1, stars))
                app.change(MissionMapScene(app, index))

            self.app.change(RaceScene(
                self.app, m["zone"], BOSS_LEVEL[m["zone"]], fog=False,
                rounds=1, map_env=copy_env(env), on_exit=on_exit,
                title=m["name"]))
        else:
            self.app.change(MissionScene(self.app, self.sel))

    def draw(self, surf):
        self.app.sky.draw(surf, skyline=False)
        ui.text(surf, "SKY MISSIONS", (60, 28), ui.WHITE, "xl")
        total = sum(self.prog.values())
        r = ui.text(surf, f"{total} / {len(MISSIONS) * 3}",
                    (ui.WIDTH - 60, 44), ui.GOLD, "title", right=True)
        ui.star(surf, (r.left - 24, r.centery), 32)

        t = pygame.time.get_ticks()
        for z, arena in enumerate(ARENAS):
            y = 130 + z * 118
            row = pygame.Rect(50, y, ui.WIDTH - 100, 100)
            ui.glass(surf, row, alpha=150, border=None)
            pygame.draw.rect(surf, arena["color"], (50, y, 6, 100),
                             border_top_left_radius=18,
                             border_bottom_left_radius=18)
            ui.text(surf, arena["name"], (76, y + 18), arena["color"], "lg")
            ui.text(surf, arena["tagline"], (76, y + 52), ui.MUTED, "xs")

            for i in range(4):
                idx = z * 4 + i
                m = MISSIONS[idx]
                cx, cy = 470 + i * 150, y + 44
                if i < 3:
                    pygame.draw.line(surf, (70, 76, 120), (cx + 32, cy),
                                     (cx + 118, cy), 3)
                is_open = unlocked(idx, self.prog)
                stars = self.prog.get(m["id"], 0)
                sel = idx == self.sel
                r = 30 if m["boss"] else 26
                if sel:
                    pr = r + 7 + 3 * math.sin(t / 180)
                    pygame.draw.circle(surf, ui.WHITE, (cx, cy), int(pr), 2)
                fill = (arena["color"] if is_open else (50, 54, 80))
                if is_open and not stars:
                    fill = ui.lerp_color(arena["color"], ui.SKY_TOP, 0.55)
                pygame.draw.circle(surf, fill, (cx, cy), r)
                if not is_open:         # padlock
                    pygame.draw.rect(surf, ui.DIM, (cx - 8, cy - 2, 16, 12),
                                     border_radius=3)
                    pygame.draw.circle(surf, ui.DIM, (cx, cy - 4), 6, 2)
                elif m["boss"]:
                    ui.draw_drone(surf, (0, 0), (cx - 27, cy - 27), 57,
                                  ui.DRONE)
                else:
                    ui.text(surf, str(i + 1), (cx, cy), ui.SKY_TOP, "lg",
                            center=True)
                ui.stars(surf, stars, (cx - 22, cy + 40), 12)

        self.draw_info(surf)
        ui.hint_bar(surf, [("ARROWS", "choose"), ("ENTER", "fly"),
                           ("ESC", "back")])

    def draw_info(self, surf):
        m = MISSIONS[self.sel]
        box = pygame.Rect(50, 606, ui.WIDTH - 100, 58)
        ui.glass(surf, box, alpha=200)
        num = f"{m['zone'] + 1}-{m['idx'] + 1}"
        ui.text(surf, f"{num}  {m['name']}", (74, 618),
                ARENAS[m["zone"]]["color"], "lg")
        if not unlocked(self.sel, self.prog):
            goal = "Locked - earn a star in the previous mission."
        elif m["boss"]:
            lvl = LEVELS[BOSS_LEVEL[m["zone"]]]
            goal = f"Duel: land before {AI_NAME} ({lvl['name']}). " \
                   f"{lvl['desc']}"
        else:
            best = mission_env(m["zone"], m["idx"]).optimal_length()
            x = box.right - 24
            for n, label in ((1, "land"), (2, f"{int(best * 1.25)} ticks"),
                             (3, f"{best} ticks")):
                r = ui.text(surf, label, (x, 622), ui.WHITE, "md", right=True)
                width = n * 22           # star size 14 + spacing 8
                ui.stars(surf, n, (r.left - 8 - width + 7, 634), 14, total=n)
                x = r.left - 8 - width - 26
            return
        ui.text(surf, goal, (box.right - 24, 622), ui.WHITE, "md",
                right=True)


# ====================== mission flight ======================

CELL = 54
ORIGIN = (60, 118)


class MissionScene(Scene):
    def __init__(self, app, index):
        super().__init__(app)
        self.index = index
        self.mission = MISSIONS[index]
        self.base = mission_env(self.mission["zone"], self.mission["idx"])
        self.arena = ARENAS[self.mission["zone"]]
        self.fx = Effects()
        self.retry()

    def retry(self):
        self.env = copy_env(self.base)
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

    def px(self):
        return ui.cell_center(ORIGIN, CELL, self.ctrl.pos())

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
        elif self.event is None and (k in ui.KEY_TO_ACTION
                                     or k == pygame.K_SPACE):
            self.queued = ui.KEY_TO_ACTION.get(k, HOVER)
            if not self.started:
                self.started = True
                self.tick()

    def fly(self, action, duration):
        self.ctrl.move_ms = max(40, duration)
        if action != HOVER:
            self.app.sound.play("move")
        self.ctrl.move(action)

    def finish(self, event):
        if self.event:
            return
        self.event = event
        if event == "goal":
            self.fx.celebrate(self.px(), ui.PLAYER)
            self.app.sound.play("goal")
            self.stars = ui.star_rating(event, self.env.steps, self.opt_ticks)
            save_stars(self.mission["id"], self.stars)
        else:
            self.fx.explosion(self.px())
            self.app.sound.play("crash")
            self.app.shake(12)

    def tick(self):
        if self.waiting:
            self.waiting = False
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
            self.fx.trail(self.px(), ui.lerp_color(ui.PLAYER, ui.BG, 0.4))
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

    def draw(self, surf):
        ui.draw_background(surf)
        e, m = self.env, self.mission
        ui.text(surf, f"{m['zone'] + 1}-{m['idx'] + 1}", (60, 30),
                self.arena["color"], "title")
        ui.text(surf, m["name"].upper(), (130, 30), ui.WHITE, "title")
        ui.text(surf, self.arena["name"], (62, 74), ui.MUTED, "sm")

        ui.draw_grid(surf, e, ORIGIN, CELL)
        progress = min(1.0, self.tick_clock / TICK) if self.started else 1.0
        ui.draw_enemies(surf, e, ORIGIN, CELL, self.ticks, progress,
                        warn=self.event is None)
        ui.draw_path(surf, e.path, ORIGIN, CELL,
                     ui.lerp_color(ui.PLAYER, ui.BG, 0.35), 4)
        if self.event and self.optimal:
            ui.draw_dots(surf, self.optimal, ORIGIN, CELL, ui.WHITE, 5)
        if self.event != "crash":
            ui.draw_drone(surf, self.ctrl.pos(), ORIGIN, CELL, ui.PLAYER)
        self.fx.draw(surf)
        self.draw_hud(surf)
        if self.event and self.end_timer > 500:
            self.draw_result(surf)

    def draw_hud(self, surf):
        x = 660
        box = pygame.Rect(x - 20, 108, 420, 300)
        ui.glass(surf, box, alpha=170)
        ui.text(surf, "TICKS", (x, 126), ui.MUTED, "sm")
        ui.text(surf, str(self.env.steps), (x, 146), ui.WHITE, "xl")
        best = self.opt_ticks
        rows = [(3, f"{best} ticks"), (2, f"{int(best * 1.25)} ticks"),
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
        for i, line in enumerate(ZONE_TIPS[self.mission["zone"]]):
            ui.text(surf, line, (x, 506 + i * 24), ui.WHITE, "sm")
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
            ui.text(surf, f"{self.env.steps} ticks  ·  best possible "
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

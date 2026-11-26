"""DUEL: you and ORCA fly the same map at the same time.

Fairness rules:
  * The world runs in ticks (TICK ms). On every tick each drone makes one
    move (or hovers) and every patrol moves one cell. Mashing keys does
    not help; holding a key keeps flying.
  * The round goes to whoever LANDS FIRST.
  * ORCA's level = how often it hesitates for a tick when it turns.
  * Fog: both drones only see the 7x7 area around them, exactly like
    the neural network does.
"""

from collections import deque

import pygame

from src.drone_env_v4 import HOVER
from games.skyrush import common as ui
from games.skyrush.airframe_art import draw_airframe
from games.skyrush.airframes import ORCA, equipped_airframe
from games.skyrush.duel_finish import (PHOTO_HOLD_MS, REPLAY_TICK_MS,
                                       draw_landing_drone, draw_pad, replay_frame)
from src.shared.drone_ctrl import DroneController
from src.shared.effects import Effects
from games.skyrush.save import load_leaderboard, save_leaderboard
from src.shared.scene import Scene
from src.shared.world import (AI_NAME, ARENAS, GRACE, LEVELS, TICK, AIPilot,
                            copy_env, make_env)

CELL = 44
ORIGIN = {"human": (60, 150), "ai": (600, 150)}
COLOR = {"human": ui.PLAYER, "ai": ui.DRONE}
NAME = {"human": "PILOT", "ai": AI_NAME}

ROUND_TIME = 30_000
COUNTDOWN = 3_000
END_DELAY = 900       # let the explosion / celebration play

EVENT_TEXT = {"goal": "LANDED", "crash": "CRASHED", "timeout": "TIME OUT",
              "dnf": "TOO SLOW"}


class RaceScene(Scene):
    tick_ms = TICK
    show_optimal_route = True

    def __init__(self, app, arena, level, fog=False, rounds=5, map_env=None,
                 on_exit=None, title=None, cinematic_finish=False):
        super().__init__(app)
        self.arena, self.level, self.fog = arena, level, fog
        self.rounds = rounds
        self.map_env = map_env       # fixed map (boss duels)
        self.on_exit = on_exit
        self.cinematic_finish = cinematic_finish
        self.airframes = {"human": equipped_airframe(), "ai": ORCA}
        self.title = title or "DUEL"
        self.round = 0
        self.wins = {"human": 0, "ai": 0}
        self.star_total = {"human": 0, "ai": 0}
        self.fx = Effects()
        self.next_round()

    # ---------- flow ----------

    def next_round(self):
        self.round += 1
        self.envs = self.build_envs()
        self.ctrl = {w: DroneController(e, self.tick_ms, linear=True)
                     for w, e in self.envs.items()}
        self.human_waiting = False
        self.pilot = self.build_pilot()
        self.opt_ticks, self.optimal = self.envs["human"].optimal_route()
        self.results = {"human": None, "ai": None}
        self.round_stars = None
        self.winner = None
        self.phase = "countdown"
        self.timer = 0
        self.tick_clock = 0
        self.ticks = 0
        self.end_timer = 0
        self.queued = None
        self.last_beep = None
        self.replay_moves = {who: deque(maxlen=2) for who in self.ctrl}
        self.photo_elapsed = 0
        self.photo_still = None

    def build_envs(self):
        base = self.map_env or make_env(self.arena)
        return {"human": copy_env(base), "ai": copy_env(base)}

    def build_pilot(self):
        return AIPilot(self.app.agent, self.level)

    def px(self, who):
        return ui.cell_center(ORIGIN[who], CELL, self.ctrl[who].pos())

    def land(self, who, event):
        if self.results[who] is not None:
            return
        self.results[who] = {"event": event, "time": self.timer}
        if event == "goal":
            self.fx.celebrate(self.px(who), COLOR[who])
            self.app.sound.play("goal")
        else:
            self.fx.explosion(self.px(who))
            self.app.sound.play("crash")
            if who == "human":
                self.app.shake(12)

    def tick(self):
        """One world tick: finish last moves, then everyone moves again."""
        if self.human_waiting:
            # No key during the grace window: the last tick was a hover.
            self.human_waiting = False
            self.ctrl["human"].move(HOVER)
        for who, c in self.ctrl.items():
            if self.cinematic_finish and self.ticks and self.results[who] is None:
                self.replay_moves[who].append((tuple(c.points), c.move_ms))
            event = c.complete()
            if event:
                self.land(who, event)

        if self.timer >= ROUND_TIME:
            for who in ("human", "ai"):
                if self.results[who] is None:
                    self.results[who] = {"event": "timeout",
                                         "time": self.timer}
        # First to land wins: the round is decided the moment someone lands.
        if any(r and r["event"] == "goal" for r in self.results.values()):
            for who in ("human", "ai"):
                if self.results[who] is None:
                    self.results[who] = {"event": "dnf", "time": self.timer}
        if all(self.results.values()):
            self.phase = "ending"
            return

        self.ticks += 1
        if self.results["human"] is None:
            action = self.queued if self.queued is not None \
                else ui.held_action()
            self.queued = None
            if action is None:
                self.human_waiting = True    # decide later in this tick
            else:
                self.move_human(action, self.tick_ms)
        if self.results["ai"] is None:
            self.ctrl["ai"].move(self.pilot.act(self.envs["ai"]))

    def move_human(self, action, duration):
        c = self.ctrl["human"]
        c.move_ms = max(40, duration)
        if action != HOVER:
            self.app.sound.play("move")
        c.move(action)

    def finish_round(self):
        def arrival(w):
            r = self.results[w]
            return r["time"] if r["event"] == "goal" else None

        th, ta = arrival("human"), arrival("ai")
        if th is not None and (ta is None or th < ta):
            self.winner = "human"
        elif ta is not None and (th is None or ta < th):
            self.winner = "ai"
        else:
            self.winner = None
        if self.winner:
            self.wins[self.winner] += 1

        self.round_stars = {
            w: ui.star_rating(self.results[w]["event"],
                              self.envs[w].steps, self.opt_ticks)
            for w in ("human", "ai")}
        for w in ("human", "ai"):
            self.star_total[w] += self.round_stars[w]

        self.app.sound.play("win" if self.winner == "human" else "lose"
                            if self.winner == "ai" else "click")
        self.phase = "round_over"

    def simultaneous_landing(self):
        human, ai = self.results["human"], self.results["ai"]
        return (human is not None and ai is not None
                and human["event"] == ai["event"] == "goal"
                and human["time"] == ai["time"])

    @property
    def replay_duration(self):
        return REPLAY_TICK_MS * len(self.replay_moves["human"])

    def match_winner(self):
        h, a = self.wins["human"], self.wins["ai"]
        if h == a:   # tie-break on route quality
            h, a = self.star_total["human"], self.star_total["ai"]
        return "human" if h > a else "ai" if a > h else None

    def finish_match(self):
        self.phase = "match_over"
        w = self.match_winner()
        if self.on_exit is None:
            board = load_leaderboard()
            key = f"{ARENAS[self.arena]['name']} / {LEVELS[self.level]['name']}"
            if self.fog:
                key += " / FOG"
            rec = board.setdefault("duels", {}).setdefault(
                key, {"human": 0, "ai": 0, "draw": 0})
            rec[w or "draw"] += 1
            save_leaderboard(board)
        self.app.sound.play("win" if w == "human" else "lose")

    def leave(self):
        if self.on_exit:
            self.on_exit(self.app, self.match_winner(),
                         self.round_stars["human"] if self.round_stars else 0)
        else:
            from games.skyrush.duel_setup import DuelSetupScene
            self.app.change(DuelSetupScene(self.app))

    # ---------- scene API ----------

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            if self.on_exit and self.phase != "match_over":
                self.on_exit(self.app, None, 0)
            else:
                self.leave()
        elif self.phase == "racing" and event.key in ui.KEY_TO_ACTION:
            self.queued = ui.KEY_TO_ACTION[event.key]
        elif self.phase == "racing" and event.key == pygame.K_SPACE:
            self.queued = HOVER
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.phase == "photo_finish":
                self.finish_round()
            elif self.phase == "round_over":
                if self.round < self.rounds:
                    self.next_round()
                else:
                    self.finish_match()
            elif self.phase == "match_over":
                if self.on_exit:
                    self.leave()
                else:
                    self.app.change(RaceScene(self.app, self.arena,
                                              self.level, self.fog,
                                              self.rounds,
                                              cinematic_finish=self.cinematic_finish))

    def update(self, dt):
        self.fx.update(dt)
        self.timer += dt

        if self.phase == "countdown":
            n = 3 - self.timer // 1000
            if n != self.last_beep and n > 0:
                self.last_beep = n
                self.app.sound.play("beep")
            if self.timer >= COUNTDOWN:
                self.phase, self.timer = "racing", 0
                self.app.sound.play("go")
                self.tick()            # first tick right at "GO!"
            return

        if self.phase == "racing":
            if self.human_waiting and self.tick_clock <= GRACE * self.tick_ms / TICK:
                action = self.queued if self.queued is not None \
                    else ui.held_action()
                if action is not None:
                    # Late start: still counts for this tick, and the drone
                    # flies a bit faster to arrive on time.
                    self.queued = None
                    self.human_waiting = False
                    self.move_human(action, self.tick_ms - self.tick_clock)
            self.tick_clock += dt
            while self.tick_clock >= self.tick_ms and self.phase == "racing":
                self.tick_clock -= self.tick_ms
                self.tick()
            for who, c in self.ctrl.items():
                c.sync(self.tick_ms - self.tick_clock)
                if c.busy:
                    self.fx.trail(self.px(who),
                                  ui.lerp_color(COLOR[who], ui.BG, 0.4))
        elif self.phase == "ending":
            for c in self.ctrl.values():
                c.update(dt)
            self.end_timer += dt
            if self.end_timer >= END_DELAY:
                if self.cinematic_finish and self.simultaneous_landing() and self.replay_duration:
                    self.phase = "photo_finish"
                else:
                    self.finish_round()
        elif self.phase == "photo_finish":
            self.photo_elapsed += dt
            if self.photo_elapsed >= self.replay_duration + PHOTO_HOLD_MS:
                self.finish_round()

    # ---------- drawing ----------

    def draw_board(self, surf, who):
        env, origin = self.envs[who], ORIGIN[who]
        res = self.results[who]
        size = CELL * env.grid_size
        revealed = self.phase in ("round_over", "match_over")

        # name plate
        draw_airframe(surf, (origin[0] + 11, origin[1] - 39), 36,
                      self.airframes[who], pygame.time.get_ticks())
        ui.text(surf, NAME[who], (origin[0] + 34, origin[1] - 50),
                COLOR[who], "lg")
        sub = "you" if who == "human" else LEVELS[self.level]["name"].lower()
        ui.text(surf, sub, (origin[0] + 36, origin[1] - 24), ui.MUTED, "xs")
        ui.text(surf, f"{env.steps}", (origin[0] + size - 3, origin[1] - 52),
                ui.WHITE, "lg", right=True)
        ui.text(surf, "ticks", (origin[0] + size - 3, origin[1] - 24),
                ui.MUTED, "xs", right=True)

        visible = None
        if self.fog and not revealed:
            visible = ui.view_cells(env)
        ui.draw_grid(surf, env, origin, CELL, visible=visible)
        controller = self.ctrl[who]
        position = controller.pos()
        landed = res and res["event"] == "goal"
        if self.cinematic_finish:
            draw_pad(surf, origin, CELL, env.goal, position, COLOR[who],
                     pygame.time.get_ticks(), self.end_timer if landed else None)
        progress = min(1.0, self.tick_clock / self.tick_ms) \
            if self.phase == "racing" else 1.0
        # During tick k patrols glide from pos(k-1) to pos(k); the warning
        # shows pos(k+1), where they will be after the next decision.
        ui.draw_enemies(surf, env, origin, CELL, self.ticks, progress,
                        visible, warn=self.phase == "racing")
        ui.draw_path(surf, env.path, origin, CELL,
                     ui.lerp_color(COLOR[who], ui.BG, 0.35), 3)
        if revealed and self.show_optimal_route and self.optimal:
            ui.draw_dots(surf, self.optimal, origin, CELL, ui.WHITE, 4)
        if not (res and res["event"] == "crash"):
            descent = None
            if self.cinematic_finish and landed:
                descent = 1.0
            elif self.cinematic_finish and controller.pending == "goal":
                descent = controller.t
            draw_landing_drone(surf, origin, CELL, position, self.airframes[who], descent,
                               controller.last_action)

        y = origin[1] + size + 14
        if res:
            c = ui.GOAL if res["event"] == "goal" else ui.OBSTACLE
            ui.text(surf, f"{EVENT_TEXT[res['event']]}  "
                          f"{res['time'] / 1000:.2f}s", (origin[0], y), c,
                    "lg")
        if self.round_stars:
            ui.stars(surf, self.round_stars[who],
                     (origin[0] + size - 80, y + 14), 22)

    def draw_header(self, surf):
        arena = ARENAS[self.arena]
        ui.text(surf, self.title, (60, 18), ui.WHITE, "title")
        tag = arena["name"] + ("  ·  FOG" if self.fog else "")
        ui.text(surf, tag, (62, 62), arena["color"], "sm")

        # big score in the middle
        cx = ui.WIDTH // 2
        ui.text(surf, str(self.wins["human"]), (cx - 40, 46), ui.PLAYER,
                "xl", center=True)
        ui.text(surf, ":", (cx, 42), ui.MUTED, "xl", center=True)
        ui.text(surf, str(self.wins["ai"]), (cx + 40, 46), ui.DRONE, "xl",
                center=True)

        # round dots on the right
        if self.rounds > 1:
            x = ui.WIDTH - 60 - (self.rounds - 1) * 26
            ui.text(surf, "ROUND", (ui.WIDTH - 60, 18), ui.MUTED, "xs",
                    right=True)
            for i in range(self.rounds):
                c = ui.WHITE if i < self.round else ui.DIM
                rad = 8 if i == self.round - 1 else 6
                pygame.draw.circle(surf, c, (x + i * 26, 52), rad,
                                   0 if i < self.round else 2)

    def draw(self, surf):
        if self.phase == "photo_finish":
            self.draw_photo_finish(surf)
            return
        ui.draw_background(surf)
        self.draw_header(surf)
        self.draw_board(surf, "human")
        self.draw_board(surf, "ai")
        self.fx.draw(surf)

        if self.phase == "countdown":
            self.draw_countdown(surf)
            ui.hint_bar(surf, [("ARROWS", "hold to fly"),
                               ("SPACE", "hover"), ("", "first to land wins")],
                        y=ui.HEIGHT - 46)
        elif self.phase in ("racing", "ending"):
            if self.timer < 600:
                k = self.timer / 600
                ui.big_text(surf, "GO!", (ui.WIDTH // 2, 360), ui.GOAL,
                            1 + k * 0.6, 255 * (1 - k))
            left = max(0, ROUND_TIME - self.timer) / 1000
            ui.text(surf, f"{left:4.1f}", (ui.WIDTH // 2, ui.HEIGHT - 34),
                    ui.WHITE if left > 5 else ui.OBSTACLE, "title",
                    center=True)
        elif self.phase == "round_over":
            self.draw_round_over(surf)
        elif self.phase == "match_over":
            self.draw_match_over(surf)

    def draw_photo_finish(self, surf):
        if self.photo_still is not None:
            surf.blit(self.photo_still, (0, 0))
            return
        ui.draw_background(surf)
        cx = ui.WIDTH // 2
        frozen = self.photo_elapsed >= self.replay_duration
        elapsed = min(self.photo_elapsed, self.replay_duration)
        zoom = elapsed / self.replay_duration
        ui.text(surf, "PHOTO FINISH", (cx, 50), ui.WHITE, "xl", center=True)
        ui.text(surf, "SAME TICK · DRAW" if frozen else "SLOW MOTION",
                (cx, 103), ui.GOLD, "md", center=True)

        for who in ("human", "ai"):
            rect = pygame.Rect(59 if who == "human" else 564, 141, 477, 458)
            env = self.envs[who]
            position, descent = replay_frame(self.replay_moves[who], self.tick_ms, elapsed)
            distance = max(abs(a - b) for a, b in zip(env.goal, position))
            cell = round(min(70 + 32 * zoom, (rect.height - 112) / (distance + 1)))
            row, col = ((a + b) / 2 for a, b in zip(env.goal, position))
            origin = (round(rect.centerx - col * cell - (cell - 3) / 2),
                      round(rect.centery - row * cell - (cell - 3) / 2 + 16))
            clip = surf.get_clip()
            surf.set_clip(rect.inflate(-2, -2).clip(clip))
            surf.fill(ui.BG, rect)
            ui.draw_grid(surf, env, origin, cell)
            draw_pad(surf, origin, cell, env.goal, position, COLOR[who], elapsed,
                     touchdown=0 if frozen else None)
            draw_landing_drone(surf, origin, cell, position, self.airframes[who], descent)
            surf.set_clip(clip)

            pygame.draw.rect(surf, ui.PANEL, (rect.x, rect.y, rect.width, 53))
            pygame.draw.rect(surf, COLOR[who], rect, 2)
            ui.text(surf, NAME[who], (rect.x + 19, rect.y + 12), COLOR[who], "lg")
            if frozen:
                arrival = self.results[who]["time"] / 1000
                ui.text(surf, f"{arrival:.2f}s", (rect.right - 19, rect.y + 15),
                        ui.WHITE, "num", right=True)

        progress = pygame.Rect(59, 621, 982, 4)
        pygame.draw.rect(surf, ui.PANEL_LIGHT, progress, border_radius=2)
        progress.width = round(progress.width * zoom)
        pygame.draw.rect(surf, ui.GOLD, progress, border_radius=2)
        ui.hint_bar(surf, [("ENTER", "result" if frozen else "skip replay")], y=665)
        if frozen:
            self.photo_still = surf.copy()

    def draw_countdown(self, surf):
        n = 3 - self.timer // 1000
        k = (self.timer % 1000) / 1000
        scale = 1.6 - 0.6 * min(1.0, k * 4)
        ui.big_text(surf, n, (ui.WIDTH // 2, 360), ui.WHITE, scale,
                    255 * (1 - k * 0.6))

    def time_behind(self, who):
        """Minimum ms a drone that did not finish still needed to land."""
        c, env = self.ctrl[who], self.envs[who]
        current = (1 - c.t) * c.move_ms
        return current + max(0, env.get_distance()) * c.move_ms

    def draw_round_over(self, surf):
        rect = pygame.Rect(60, 646, ui.WIDTH - 120, 60)
        ui.glass(surf, rect, alpha=220)
        r = self.results
        if self.winner:
            other = "ai" if self.winner == "human" else "human"
            other_event = r[other]["event"]
            if other_event == "dnf":
                gap = self.time_behind(other) / 1000
                why = f"{gap:.2f}s ahead"
                if gap < 0.3:
                    why = "close finish" if self.cinematic_finish else f"photo finish, {why}"
            else:
                why = f"{NAME[other]} {EVENT_TEXT[other_event].lower()}"
            head = f"{NAME[self.winner]} TAKES THE ROUND"
        else:
            head, why = "DEAD HEAT", "nobody landed first"
            if self.cinematic_finish and self.simultaneous_landing():
                why = "both landed on the same tick"
        color = (ui.PLAYER if self.winner == "human" else
                 ui.DRONE if self.winner == "ai" else ui.WHITE)
        ui.text(surf, head, (rect.x + 22, rect.y + 8), color, "lg")
        ui.text(surf, f"{why}  ·  best possible {self.opt_ticks} ticks "
                      "(white dots)", (rect.x + 22, rect.y + 36), ui.MUTED,
                "xs")
        nxt = "next round" if self.round < self.rounds else "result"
        ui.key_cap(surf, "ENTER", (rect.right - 170, rect.y + 18))
        ui.text(surf, nxt, (rect.right - 96, rect.y + 20), ui.WHITE, "sm")

    def draw_match_over(self, surf):
        overlay = pygame.Surface((ui.WIDTH, ui.HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 8, 20, 200))
        surf.blit(overlay, (0, 0))
        box = pygame.Rect(ui.WIDTH // 2 - 290, 170, 580, 360)
        ui.glass(surf, box, alpha=240)
        w = self.match_winner()
        title, color = ((f"YOU BEAT {AI_NAME}!", ui.PLAYER) if w == "human"
                        else (f"{AI_NAME} WINS", ui.DRONE) if w == "ai" else
                        ("DEAD HEAT", ui.WHITE))
        cx = box.centerx
        ui.text(surf, title, (cx, 230), color, "xl", center=True)
        if self.rounds > 1:
            ui.text(surf, f"{self.wins['human']}  :  {self.wins['ai']}",
                    (cx, 300), ui.WHITE, "title", center=True)
            ui.text(surf, f"route stars  {self.star_total['human']} vs "
                          f"{self.star_total['ai']}  (tie-break)",
                    (cx, 345), ui.MUTED, "sm", center=True)
        if w == "human":
            hint = ("Mission cleared!" if self.on_exit else
                    "Ready for the next level?" if self.level < 2 else
                    "Try THE STORM with fog on.")
        else:
            hint = "Tip: press the next direction before the turn."
        ui.text(surf, hint, (cx, 395), ui.GOLD, "md", center=True)
        items = ([("ENTER", "continue")] if self.on_exit else
                 [("ENTER", "rematch"), ("ESC", "change setup")])
        ui.hint_bar(surf, items, y=460)

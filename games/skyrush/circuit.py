"""An endless run of generated courses, with a Legend race every five stages."""

import secrets

import pygame

from games.skyrush import common as ui
from games.skyrush.circuit_maps import STAGE_NAMES, generate_course
from games.skyrush.missions import BOSS_LEVEL, MISSIONS, FlightScene, MissionMapScene
from games.skyrush.race import RaceScene
from games.skyrush.save import load_leaderboard, save_leaderboard
from src.shared.world import ARENAS


def start_circuit(app):
    CircuitRun().launch(app)


def return_to_missions(app, notice=None):
    scene = MissionMapScene(app, selected=len(MISSIONS) - 1)
    scene.circuit_notice = notice
    app.change(scene)


class CircuitRun:
    def __init__(self):
        self.seed = secrets.randbits(64)
        self.cleared = 0
        self.previous_map = None
        self.best = load_leaderboard().get("circuit_best", 0)

    def launch(self, app):
        stage = self.cleared + 1
        if not app.agent.available:
            return_to_missions(app, "ORCA model needed")
            return
        try:
            kind, zone, env = generate_course(self.seed, stage, app.agent, self.previous_map)
        except ValueError:
            return_to_missions(app, "Could not build the next stage. Start a new run.")
            return
        if kind == "boss":
            app.change(CircuitRace(app, self, stage, zone, env))
        else:
            app.change(CircuitFlight(app, self, stage, zone, env, kind))

    def clear_stage(self, stage, env):
        if stage != self.cleared + 1:
            return
        self.cleared = stage
        self.previous_map = env.map_spec()
        if stage > self.best:
            board = load_leaderboard()
            board["circuit_best"] = stage
            save_leaderboard(board)
            self.best = stage


def result_controls(won, practice):
    if won:
        return [("ENTER", "new run" if practice else "next map"), ("ESC", "missions")]
    return [("R", "practice same map"), ("N", "new run"), ("ESC", "missions")]


class CircuitFlight(FlightScene):
    require_wind = True

    def __init__(self, app, run, stage, zone, base, kind, practice=False):
        self.run, self.stage, self.zone, self.kind = run, stage, zone, kind
        self.practice = practice
        super().__init__(app, base)

    def finish(self, event):
        previous = self.event
        super().finish(event)
        if not previous and event == "goal" and not self.practice:
            self.run.clear_stage(self.stage, self.base)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        key = event.key
        if key == pygame.K_ESCAPE:
            return_to_missions(self.app)
        elif not self.event:
            self.flight_key(key)
        elif self.event == "goal":
            if key == pygame.K_RETURN:
                if self.practice:
                    start_circuit(self.app)
                else:
                    self.run.launch(self.app)
        elif key == pygame.K_r:
            self.app.change(CircuitFlight(self.app, self.run, self.stage, self.zone,
                                          self.base, self.kind, practice=True))
        elif key == pygame.K_n:
            start_circuit(self.app)

    def draw(self, surf):
        ui.draw_background(surf)
        accent = ARENAS[self.zone]["color"]
        title = "PRACTICE" if self.practice else f"STAGE {self.stage}"
        ui.text(surf, title, (60, 29), accent, "title")
        ui.text(surf, f"Endless Circuit · {STAGE_NAMES[self.kind]}", (62, 76), ui.MUTED, "sm")
        self.draw_flight(surf)
        panel = pygame.Rect(645, 118, 400, 260)
        ui.glass(surf, panel, alpha=225, border=accent)
        ui.text(surf, "CURRENT RUN", (671, 145), accent, "sm")
        ui.text(surf, f"{self.run.cleared} cleared", (670, 174), ui.WHITE, "title")
        ui.text(surf, f"Best run: {self.run.best}", (671, 239), ui.GOLD, "md")
        ui.text(surf, f"Moves: {self.env.steps}", (671, 279), ui.MUTED, "md")
        if not self.started:
            ui.text(surf, "Press an arrow key to take off.", (671, 329), ui.WHITE, "sm")
        tip = {"wind": "Ride the wind to reach the other side.",
               "patrol": "Cross the lanes. Pink marks the next move.",
               "mixed": "Use the wind and time your patrol crossing."}
        ui.text(surf, tip[self.kind], (661, 417), ui.MUTED, "md")
        self.draw_equipment(surf)
        if not self.event:
            ui.hint_bar(surf, [("ARROWS", "fly"), ("SPACE", "hover"), ("ESC", "missions")])
        elif self.end_timer >= 320:
            self.draw_result(surf)

    def draw_result(self, surf):
        box = pygame.Rect(258, 262, 584, 191)
        ui.glass(surf, box, alpha=247, border=ui.GOAL if self.event == "goal" else ui.OBSTACLE)
        won = self.event == "goal"
        if self.practice:
            title = "PRACTICE COMPLETE" if won else "PRACTICE FAILED"
        else:
            title = "STAGE CLEARED" if won else "RUN ENDED"
        ui.text(surf, title, (box.centerx, 303), ui.WHITE, "title", center=True)
        if won:
            caption = f"Landed in {self.env.steps} moves"
        else:
            reason = "Crashed" if self.event == "crash" else "Out of time"
            caption = f"{reason}  ·  {self.run.cleared} stages cleared"
        ui.text(surf, caption, (box.centerx, 355), ui.MUTED, "md", center=True)
        ui.hint_bar(surf, result_controls(won, self.practice), y=400)


class CircuitRace(RaceScene):
    show_optimal_route = False

    def __init__(self, app, run, stage, zone, base, practice=False):
        self.run, self.stage, self.practice = run, stage, practice
        label = "PRACTICE" if practice else f"STAGE {stage}"
        super().__init__(app, zone, BOSS_LEVEL, rounds=1, map_env=base,
                         on_exit=lambda app, *_: return_to_missions(app),
                         title=f"{label} · LEGEND RACE")

    def finish_round(self):
        super().finish_round()
        if self.winner == "human" and not self.practice:
            self.run.clear_stage(self.stage, self.map_env)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN or self.phase != "round_over":
            super().handle_event(event)
            return
        key = event.key
        if key == pygame.K_ESCAPE:
            return_to_missions(self.app)
        elif self.winner == "human":
            if key == pygame.K_RETURN:
                if self.practice:
                    start_circuit(self.app)
                else:
                    self.run.launch(self.app)
        elif key == pygame.K_r:
            self.app.change(CircuitRace(self.app, self.run, self.stage, self.arena,
                                        self.map_env, practice=True))
        elif key == pygame.K_n:
            start_circuit(self.app)

    def draw_header(self, surf):
        super().draw_header(surf)
        ui.text(surf, f"{self.run.cleared} cleared  ·  Best {self.run.best}",
                (1036, 37), ui.GOLD, "md", right=True)

    def draw_round_over(self, surf):
        box = pygame.Rect(60, 644, 980, 61)
        ui.glass(surf, box, alpha=240)
        won = self.winner == "human"
        title = "YOU BEAT LEGEND" if won else "RUN ENDED"
        ui.text(surf, title, (80, 663), ui.GOAL if won else ui.OBSTACLE, "lg")
        x = 551 if won and not self.practice else 472
        for key, label in result_controls(won, self.practice):
            cap = ui.key_cap(surf, key, (x, 663))
            text = ui.text(surf, label, (cap.right + 8, 665), ui.WHITE, "sm")
            x = text.right + 20

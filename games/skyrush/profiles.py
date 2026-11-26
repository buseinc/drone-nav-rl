"""Choose, create, or delete a local player profile."""

import pygame

from games.skyrush import common as ui
from games.skyrush.save import (MAX_NAME_LENGTH, active_profile_name,
                                can_import_legacy_progress, create_profile,
                                delete_profile, profile_names, select_profile)
from src.shared.scene import Scene

PLAYER_PANEL = pygame.Rect(129, 186, 394, 418)
ACTION_PANEL = pygame.Rect(547, 186, 424, 418)
NAME_BOX = pygame.Rect(575, 284, 368, 55)
PRIMARY = pygame.Rect(575, 453, 368, 49)
NEW_PLAYER = pygame.Rect(575, 522, 174, 47)
DELETE_PLAYER = pygame.Rect(763, 522, 180, 47)
CONFIRM_BOX = pygame.Rect(292, 219, 516, 263)
CANCEL_DELETE = pygame.Rect(320, 406, 212, 46)
CONFIRM_DELETE = pygame.Rect(550, 406, 230, 46)
ROWS = 5


def display_name(name, width, font):
    if ui.render(name, font, ui.WHITE).get_width() <= width:
        return name
    while ui.render(name + "…", font, ui.WHITE).get_width() > width:
        name = name[:-1]
    return name + "…"


class ProfileScene(Scene):
    def __init__(self, app, from_menu=False):
        super().__init__(app)
        self.from_menu = from_menu
        self.typing_name = False
        self.name = ""
        self.error = ""
        self.delete_target = None
        try:
            self.names = profile_names()
        except (OSError, ValueError):
            self.names = []
            self.error = "The player save could not be read."
        current = active_profile_name()
        self.selected = self.names.index(current) if current in self.names else 0
        if not self.names and not self.error:
            self.begin_create()

    def begin_create(self):
        self.typing_name = True
        self.name = ""
        self.error = ""
        pygame.key.start_text_input()
        pygame.key.set_text_input_rect(NAME_BOX)

    def stop_typing(self):
        if self.typing_name:
            pygame.key.stop_text_input()
            self.typing_name = False

    def cancel(self):
        if self.typing_name and self.names:
            self.stop_typing()
            self.error = ""
        elif self.from_menu and active_profile_name() is not None:
            self.enter_menu()
        else:
            from games.skyrush.title import TitleScene
            self.stop_typing()
            self.app.change(TitleScene(self.app))

    def enter_menu(self):
        from games.skyrush.menu import MenuScene
        self.stop_typing()
        self.app.change(MenuScene(self.app))

    def submit(self):
        try:
            if self.typing_name:
                create_profile(self.name)
            elif self.names:
                select_profile(self.names[self.selected])
            else:
                return
        except ValueError as error:
            self.error = str(error)
            return
        except (OSError, KeyError):
            self.error = "Could not open the player save."
            return
        self.app.sound.play("go")
        self.enter_menu()

    def ask_to_delete(self):
        self.error = ""
        self.delete_target = self.names[self.selected]
        self.app.sound.play("click")

    def confirm_delete(self):
        target = self.delete_target
        self.delete_target = None
        try:
            delete_profile(target)
        except (OSError, KeyError, ValueError):
            self.error = "Could not delete this player."
            return
        self.names.remove(target)
        self.selected = min(self.selected, max(0, len(self.names) - 1))
        self.app.sound.play("click")
        if not self.names:
            self.begin_create()

    def handle_delete_dialog(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_y:
                self.confirm_delete()
            elif event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                self.delete_target = None
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if CONFIRM_DELETE.collidepoint(event.pos):
                self.confirm_delete()
            elif CANCEL_DELETE.collidepoint(event.pos):
                self.delete_target = None

    def visible_players(self):
        start = min(max(0, self.selected - ROWS + 1), max(0, len(self.names) - ROWS))
        for offset, name in enumerate(self.names[start:start + ROWS]):
            yield start + offset, name, pygame.Rect(154, 254 + offset * 59, 344, 49)

    def handle_event(self, event):
        if self.delete_target is not None:
            self.handle_delete_dialog(event)
        elif self.typing_name and event.type == pygame.TEXTINPUT:
            self.name = (self.name + event.text)[:MAX_NAME_LENGTH]
            self.error = ""
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if PRIMARY.collidepoint(event.pos):
                self.submit()
            elif NEW_PLAYER.collidepoint(event.pos) and self.names and not self.typing_name:
                self.begin_create()
            elif DELETE_PLAYER.collidepoint(event.pos) and self.names and not self.typing_name:
                self.ask_to_delete()
            else:
                for index, _, rect in self.visible_players():
                    if rect.collidepoint(event.pos):
                        self.stop_typing()
                        self.error = ""
                        self.selected = index
                        self.app.sound.play("click")
                        break
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.cancel()
            elif event.key == pygame.K_RETURN:
                self.submit()
            elif self.typing_name:
                if event.key == pygame.K_BACKSPACE:
                    self.name = self.name[:-1]
                    self.error = ""
            elif event.key == pygame.K_n and self.names:
                self.begin_create()
            elif event.key == pygame.K_DELETE and self.names:
                self.ask_to_delete()
            elif self.names and event.key in (pygame.K_UP, pygame.K_DOWN):
                direction = -1 if event.key == pygame.K_UP else 1
                self.selected = (self.selected + direction) % len(self.names)
                self.app.sound.play("click")

    def draw(self, surface):
        self.app.sky.draw(surface, skyline=False)
        ui.text(surface, "PLAYER PROFILES", (129, 47), ui.WHITE, "xl")
        ui.text(surface, "Choose your player or start a new game.", (132, 122), ui.MUTED, "md")
        ui.glass(surface, PLAYER_PANEL, (24, 34, 58), alpha=232, border=(60, 78, 110))
        ui.glass(surface, ACTION_PANEL, (24, 34, 58), alpha=232, border=(60, 100, 110))
        ui.text(surface, "Saved players", (154, 208), ui.MUTED, "md")
        if self.names:
            for index, name, rect in self.visible_players():
                selected = index == self.selected and not self.typing_name
                ui.glass(surface, rect, alpha=220 if selected else 120,
                         border=ui.GOAL if selected else (49, 67, 94), radius=9)
                label = display_name(name, rect.width - 30, "md")
                ui.text(surface, label, (rect.x + 15, rect.y + 14), ui.WHITE, "md")
            if len(self.names) > ROWS:
                ui.text(surface, f"{self.selected + 1} / {len(self.names)}", (493, 565),
                        ui.MUTED, "sm", right=True)
        else:
            ui.text(surface, "No saved players yet.", (154, 260), ui.MUTED, "sm")

        if self.typing_name:
            self.draw_name_form(surface)
            primary = "Create player"
            controls = [("ENTER", "create player"), ("ESC", "back")]
        elif self.names:
            ui.text(surface, "Continue as", (575, 215), ui.MUTED, "md")
            label = display_name(self.names[self.selected], PRIMARY.width, "lg")
            ui.text(surface, label, (575, 249), ui.WHITE, "lg")
            ui.text(surface, "Your missions and records will be loaded.", (575, 304), ui.MUTED, "sm")
            ui.glass(surface, NEW_PLAYER, alpha=125, border=(76, 96, 133), radius=9)
            ui.text(surface, "New player", NEW_PLAYER.center, ui.WHITE, "md", center=True)
            ui.glass(surface, DELETE_PLAYER, (62, 32, 48), alpha=150,
                     border=(148, 71, 87), radius=9)
            ui.text(surface, "Delete player", DELETE_PLAYER.center, ui.OBSTACLE, "md", center=True)
            primary = "Continue"
            controls = [("UP/DOWN", "choose"), ("ENTER", "play"), ("N", "new player"),
                        ("DEL", "delete"), ("ESC", "back")]
        else:
            primary = None
            controls = [("ESC", "back")]
        if self.error:
            ui.text(surface, self.error, (575, 398), ui.OBSTACLE, "sm")
        if primary:
            pygame.draw.rect(surface, ui.GOAL, PRIMARY, border_radius=9)
            ui.text(surface, primary, PRIMARY.center, ui.SKY_TOP, "lg", center=True)
        if self.delete_target is None:
            ui.hint_bar(surface, controls, y=665)
        else:
            self.draw_delete_dialog(surface)

    def draw_delete_dialog(self, surface):
        dim = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim.fill((8, 12, 24, 185))
        surface.blit(dim, (0, 0))
        ui.glass(surface, CONFIRM_BOX, (27, 34, 57), alpha=255, border=ui.OBSTACLE)
        x = CONFIRM_BOX.centerx
        ui.text(surface, "Delete this player?", (x, 260), ui.WHITE, "title", center=True)
        name = display_name(self.delete_target, CONFIRM_BOX.width - 56, "lg")
        ui.text(surface, name, (x, 308), ui.OBSTACLE, "lg", center=True)
        ui.text(surface, "This removes their stars, duel records, and unlocked adventures.",
                (x, 351), ui.MUTED, "sm", center=True)
        ui.text(surface, "This cannot be undone.", (x, 376), ui.MUTED, "xs", center=True)
        ui.glass(surface, CANCEL_DELETE, border=(91, 112, 151), radius=9)
        ui.text(surface, "Cancel", CANCEL_DELETE.center, ui.WHITE, "md", center=True)
        pygame.draw.rect(surface, ui.OBSTACLE, CONFIRM_DELETE, border_radius=9)
        ui.text(surface, "Delete player", CONFIRM_DELETE.center, ui.SKY_TOP, "md", center=True)
        ui.hint_bar(surface, [("ESC", "cancel"), ("Y", "delete player")], y=665)

    def draw_name_form(self, surface):
        ui.text(surface, "New player", (575, 213), ui.WHITE, "title")
        ui.text(surface, "Player name", (575, 262), ui.MUTED, "xs")
        ui.glass(surface, NAME_BOX, (16, 24, 43), alpha=245, border=ui.GOAL, radius=9)
        label = display_name(self.name, NAME_BOX.width - 35, "md") if self.name else "Enter your name"
        name = ui.text(surface, label, (590, 301),
                       ui.WHITE if self.name else ui.DIM, "md")
        if pygame.time.get_ticks() // 450 % 2 == 0 and (self.name or not self.error):
            x = name.right + 3 if self.name else name.left
            pygame.draw.line(surface, ui.GOAL, (x, name.top), (x, name.bottom), 2)
        if not self.names and can_import_legacy_progress():
            ui.text(surface, "This player will keep the progress on this PC.", (575, 356), ui.GOLD, "sm")
        else:
            ui.text(surface, "This player starts with a fresh game.", (575, 356), ui.MUTED, "sm")

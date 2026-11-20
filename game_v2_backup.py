
import os
import pygame
import torch

from src.drone_env_v2 import DroneEnvV2
from src.dqn_model import DQN

pygame.init()

WIDTH, HEIGHT = 900, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("DroneNav AI")

clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas", 23)
small_font = pygame.font.SysFont("consolas", 17)
title_font = pygame.font.SysFont("consolas", 34, bold=True)

BG = (13, 19, 33)
PANEL = (25, 35, 55)
EMPTY = (35, 47, 67)
OBSTACLE = (224, 91, 94)
DRONE = (65, 190, 255)
GOAL = (81, 220, 150)
WHITE = (240, 244, 250)
MUTED = (155, 170, 190)

CELL = 54
OFFSET_X = 35
OFFSET_Y = 95

env = DroneEnvV2()
model = None
mode = "PLAYER"
finished = False
message = "Reach the green target!"
autoplay = False
last_ai_step = 0

actions = {
    pygame.K_UP: 0,
    pygame.K_DOWN: 1,
    pygame.K_LEFT: 2,
    pygame.K_RIGHT: 3,
}

def draw_text(text, x, y, color=WHITE, use_font=None):
    surface = (use_font or font).render(text, True, color)
    screen.blit(surface, (x, y))

def restart(new_map=True):
    global finished, message, autoplay

    if new_map:
        env.reset()
    else:
        env.position = env.start
        env.steps = 0

    finished = False
    autoplay = False
    message = "Reach the green target!"

def load_ai():
    global model

    path = "models/dqn_model.pth"

    if not os.path.exists(path):
        return False

    model = DQN(len(env.get_state()), 4)
    model.load_state_dict(
        torch.load(
            path,
            map_location="cpu",
            weights_only=True
        )
    )
    model.eval()
    return True

def move(action):
    global finished, message, autoplay

    if finished:
        return

    _, reward, done = env.step(action)

    if done:
        finished = True
        autoplay = False

        if env.position == env.goal:
            message = "MISSION COMPLETE!"
        elif reward == -100:
            message = "CRASH! Mission failed."
        else:
            message = "TIME LIMIT REACHED."

def ai_step():
    if model is None or finished:
        return

    state = torch.tensor(
        env.get_state(),
        dtype=torch.float32
    ).unsqueeze(0)

    with torch.no_grad():
        q_values = model(state)

    action = int(torch.argmax(q_values, dim=1).item())
    move(action)

def draw_game():
    screen.fill(BG)

    draw_text("DRONENAV AI", 35, 25, DRONE, title_font)
    draw_text("Can you beat the agent?", 310, 34, MUTED, small_font)

    # Grid
    for row in range(env.grid_size):
        for col in range(env.grid_size):
            rect = pygame.Rect(
                OFFSET_X + col * CELL,
                OFFSET_Y + row * CELL,
                CELL - 3,
                CELL - 3
            )

            color = EMPTY

            if (row, col) in env.obstacles:
                color = OBSTACLE

            if (row, col) == env.goal:
                color = GOAL

            pygame.draw.rect(
                screen, color, rect, border_radius=6
            )

    # Drone
    row, col = env.position
    center = (
        OFFSET_X + col * CELL + CELL // 2,
        OFFSET_Y + row * CELL + CELL // 2
    )

    pygame.draw.circle(screen, DRONE, center, 17)
    pygame.draw.circle(screen, WHITE, center, 7)

    # Side panel
    pygame.draw.rect(
        screen, PANEL,
        (600, 95, 275, 540),
        border_radius=14
    )

    draw_text("MISSION CONTROL", 620, 120, DRONE)
    draw_text(f"MODE: {mode}", 620, 170)
    draw_text(f"STEPS: {env.steps}", 620, 210)
    draw_text(f"MAX: {env.max_steps}", 620, 250)

    draw_text("CONTROLS", 620, 325, GOAL)
    draw_text("Arrows : Move", 620, 365, use_font=small_font)
    draw_text("A      : AI Mode", 620, 395, use_font=small_font)
    draw_text("P      : Play Mode", 620, 425, use_font=small_font)
    draw_text("SPACE  : AI Step", 620, 455, use_font=small_font)
    draw_text("R      : Restart", 620, 485, use_font=small_font)
    draw_text("N      : New Map", 620, 515, use_font=small_font)

    draw_text("Green = Goal", 620, 570, GOAL, small_font)
    draw_text("Red = Obstacle", 620, 595, OBSTACLE, small_font)

    draw_text(message, 35, 655, WHITE, small_font)

    pygame.display.flip()

running = True

while running:
    clock.tick(30)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

            elif event.key == pygame.K_n:
                restart(new_map=True)

            elif event.key == pygame.K_r:
                restart(new_map=False)

            elif event.key == pygame.K_p:
                mode = "PLAYER"
                restart(new_map=False)

            elif event.key == pygame.K_a:
                if load_ai():
                    mode = "AI"
                    restart(new_map=False)
                    autoplay = True
                    last_ai_step = pygame.time.get_ticks()
                else:
                    message = "Train DQN first!"

            elif event.key == pygame.K_SPACE and mode == "AI":
                autoplay = False
                ai_step()

            elif mode == "PLAYER" and event.key in actions:
                move(actions[event.key])

    if mode == "AI" and autoplay and not finished:
        now = pygame.time.get_ticks()

        if now - last_ai_step >= 250:
            ai_step()
            last_ai_step = now

    draw_game()

pygame.quit()

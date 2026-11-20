"""Train one Double DQN that handles clean maps, wind and patrols.

Run from the project root:  python -m src.train_dqn_v4

Same recipe as V3 (Double DQN, soft target updates, curriculum), plus:
  * 5 actions (hover added), bigger network (256 hidden units),
  * every episode samples a hazard setting, so one model can play all
    game modes,
  * validation reports each hazard setting separately.
"""

import os
import random
from collections import deque

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim

from src.dqn_model import DQN
from src.drone_env_v4 import DroneEnvV4, N_ACTIONS
from src.evaluate_v4 import evaluate_all

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

EPISODES = 12000
BATCH_SIZE = 128
GAMMA = 0.97
LEARNING_RATE = 5e-4
HIDDEN = 256
EPSILON_START, EPSILON_MIN = 1.0, 0.05
EPSILON_DECAY_EPISODES = 2000
BUFFER_SIZE = 100_000
TARGET_TAU = 0.005
EVAL_EVERY = 500
CHECKPOINTS = {200, 1000, 2500, 5000, 8000}

# Curriculum: (until_episode, obstacles, max_start_goal_dist,
#              [(wind_streams, enemy_count), ...] sampled uniformly)
# First learn plain navigation (like V3), then add hazards step by step.
CURRICULUM = [
    (500, 6, 6, [(0, 0)]),
    (1500, 10, 10, [(0, 0), (1, 0), (0, 1)]),
    (3000, 15, None, [(0, 0), (1, 0), (0, 1), (1, 1)]),
    (EPISODES, 15, None, [(0, 0), (2, 0), (0, 2), (2, 2), (1, 1)]),
]

os.makedirs("models/checkpoints", exist_ok=True)

env = DroneEnvV4(seed=SEED)
state_size = env.state_size

policy_net = DQN(state_size, N_ACTIONS, HIDDEN)
target_net = DQN(state_size, N_ACTIONS, HIDDEN)
target_net.load_state_dict(policy_net.state_dict())
optimizer = optim.Adam(policy_net.parameters(), lr=LEARNING_RATE)
loss_fn = nn.SmoothL1Loss()
memory = deque(maxlen=BUFFER_SIZE)


def select_action(state, epsilon):
    if random.random() < epsilon:
        return random.randrange(N_ACTIONS)
    with torch.no_grad():
        q = policy_net(torch.tensor(state).unsqueeze(0))
    return int(q.argmax(dim=1).item())


def train_step():
    if len(memory) < 2000:
        return None
    batch = random.sample(memory, BATCH_SIZE)
    s, a, r, s2, d = map(np.array, zip(*batch))
    s = torch.tensor(s, dtype=torch.float32)
    a = torch.tensor(a, dtype=torch.long).unsqueeze(1)
    r = torch.tensor(r, dtype=torch.float32)
    s2 = torch.tensor(s2, dtype=torch.float32)
    d = torch.tensor(d, dtype=torch.float32)

    q = policy_net(s).gather(1, a).squeeze(1)
    with torch.no_grad():
        best = policy_net(s2).argmax(dim=1, keepdim=True)
        q_next = target_net(s2).gather(1, best).squeeze(1)
        target = r + GAMMA * q_next * (1 - d)

    loss = loss_fn(q, target)
    optimizer.zero_grad()
    loss.backward()
    nn.utils.clip_grad_norm_(policy_net.parameters(), 10.0)
    optimizer.step()
    with torch.no_grad():
        for p, tp in zip(policy_net.parameters(), target_net.parameters()):
            tp.mul_(1 - TARGET_TAU).add_(TARGET_TAU * p)
    return float(loss.item())


def stage(episode):
    for until, obstacles, max_dist, hazards in CURRICULUM:
        if episode <= until:
            return obstacles, max_dist, hazards
    return CURRICULUM[-1][1:]


results, best_score = [], -1.0

for episode in range(1, EPISODES + 1):
    obstacles, max_dist, hazards = stage(episode)
    env.obstacle_count, env.max_start_goal_dist = obstacles, max_dist
    env.wind_streams, env.enemy_count = random.choice(hazards)
    epsilon = max(EPSILON_MIN, EPSILON_START - (EPSILON_START - EPSILON_MIN)
                  * episode / EPSILON_DECAY_EPISODES)

    state = env.reset()
    done, total_reward, losses = False, 0.0, []
    while not done:
        action = select_action(state, epsilon)
        next_state, reward, done, info = env.step(action)
        terminal = done and info["event"] != "timeout"
        memory.append((state, action, reward, next_state, float(terminal)))
        loss = train_step()
        if loss is not None:
            losses.append(loss)
        state = next_state
        total_reward += reward

    results.append({
        "episode": episode, "reward": total_reward,
        "success": int(info["event"] == "goal"), "event": info["event"],
        "steps": env.steps, "obstacles": obstacles,
        "wind": env.wind_streams, "enemies": env.enemy_count,
        "epsilon": epsilon, "loss": np.mean(losses) if losses else np.nan,
    })

    if episode in CHECKPOINTS:
        torch.save(policy_net.state_dict(),
                   f"models/checkpoints/dqn_v4_ep{episode}.pth")

    if episode % EVAL_EVERY == 0:
        val = evaluate_all(policy_net, episodes=100, seed=7)
        policy_net.train()
        score = np.mean([v["success"] for v in val.values()])
        recent = np.mean([x["success"] for x in results[-EVAL_EVERY:]])
        tag = ""
        if score > best_score:
            best_score = score
            torch.save(policy_net.state_dict(), "models/dqn_v4.pth")
            tag = "  <- best, saved"
        parts = "  ".join(f"{k} {100 * v['success']:3.0f}%"
                          f"(c{100 * v['crash']:2.0f})"
                          for k, v in val.items())
        print(f"Ep {episode:5d} | eps {epsilon:.2f} | train "
              f"{100 * recent:5.1f}% | val avg {100 * score:5.1f}% | "
              f"{parts}{tag}", flush=True)

torch.save(policy_net.state_dict(), "models/checkpoints/dqn_v4_final.pth")
pd.DataFrame(results).to_csv("results/dqn_v4_training.csv", index=False)
print(f"\nDone. Best validation average: {100 * best_score:.1f}%")

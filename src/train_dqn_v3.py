"""Train a Double DQN on DroneEnvV3 with a curriculum.

Run from the project root:  python -m src.train_dqn_v3
"""

import os
import random
from collections import deque

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim

from src.drone_env_v3 import DroneEnvV3
from src.dqn_model import DQN
from src.evaluate_v3 import evaluate

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

EPISODES = 6000
BATCH_SIZE = 128
GAMMA = 0.97
LEARNING_RATE = 5e-4
EPSILON_START, EPSILON_MIN = 1.0, 0.05
EPSILON_DECAY_EPISODES = 1500     # linear decay over this many episodes
BUFFER_SIZE = 50_000
TARGET_TAU = 0.005                 # soft target update
EVAL_EVERY = 250
CHECKPOINTS = {100, 500, 1000, 2000, 4000}   # for a "Watch It Learn" mode

# Curriculum: (until_episode, obstacle_count, max_start_goal_dist)
CURRICULUM = [
    (500, 5, 4),
    (1200, 10, 8),
    (2000, 15, 12),
    (EPISODES, 15, None),
]

os.makedirs("models/checkpoints", exist_ok=True)

env = DroneEnvV3(seed=SEED)
state_size, action_size = env.state_size, 4

policy_net = DQN(state_size, action_size)
target_net = DQN(state_size, action_size)
target_net.load_state_dict(policy_net.state_dict())
optimizer = optim.Adam(policy_net.parameters(), lr=LEARNING_RATE)
loss_fn = nn.SmoothL1Loss()
memory = deque(maxlen=BUFFER_SIZE)


def select_action(state, epsilon):
    if random.random() < epsilon:
        return random.randrange(action_size)
    with torch.no_grad():
        q = policy_net(torch.tensor(state).unsqueeze(0))
    return int(q.argmax(dim=1).item())


def train_step():
    if len(memory) < 1000:
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
        # Double DQN: the policy net picks the action, the target net scores it.
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


def curriculum(episode):
    for until, obstacles, max_dist in CURRICULUM:
        if episode <= until:
            return obstacles, max_dist
    return CURRICULUM[-1][1:]


results, best_success = [], -1.0

for episode in range(1, EPISODES + 1):
    env.obstacle_count, env.max_start_goal_dist = curriculum(episode)
    epsilon = max(EPSILON_MIN, EPSILON_START - (EPSILON_START - EPSILON_MIN)
                  * episode / EPSILON_DECAY_EPISODES)

    state = env.reset()
    done, total_reward, losses = False, 0.0, []

    while not done:
        action = select_action(state, epsilon)
        next_state, reward, done, info = env.step(action)
        # A timeout is not a "real" terminal state: the future still matters.
        terminal = done and info["event"] != "timeout"
        memory.append((state, action, reward, next_state, float(terminal)))
        loss = train_step()
        if loss is not None:
            losses.append(loss)
        state = next_state
        total_reward += reward

    results.append({
        "episode": episode,
        "reward": total_reward,
        "success": int(info["event"] == "goal"),
        "event": info["event"],
        "steps": env.steps,
        "obstacles": env.obstacle_count,
        "epsilon": epsilon,
        "loss": np.mean(losses) if losses else np.nan,
    })

    if episode in CHECKPOINTS:
        torch.save(policy_net.state_dict(),
                   f"models/checkpoints/dqn_v3_ep{episode}.pth")

    if episode % EVAL_EVERY == 0:
        # Validation maps (seed 7) are different from the final test maps
        # (seed 2026), so picking the best model does not cheat the test.
        val = evaluate(policy_net, episodes=200, seed=7)
        policy_net.train()
        results[-1].update({f"val_{k}": v for k, v in val.items()})
        recent = np.mean([x["success"] for x in results[-EVAL_EVERY:]])

        tag = ""
        if val["success"] > best_success:
            best_success = val["success"]
            torch.save(policy_net.state_dict(), "models/dqn_v3.pth")
            tag = "  <- best, saved"

        print(f"Ep {episode:5d} | obstacles {env.obstacle_count:2d} | "
              f"eps {epsilon:.2f} | train {100 * recent:5.1f}% | "
              f"val success {100 * val['success']:5.1f}% "
              f"crash {100 * val['crash']:4.1f}% "
              f"timeout {100 * val['timeout']:4.1f}% "
              f"eff {100 * val['path_efficiency']:5.1f}%{tag}", flush=True)

torch.save(policy_net.state_dict(), "models/checkpoints/dqn_v3_final.pth")
pd.DataFrame(results).to_csv("results/dqn_v3_training.csv", index=False)
print(f"\nDone. Best validation success: {100 * best_success:.1f}%")

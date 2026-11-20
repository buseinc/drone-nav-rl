"""Greedy evaluation of a DQN agent on DroneEnvV4 maps.

Run:  python -m src.evaluate_v4
"""

import numpy as np
import torch

from src.drone_env_v4 import DroneEnvV4, N_ACTIONS

# (name, wind_streams, enemy_count)
CONFIGS = [
    ("clean", 0, 0),
    ("wind", 2, 0),
    ("patrols", 0, 2),
    ("wind+patrols", 2, 2),
]


def run_episode(env, model):
    state = env.get_state()
    done, info = False, {"event": "move"}
    while not done:
        with torch.no_grad():
            q = model(torch.tensor(state).unsqueeze(0))
        state, _, done, info = env.step(int(q.argmax(dim=1).item()))
    return info["event"]


def evaluate(model, episodes=200, seed=2026, obstacle_count=15,
             wind_streams=0, enemy_count=0):
    env = DroneEnvV4(seed=seed, obstacle_count=obstacle_count,
                     wind_streams=wind_streams, enemy_count=enemy_count)
    model.eval()
    counts = {"goal": 0, "crash": 0, "timeout": 0}
    ratios = []
    for _ in range(episodes):
        env.reset()
        event = run_episode(env, model)
        counts[event] += 1
        if event == "goal":
            ratios.append(env.optimal_length() / env.steps)
    return {
        "success": counts["goal"] / episodes,
        "crash": counts["crash"] / episodes,
        "timeout": counts["timeout"] / episodes,
        "path_efficiency": float(np.mean(ratios)) if ratios else 0.0,
    }


def evaluate_all(model, episodes=200, seed=2026):
    return {name: evaluate(model, episodes, seed, wind_streams=w,
                           enemy_count=e)
            for name, w, e in CONFIGS}


if __name__ == "__main__":
    from src.dqn_model import DQN

    env = DroneEnvV4()
    model = DQN(env.state_size, N_ACTIONS, hidden=256)
    model.load_state_dict(torch.load("models/dqn_v4.pth", map_location="cpu",
                                     weights_only=True))
    print("Test maps: 200 per setting (15 obstacles, unseen seed)")
    for name, r in evaluate_all(model).items():
        print(f"{name:13s} success {100 * r['success']:5.1f}%  "
              f"crash {100 * r['crash']:5.1f}%  "
              f"timeout {100 * r['timeout']:5.1f}%  "
              f"efficiency {100 * r['path_efficiency']:5.1f}%")

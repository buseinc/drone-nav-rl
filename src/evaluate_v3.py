"""Greedy evaluation of a DQN agent on DroneEnvV3 maps."""

import numpy as np
import torch

from src.drone_env_v3 import DroneEnvV3


def run_episode(env, model):
    state = env.get_state()
    done, info = False, {"event": "move"}
    while not done:
        with torch.no_grad():
            q = model(torch.tensor(state).unsqueeze(0))
        state, _, done, info = env.step(int(q.argmax(dim=1).item()))
    return info["event"]


def evaluate(model, episodes=200, seed=2026, obstacle_count=15):
    """Success / crash / timeout rates and path quality on unseen maps."""
    env = DroneEnvV3(seed=seed, obstacle_count=obstacle_count)
    model.eval()
    counts = {"goal": 0, "crash": 0, "timeout": 0}
    ratios = []  # optimal_length / agent_length, 1.0 = perfect

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


if __name__ == "__main__":
    from src.dqn_model import DQN

    env = DroneEnvV3()
    model = DQN(env.state_size, 4)
    model.load_state_dict(torch.load("models/dqn_v3.pth",
                                     map_location="cpu", weights_only=True))
    r = evaluate(model)
    print(f"Test maps: 200 (15 obstacles, unseen seed)")
    print(f"Success rate:    {100 * r['success']:.1f}%")
    print(f"Collision rate:  {100 * r['crash']:.1f}%")
    print(f"Timeout rate:    {100 * r['timeout']:.1f}%")
    print(f"Path efficiency: {100 * r['path_efficiency']:.1f}% of optimal")

"""Thin wrapper around the trained DQN, used by every game mode."""

import os

import numpy as np
import torch

from src.dqn_model import DQN
from src.drone_env_v4 import N_ACTIONS, DroneEnvV4

MODEL_PATH = "models/dqn_v4.pth"
HIDDEN = 256


class Agent:
    def __init__(self, path=MODEL_PATH):
        self.path = path
        self.model = None
        if os.path.exists(path):
            state_size = DroneEnvV4(seed=0).state_size
            self.model = DQN(state_size, N_ACTIONS, HIDDEN)
            self.model.load_state_dict(
                torch.load(path, map_location="cpu", weights_only=True))
            self.model.eval()

    @property
    def available(self):
        return self.model is not None

    def q_values(self, state):
        with torch.no_grad():
            q = self.model(torch.tensor(state).unsqueeze(0))
        return q[0].numpy()

    def act(self, state):
        return int(np.argmax(self.q_values(state)))

    def policy_map(self, env):
        """For every free cell: what would the AI do if it were there now?

        Returns {cell: (best_action, max_q, gap)} where gap is the margin
        between the best and second-best Q-value (how decisive the AI is).
        All cells go through the network in one batch, so this is cheap.
        """
        cells = [(r, c) for r in range(env.grid_size)
                 for c in range(env.grid_size)
                 if (r, c) not in env.obstacles and (r, c) != env.goal]
        if not cells:
            return {}
        states = np.stack([env.get_state(position=p) for p in cells])
        with torch.no_grad():
            q = self.model(torch.tensor(states)).numpy()
        top2 = np.sort(q, axis=1)[:, -2:]
        return {p: (int(q[i].argmax()), float(top2[i, 1]),
                    float(top2[i, 1] - top2[i, 0]))
                for i, p in enumerate(cells)}


def softmax(q):
    e = np.exp(q - q.max())
    return e / e.sum()

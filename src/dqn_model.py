
import torch
import torch.nn as nn


class DQN(nn.Module):
    def __init__(self, state_size=104, action_size=4, hidden=128):
        super().__init__()

        self.network = nn.Sequential(
            nn.Linear(state_size, hidden),
            nn.ReLU(),

            nn.Linear(hidden, hidden),
            nn.ReLU(),

            nn.Linear(hidden, action_size)
        )

    def forward(self, state):
        return self.network(state)

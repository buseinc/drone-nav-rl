import torch
import torch.nn as nn


class CNNDQN(nn.Module):
    def __init__(self, state_size=104, action_size=4):
        super().__init__()

        if state_size != 104:
            raise ValueError("CNN-DQN expects a 10x10 map and 104 features.")

        self.conv = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=3, padding=1),
            nn.ReLU(),

            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.ReLU(),

            nn.MaxPool2d(2)
        )

        self.head = nn.Sequential(
            nn.Flatten(),
            nn.Linear(32 * 5 * 5, 128),
            nn.ReLU(),
            nn.Linear(128, action_size)
        )

    def forward(self, state):
        if state.dim() == 1:
            state = state.unsqueeze(0)

        batch_size = state.shape[0]

        # Original state: 100 map cells + 2 drone + 2 goal
        obstacles = state[:, :100].reshape(
            batch_size, 1, 10, 10
        )

        drone_coords = (
            state[:, 100:102] * 9
        ).round().long().clamp(0, 9)

        goal_coords = (
            state[:, 102:104] * 9
        ).round().long().clamp(0, 9)

        drone_map = torch.zeros(
            batch_size, 100,
            device=state.device,
            dtype=state.dtype
        )

        goal_map = torch.zeros_like(drone_map)

        drone_index = (
            drone_coords[:, 0] * 10 + drone_coords[:, 1]
        ).unsqueeze(1)

        goal_index = (
            goal_coords[:, 0] * 10 + goal_coords[:, 1]
        ).unsqueeze(1)

        drone_map.scatter_(1, drone_index, 1.0)
        goal_map.scatter_(1, goal_index, 1.0)

        drone_map = drone_map.reshape(batch_size, 1, 10, 10)
        goal_map = goal_map.reshape(batch_size, 1, 10, 10)

        image = torch.cat(
            [obstacles, drone_map, goal_map],
            dim=1
        )

        features = self.conv(image)
        return self.head(features)

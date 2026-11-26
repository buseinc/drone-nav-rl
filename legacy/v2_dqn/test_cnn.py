import torch

from legacy.v2_dqn.drone_env_v2 import DroneEnvV2
from legacy.v2_dqn.cnn_dqn_model import CNNDQN

env = DroneEnvV2()
state = env.reset()

model = CNNDQN()

with torch.no_grad():
    q_values = model(
        torch.tensor(state, dtype=torch.float32)
    )

print("State size:", len(state))
print("CNN input channels:", 3)
print("Q-values:", q_values)
print("Selected action:", q_values.argmax(dim=1).item())
print(
    "Parameters:",
    sum(p.numel() for p in model.parameters())
)

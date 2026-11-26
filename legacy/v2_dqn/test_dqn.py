
import torch

from legacy.v2_dqn.drone_env_v2 import DroneEnvV2
from src.dqn_model import DQN

env = DroneEnvV2()
state = env.reset()

model = DQN()

state_tensor = torch.tensor(
    state, dtype=torch.float32
)

with torch.no_grad():
    q_values = model(state_tensor)

print("State size:", len(state))
print("Q-values:", q_values)
print("Selected action:", torch.argmax(q_values).item())

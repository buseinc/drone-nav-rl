import torch

from legacy.v2_dqn.drone_env_v2 import DroneEnvV2
from src.dqn_model import DQN

env = DroneEnvV2(seed=2026)

model = DQN(state_size=104, action_size=4)
model.load_state_dict(
    torch.load(
        "legacy/models/dqn_model.pth",
        map_location="cpu",
        weights_only=True
    )
)
model.eval()

episodes = 200
successes = 0
collisions = 0
timeouts = 0
successful_steps = []

for _ in range(episodes):
    state = env.reset()
    done = False

    while not done:
        state_tensor = torch.tensor(
            state, dtype=torch.float32
        ).unsqueeze(0)

        with torch.no_grad():
            action = int(model(state_tensor).argmax(dim=1).item())

        state, reward, done = env.step(action)

    if env.position == env.goal:
        successes += 1
        successful_steps.append(env.steps)
    elif reward == -100:
        collisions += 1
    else:
        timeouts += 1

print(f"Test maps: {episodes}")
print(f"Success rate: {100 * successes / episodes:.1f}%")
print(f"Collision rate: {100 * collisions / episodes:.1f}%")
print(f"Timeout rate: {100 * timeouts / episodes:.1f}%")

if successful_steps:
    print(
        "Average successful path length:",
        round(sum(successful_steps) / len(successful_steps), 2)
    )

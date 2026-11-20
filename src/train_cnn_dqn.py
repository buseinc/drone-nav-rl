
import random
from collections import deque

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim

from src.drone_env_v2 import DroneEnvV2
from src.cnn_dqn_model import CNNDQN


# Reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

# Hyperparameters
EPISODES = 3000
BATCH_SIZE = 64
GAMMA = 0.95
LEARNING_RATE = 0.001

EPSILON = 1.0
EPSILON_MIN = 0.05
EPSILON_DECAY = 0.997

BUFFER_SIZE = 20000
TARGET_UPDATE = 250

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

# Environment
env = DroneEnvV2(seed=SEED)
state_size = len(env.get_state())
action_size = 4

# Main network learns Q-values
policy_net = CNNDQN(state_size, action_size).to(device)

# Target network provides more stable targets
target_net = CNNDQN(state_size, action_size).to(device)
target_net.load_state_dict(policy_net.state_dict())
target_net.eval()

optimizer = optim.Adam(
    policy_net.parameters(),
    lr=LEARNING_RATE
)

loss_fn = nn.SmoothL1Loss()

# Experience replay memory
memory = deque(maxlen=BUFFER_SIZE)


def select_action(state, epsilon):
    if random.random() < epsilon:
        return random.randrange(action_size)

    state_tensor = torch.tensor(
        state,
        dtype=torch.float32,
        device=device
    ).unsqueeze(0)

    with torch.no_grad():
        q_values = policy_net(state_tensor)

    return int(q_values.argmax(dim=1).item())


def train_step():
    if len(memory) < BATCH_SIZE:
        return None

    batch = random.sample(memory, BATCH_SIZE)

    states, actions, rewards, next_states, dones = zip(*batch)

    states = torch.tensor(
        np.array(states), dtype=torch.float32, device=device
    )
    actions = torch.tensor(
        actions, dtype=torch.long, device=device
    ).unsqueeze(1)
    rewards = torch.tensor(
        rewards, dtype=torch.float32, device=device
    )
    next_states = torch.tensor(
        np.array(next_states), dtype=torch.float32, device=device
    )
    dones = torch.tensor(
        dones, dtype=torch.float32, device=device
    )

    # Q-values for the actions actually taken
    current_q = policy_net(states).gather(1, actions).squeeze(1)

    # Bellman targets
    with torch.no_grad():
        next_q = target_net(next_states).max(dim=1).values
        target_q = rewards + GAMMA * next_q * (1 - dones)

    loss = loss_fn(current_q, target_q)

    optimizer.zero_grad()
    loss.backward()
    nn.utils.clip_grad_norm_(policy_net.parameters(), 10.0)
    optimizer.step()

    return float(loss.item())


results = []
global_step = 0

print("Training device:", device)
print("State size:", state_size)

for episode in range(1, EPISODES + 1):
    state = env.reset()
    done = False
    total_reward = 0
    losses = []

    while not done:
        old_distance = (
            abs(env.position[0] - env.goal[0])
            + abs(env.position[1] - env.goal[1])
        )

        action = select_action(state, EPSILON)
        next_state, reward, done = env.step(action)

        new_distance = (
            abs(env.position[0] - env.goal[0])
            + abs(env.position[1] - env.goal[1])
        )

        # Reward shaping:
        # Moving closer to the goal earns a small bonus.
        # Moving farther away receives a small penalty.
        shaped_reward = reward + 2.0 * (
            old_distance - new_distance
        )

        memory.append((
            state, action, shaped_reward, next_state, done
        ))

        loss = train_step()

        if loss is not None:
            losses.append(loss)

        state = next_state
        total_reward += reward
        global_step += 1

        if global_step % TARGET_UPDATE == 0:
            target_net.load_state_dict(
                policy_net.state_dict()
            )

    success = int(env.position == env.goal)

    results.append({
        "episode": episode,
        "reward": total_reward,
        "success": success,
        "steps": env.steps,
        "epsilon": EPSILON,
        "loss": np.mean(losses) if losses else np.nan
    })

    EPSILON = max(
        EPSILON_MIN,
        EPSILON * EPSILON_DECAY
    )

    if episode % 100 == 0:
        recent = results[-100:]
        success_rate = np.mean([
            x["success"] for x in recent
        ]) * 100

        print(
            f"Episode {episode} | "
            f"Success Rate: {success_rate:.1f}% | "
            f"Epsilon: {EPSILON:.3f}"
        )


# Save model and results
torch.save(
    policy_net.state_dict(),
    "models/cnn_dqn_model.pth"
)

pd.DataFrame(results).to_csv(
    "results/cnn_dqn_training.csv",
    index=False
)

print("\nDQN training completed!")
print("Model saved: models/cnn_dqn_model.pth")


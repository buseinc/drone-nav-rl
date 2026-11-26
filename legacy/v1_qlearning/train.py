import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from legacy.v1_qlearning.drone_env import DroneEnv


# Create environment
env = DroneEnv()

# Q-table: rows, columns, actions
q_table = np.zeros((env.grid_size, env.grid_size, 4))

# Hyperparameters
alpha = 0.1
gamma = 0.95
epsilon = 1.0
epsilon_min = 0.05
epsilon_decay = 0.995

episodes = 3000

rewards_history = []
success_history = []

np.random.seed(42)

for episode in range(episodes):

    state = env.reset()
    total_reward = 0
    done = False

    while not done:

        # Exploration vs exploitation
        if np.random.random() < epsilon:
            action = np.random.randint(4)
        else:
            action = np.argmax(q_table[state])

        next_state, reward, done = env.step(action)

        # Q-learning update
        old_q = q_table[state][action]

        if done:
            target = reward
        else:
            target = reward + gamma * np.max(q_table[next_state])

        q_table[state][action] = old_q + alpha * (
            target - old_q
        )

        state = next_state
        total_reward += reward

    rewards_history.append(total_reward)

    success_history.append(
        int(state == env.goal)
    )

    # Gradually reduce exploration
    epsilon = max(epsilon_min, epsilon * epsilon_decay)

    if (episode + 1) % 500 == 0:
        recent_success = np.mean(success_history[-500:])

        print(
            f"Episode {episode + 1} | "
            f"Success Rate: {recent_success:.2%} | "
            f"Epsilon: {epsilon:.3f}"
        )


# Save results
os.makedirs("models", exist_ok=True)
os.makedirs("results", exist_ok=True)

np.save("legacy/models/q_table.npy", q_table)

results = pd.DataFrame({
    "episode": np.arange(1, episodes + 1),
    "reward": rewards_history,
    "success": success_history
})

results.to_csv("legacy/results/training_results.csv", index=False)

# Plot learning curve
results["reward_smooth"] = (
    results["reward"].rolling(100).mean()
)

plt.figure(figsize=(10, 5))

plt.plot(
    results["episode"],
    results["reward_smooth"]
)

plt.title("Q-Learning Training Progress")
plt.xlabel("Episode")
plt.ylabel("Average Reward (100 episodes)")
plt.grid(True)

plt.savefig("legacy/results/training_curve.png")
plt.show()

print("Training completed!")
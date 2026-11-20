import numpy as np
import matplotlib.pyplot as plt

from src.drone_env import DroneEnv

# Ortamı ve eğitilmiş Q-table'ı yükle
env = DroneEnv()
q_table = np.load("models/q_table.npy")

state = env.reset()
path = [state]

done = False
total_reward = 0

while not done:
    # Her konumda en yüksek Q-value'ya sahip hareketi seç
    action = int(np.argmax(q_table[state]))

    next_state, reward, done = env.step(action)

    path.append(next_state)
    total_reward += reward
    state = next_state

success = state == env.goal

print("Success:", success)
print("Total Reward:", total_reward)
print("Steps:", env.steps)
print("Path:", path)

# Haritayı çiz
fig, ax = plt.subplots(figsize=(7, 7))

ax.set_xlim(-0.5, env.grid_size - 0.5)
ax.set_ylim(env.grid_size - 0.5, -0.5)

ax.set_xticks(range(env.grid_size))
ax.set_yticks(range(env.grid_size))
ax.grid(True)

# Engeller
for row, col in env.obstacles:
    ax.add_patch(
        plt.Rectangle(
            (col - 0.5, row - 0.5),
            1,
            1,
            color="gray"
        )
    )

# Başlangıç ve hedef
ax.scatter(
    0, 0,
    color="green",
    s=200,
    label="Start"
)

ax.scatter(
    env.goal[1],
    env.goal[0],
    color="red",
    s=200,
    label="Goal"
)

# Drone'un öğrendiği rota
x = [pos[1] for pos in path]
y = [pos[0] for pos in path]

ax.plot(
    x, y,
    color="blue",
    marker="o",
    linewidth=2,
    label="Drone Path"
)

ax.set_title("Learned Drone Navigation Path")
ax.legend()

plt.savefig("results/learned_path.png", dpi=150)
plt.show()
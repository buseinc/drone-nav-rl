from legacy.v1_qlearning.drone_env import DroneEnv

env = DroneEnv()

state = env.reset()

print("Starting position:", state)

actions = [3, 3, 1]

for action in actions:
    state, reward, done = env.step(action)

    print(
        "State:", state,
        "Reward:", reward,
        "Done:", done
    )

    if done:
        break
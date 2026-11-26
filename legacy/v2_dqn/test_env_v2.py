from legacy.v2_dqn.drone_env_v2 import DroneEnvV2

env = DroneEnvV2()

for i in range(3):
    state = env.reset()

    print(f"\nMap {i + 1}")
    print("Start:", env.start)
    print("Goal:", env.goal)
    print("Obstacles:", len(env.obstacles))
    print("State size:", len(state))
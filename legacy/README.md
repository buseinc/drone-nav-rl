# Legacy experiments

These experiments trace ORCA from a Q-table on a fixed map to the neural pilot
used by [SkyRush](../README.md). Run archived scripts from the repository root,
for example `python -m legacy.v3_dqn.evaluate_v3`.

| Version | Idea | Test success | What we learned |
|---|---|---|---|
| **v1** `v1_qlearning/` | Tabular Q-learning on one fixed map | works on that map only | A Q-table memorizes one map; it cannot generalize. |
| **v2** `v2_dqn/` | DQN, sees the whole 10x10 map as 100 numbers (+ a CNN variant) | **4 %** (crashes 50 %, loops 46 %) | A flat full-map view does not transfer to new maps. Reward too sparse. |
| **v3** `v3_dqn/` | Egocentric 7x7 view, visit memory, BFS reward shaping, Double DQN, curriculum | **95.5 %** | What the agent *sees* matters more than the algorithm. Goal-direction sign fixed the oscillation bug. |
| **v4** `src/` (current) | v3 + wind, patrols, hover action, revisit penalty | 84-96 % per hazard set | Agents exploit rewards (hovering forever); curriculum order matters. |

The archive includes the [trained models](models/), [training logs and plots](results/),
and the single-file prototypes for [v2](v2_dqn/game_v2_backup.py) and
[v3](v3_dqn/game_v3_single_backup.py).

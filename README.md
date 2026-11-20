# drone-nav-rl

Two pygame drone games built on one shared reinforcement-learning core.
The AI pilot **ORCA** is a Double DQN that learned to fly by itself.

## Run

```bash
python skyrush.py      # SkyRush: grid arcade game (missions, duels vs ORCA)
python lifeline.py     # Lifeline: emergency delivery game (in development)
python game.py         # shortcut for SkyRush
```

## Layout

```
src/                  shared core, used by both games
  drone_env_v4.py       grid world: wind, patrols, hover (the rules)
  train_dqn_v4.py       train ORCA   ->  models/dqn_v4.pth
  evaluate_v4.py        test ORCA on unseen maps
  shared/               agent, tick world, drone animation, effects,
                        sound, scene base, route search

games/skyrush/        SkyRush only (menus, modes, theme)
games/lifeline/       Lifeline only (its own theme and scenes)

models/               trained models (+ checkpoints for "watch it learn")
results/              training logs; *_save.json are personal saves (git-ignored)
```

Rule of thumb: game-specific code goes into its own `games/<name>/`
folder. Anything both games need (environment rules, ORCA, animation)
goes into `src/`. New mechanics are added to the environment as options
(like `wind_streams` and `enemy_count`) so ORCA can be trained with them
and the other game is not affected.

## Train / evaluate ORCA

```bash
python -m src.train_dqn_v4     # ~1 hour on CPU
python -m src.evaluate_v4
```

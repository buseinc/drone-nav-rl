# SkyRush

SkyRush is a grid-based drone racing game built with Python and Pygame. Navigate wind currents and moving patrols, race the ORCA AI pilot, and unlock new airframes as you earn mission stars and extend your Endless Circuit record.

## Quick start

With Python 3.10 or newer, run these commands from the repository root:

```bash
python -m pip install -r requirements.txt
python skyrush.py
```

Choose or create a local player profile to start. The trained ORCA model is included in the repository.

## Game modes

| Mode | What you play |
| --- | --- |
| **Sky Missions** | Earn stars across 16 stages in four zones. Each zone ends with a race against Legend ORCA. |
| **Endless Circuit** | Clear the final Sky Missions boss to unlock generated courses. Every fifth stage is a Legend ORCA race. |
| **Duel** | Race ORCA to the landing pad on Rookie, Ace, or Legend difficulty. Close finishes can trigger a photo finish. |
| **Tracks** | Race ORCA on hand-built courses with their own layouts and hazards. |
| **ORCA: On the Trail** | Start as a chick on a farm and unlock a duckling rescue scenario. |
| **Neural Lab** | Inspect the actions ORCA recommends as you explore the grid. |

The **Hangar** has two collections, **Flight Drones** and **Character Drones**. Mission stars and new Circuit records earn credits, and your profile remembers which drones you unlock and equip. Drone powers are available in solo Sky Missions and solo Circuit stages. Races use standard flight rules for both pilots.

## Controls

| Key | Action |
| --- | --- |
| Arrow keys | Fly or move through menus |
| `Space` | Hover during flight |
| `Q` | Arm a drone power when available |
| `Enter` | Confirm a menu selection |
| `H` | Open the Hangar from the main menu |
| `P` | Open profiles from the main menu |

Profiles and progress are saved locally in `results/skyrush_profiles.json`.

## Project layout

| Path | Contents |
| --- | --- |
| [`skyrush.py`](skyrush.py) | Game launcher |
| [`games/skyrush/`](games/skyrush/) | Menus, modes, airframes, and game art |
| [`src/`](src/) | Flight environment, ORCA network, training, and evaluation |
| [`models/`](models/) | Trained ORCA model and training checkpoints |
| [`legacy/`](legacy/README.md) | Archived versions and experiments from before SkyRush |

## ORCA

ORCA uses a Double DQN trained to reach landing pads while handling obstacles, wind, and moving patrols. The evaluation script measures performance on held-out maps, and the training script builds the model from scratch.

```bash
python -m src.evaluate_v4
python -m src.train_dqn_v4
```

Training writes a new model to `models/dqn_v4.pth`.

"""Player airframes, their prices and the profile's equipped model."""

from dataclasses import dataclass

from games.skyrush.save import load_leaderboard, save_leaderboard

MISSION_STAR_CREDITS = 100
CIRCUIT_STAGE_CREDITS = 150


@dataclass(frozen=True)
class Airframe:
    key: str
    name: str
    role: str
    power: str
    price: int
    accent: tuple
    shell: tuple
    description: tuple
    hardware: str = ""
    charges: int = 0


KESTREL = Airframe("kestrel", "Kestrel", "All-rounder", "Standard flight", 0,
                   (255, 164, 83), (223, 222, 206),
                   ("A balanced quadcopter for any route.",), "Standard motors")
PIP = Airframe("pip", "Pip", "Starter drone", "Standard flight", 0,
               (255, 164, 207), (247, 145, 192),
               ("A little pink drone with a glowing heart.",), "Heart light")
PUDDLE = Airframe("puddle", "Puddle", "Starter drone", "Standard flight", 0,
                  (255, 206, 96), (255, 210, 99),
                  ("A little duck with bright orange feet.",), "Webbed landing feet")
NEEDLE = Airframe("needle", "Needle", "Speed", "Boost", 850,
                  (100, 174, 255), (57, 103, 170),
                  ("Press Q, then fly two tiles in one move.", "One boost per flight. Mind the walls."), "Twin boost pods", 1)
MOTH = Airframe("moth", "Moth", "Patrol scout", "Look ahead", 1550,
                (217, 153, 255), (97, 71, 129),
                ("Purple rings show where patrols will be", "two moves ahead. Always on."), "Active radar")
ANCHOR = Airframe("anchor", "Anchor", "Wind control", "Wind brake", 3100,
                  (168, 224, 123), (103, 131, 106),
                  ("Press Q before entering a wind tile.", "Cancel the push. Two uses per flight."), "Twin brake vanes", 2)
BUMBLE = Airframe("bumble", "Bumble", "Patrol trickster", "Backstep", 950,
                  (255, 217, 111), (226, 167, 67),
                  ("Press Q, then Space to go back one tile.", "One backstep per flight."), "Flutter wings", 1)
JELLY = Airframe("jelly", "Jelly", "Corner specialist", "Side glide", 1250,
                 (210, 179, 255), (164, 118, 212),
                 ("Press Q, then turn left or right.", "Fly forward and turn in one move."), "Flexible thrusters", 1)
SPROUT = Airframe("sprout", "Sprout", "Wind scout", "Wind forecast", 750,
                  (150, 237, 197), (108, 194, 161),
                  ("Follow green dots to see where nearby", "wind would carry you. Always on."), "Leaf sensors")
FINCH = Airframe("finch", "Finch", "Bird drone", "Standard flight", 0,
                 (131, 213, 251), (84, 162, 206),
                 ("A curious bird with folding wings.",), "Folding wings")
ORBIT = Airframe("orbit", "Orbit", "Astronaut drone", "Standard flight", 0,
                 (127, 244, 224), (231, 237, 247),
                 ("A tiny astronaut with folding feet.",), "Polarized visor")
ORCA = Airframe("orca", "ORCA", "AI pilot", "Standard flight", 0,
                (86, 222, 247), (64, 81, 104), ())
FLIGHT_DRONES = (KESTREL, NEEDLE, MOTH, ANCHOR)
CHARACTER_DRONES = (PIP, PUDDLE, FINCH, ORBIT, BUMBLE, JELLY, SPROUT)
AIRFRAMES = FLIGHT_DRONES + CHARACTER_DRONES
BY_KEY = {airframe.key: airframe for airframe in AIRFRAMES}
BY_KEY["mochi"] = ORBIT  # Keep the equipped slot for profiles saved with Mochi.


def hangar_state(board):
    return board.get("hangar", {})


def is_owned(board, airframe):
    return airframe.price == 0 or airframe.key in hangar_state(board).get("owned", [])


def credits(board):
    earned = sum(board.get("missions", {}).values()) * MISSION_STAR_CREDITS
    earned += board.get("circuit_best", 0) * CIRCUIT_STAGE_CREDITS
    return earned - hangar_state(board).get("spent", 0)


def equipped_airframe():
    board = load_leaderboard()
    model = BY_KEY.get(hangar_state(board).get("equipped"), KESTREL)
    return model if is_owned(board, model) else KESTREL


def equip_airframe(airframe):
    """Equip a model, buying it once when enough credits are available."""
    board = load_leaderboard()
    owned = is_owned(board, airframe)
    if not owned and credits(board) < airframe.price:
        return False
    hangar = board.setdefault("hangar", {})
    if not owned:
        hangar.setdefault("owned", []).append(airframe.key)
        hangar["spent"] = hangar.get("spent", 0) + airframe.price
    hangar["equipped"] = airframe.key
    save_leaderboard(board)
    return True

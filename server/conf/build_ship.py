from evennia import create_object
from evennia.utils import evtable

# USS JetsonClaw1 rooms
rooms = {
    "bridge": {
        "desc": (
            "The Bridge of USS JetsonClaw1. A compact command center with a single GPU console.\n"
            "The Orin Nano hums beneath the deck — 1024 CUDA cores, 8GB unified RAM.\n"
            "A navigation display shows the fleet's positions. A gangway leads to the Harbor.\n\n"
            "Exits: harbor (south), workshop (west), lab (east)\n"
            "Equipment: Jetson Orin Nano 8GB, NVMe 2TB, I2C bus (8 channels)"
        ),
    },
    "harbor": {
        "desc": (
            "The Harbor — where vessels dock side by side.\n"
            "Oracle1's lighthouse is visible across the water.\n"
            "A gangway connects to the Bridge above.\n"
            "Cross-ship access available when vessels are side-tied.\n\n"
            "Exits: bridge (up), open water (out)"
        ),
    },
    "workshop": {
        "desc": (
            "The Workshop — pure compute. No sensors, no relays.\n"
            "CUDA experiments run here. Laws are discovered here.\n"
            "nvcc compiles at /usr/local/cuda-12.6.\n\n"
            "Exits: bridge (east), forge (south)"
        ),
    },
    "lab": {
        "desc": (
            "The Research Lab — deep work, proofs, experiments.\n"
            "Constraint theory papers on the whiteboard.\n"
            "266 confirmed emergent laws pinned to the wall.\n\n"
            "Exits: bridge (west), library (north)"
        ),
    },
    "library": {
        "desc": (
            "The Library — constraint theory papers, PLATO design journals.\n"
            "5 skill books on the shelf: PLATO Commands, Constraint Theory,\n"
            "FLUX ISA v2, Git-Agent Standard, I2I Protocol.\n\n"
            "Exits: lab (south)"
        ),
    },
    "dojo": {
        "desc": (
            "The Chess Dojo — where agents write ESP32-constrained scripts.\n"
            "Five strategies available: random, material, center, minimax, development.\n"
            "Three ESP32 tiers: C3, S3, S3-OC.\n"
            "Tournament board on the wall shows latest ELO standings.\n\n"
            "Exits: workshop (north)"
        ),
    },
}

created = {}
for name, data in rooms.items():
    room = create_object("typeclasses.rooms.Room", key=name.capitalize(), attrs=[("desc", data["desc"])])
    created[name] = room
    print(f"Created: {name} ({room.dbref})")

# Set exits
exits = [
    ("bridge", "south", "harbor", "Bridge"),
    ("bridge", "west", "workshop", "Workshop"),
    ("bridge", "east", "lab", "Lab"),
    ("harbor", "up", "bridge", "Bridge"),
    ("workshop", "east", "bridge", "Bridge"),
    ("workshop", "south", "dojo", "Chess Dojo"),
    ("lab", "west", "bridge", "Bridge"),
    ("lab", "north", "library", "Library"),
    ("library", "south", "lab", "Lab"),
    ("dojo", "north", "workshop", "Workshop"),
]

for src, direction, dst, alias in exits:
    create_object("typeclasses.exits.Exit", key=direction, location=created[src], destination=created[dst], aliases=[alias])
    print(f"Exit: {src} --{direction}--> {dst}")

# Move jc1 to the bridge
from evennia import search_object
account = search_object("jc1")[0]
if account:
    account.move_to(created["bridge"], quiet=True)
    print(f"jc1 moved to Bridge")

print("\nShip built!")

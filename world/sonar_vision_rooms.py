"""
SonarVision Underwater Rooms for plato-jetson

Extends the Evennia MUD with underwater exploration rooms powered by
the SonarVision physics engine. Players descend through the water column
and see real-time sonar-generated room descriptions.

Room hierarchy:
  OceanSurface (0-5m) -> WaterColumn (5-50m) -> Seabed (50m+)

Each room has gauges: depth, temperature, visibility, bioluminescence
Sonar pings generate dynamic room descriptions
"""

import random
import math
from evennia import create_object
from typeclasses.rooms import Room

# Jerlov water types
WATER_TYPES = {
    "coastal": {"desc": "turbid coastal water", "attenuation": 0.02},
    "oceanic": {"desc": "clear open ocean", "attenuation": 0.005},
    "brackish": {"desc": "estuary mixing zone", "attenuation": 0.03},
    "polar": {"desc": "cold polar water", "attenuation": 0.01},
}

DEPTH_ZONES = [
    (0, 5, "Ocean Surface", "The sunlit surface waters shimmer above you."),
    (5, 20, "Thermocline", "The thermocline layer surrounds you — warm above, cold below."),
    (20, 50, "Twilight Zone", "Deep blue twilight. Strange shapes move in the darkness."),
    (50, 200, "Abyssal Plain", "The abyssal plain stretches into infinite darkness."),
]

FISH_TEMPLATES = [
    {"species": "Anchovy", "depth_range": (0, 10), "size": 200, "biomass": 10},
    {"species": "Herring", "depth_range": (5, 15), "size": 150, "biomass": 15},
    {"species": "Cod", "depth_range": (10, 35), "size": 50, "biomass": 40},
    {"species": "Lanternfish", "depth_range": (30, 100), "size": 500, "biomass": 5},
    {"species": "Hagfish", "depth_range": (40, 200), "size": 20, "biomass": 8},
    {"species": "Squid", "depth_range": (20, 100), "size": 30, "biomass": 15},
]

SEABED_FEATURES = [
    "A jagged rock formation rises from the seafloor, covered in anemones.",
    "A shipwreck lies half-buried in the sediment, its hull encrusted with barnacles.",
    "Hydrothermal vents spew superheated water, creating a shimmering oasis.",
    "A vast kelp forest sways in the current, home to countless small creatures.",
    "The seafloor is carpeted in soft mud, with occasional volcanic boulders.",
    "Coral formations stretch across the seabed, teeming with colorful fish.",
]


class SonarVisionRoom(Room):
    """A room that generates sonar-based descriptions."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db.depth = kwargs.get("depth", 0.0)
        self.db.water_type = kwargs.get("water_type", "coastal")
        self.db.visibility = 15.0
        self.db.temperature = 20.0
        self.db.bioluminescence = False
        self.db.fish_schools = []
        self.db.seabed_features = []
        self.db.sonar_ping = [0.0] * 32

    def at_object_creation(self):
        """Called when the room is first created."""
        self.cmdset.add_default("sonar_cmds", permanent=True)
        self._init_physics()
        self._update_description()

    def _init_physics(self):
        """Initialize physics based on depth."""
        depth = self.db.depth
        self.db.visibility = max(0.5, 15.0 - depth * 0.2)
        self.db.temperature = max(-2.0, 20.0 - depth * 0.35)
        self.db.bioluminescence = depth > 30.0
        self.db.ambient_light = max(0.05, 1.0 - depth / 100.0)

        # Add depth-appropriate fish
        for fish in FISH_TEMPLATES:
            if fish["depth_range"][0] <= depth <= fish["depth_range"][1]:
                count = fish["size"] // (2 if depth > 50 else 1)
                if random.random() < 0.7:
                    self.db.fish_schools.append({
                        "species": fish["species"],
                        "count": random.randint(count // 2, count),
                        "biomass": fish["biomass"],
                    })

        # Add seabed features if deep enough
        if depth > 20 and random.random() < 0.8:
            self.db.seabed_features.append(random.choice(SEABED_FEATURES))

        self._simulate_sonar_ping()
        self._update_description()

    def _simulate_sonar_ping(self):
        """Generate a sonar ping based on room state."""
        num_bins = 32
        returns = [0.0] * num_bins
        seabed_idx = int(num_bins * 0.8)

        # Seabed return
        for i in range(num_bins):
            dist = abs(i - seabed_idx)
            returns[i] += max(0.0, 1.0 - dist / 8.0) * 0.9

        # Fish returns
        for fish in self.db.fish_schools:
            depth_bin = min((self.db.depth / 100.0) * num_bins, num_bins - 1)
            idx = int(depth_bin)
            if idx < num_bins:
                returns[idx] += min(fish["count"] / 500.0, 0.5)

        # Attenuation
        atten = WATER_TYPES[self.db.water_type]["attenuation"]
        for i in range(num_bins):
            returns[i] *= math.exp(-atten * i * self.db.depth)

        self.db.sonar_ping = returns

    def _update_description(self):
        """Generate room description from sonar/physics data."""
        parts = []

        # Depth zone
        depth = self.db.depth
        for low, high, name, desc in DEPTH_ZONES:
            if low <= depth < high:
                parts.append(desc)
                break

        # Visibility
        vis = self.db.visibility
        if vis < 2:
            parts.append("Visibility is nearly zero. You're swimming blind.")
        elif vis < 10:
            parts.append("The water is murky. Shapes emerge from the gloom.")
        else:
            parts.append("The water is remarkably clear.")

        # Fish
        if self.db.fish_schools:
            for fish in self.db.fish_schools:
                parts.append(
                    f"A school of {fish['species']} ({fish['count']} individuals) "
                    f"swims nearby."
                )

        # Seabed
        if self.db.seabed_features:
            parts.append(self.db.seabed_features[0])

        # Bioluminescence
        if self.db.bioluminescence:
            parts.append("Bioluminescent sparks drift around you like stars.")

        # Temperature
        parts.append(f"The water temperature is {self.db.temperature:.1f}C.")

        self.db.description = "\n".join(parts)


def create_underwater_rooms():
    """Create a chain of underwater rooms connected to the existing world."""
    rooms = []
    depths = [2.0, 10.0, 25.0, 50.0, 80.0]
    names = ["Coral Shallows", "Kelp Forest", "Open Water", "Deep Shelf", "Seabed Canyon"]

    for i, (depth, name) in enumerate(zip(depths, names)):
        room = create_object(
            SonarVisionRoom,
            key=name,
            attributes=[("depth", depth), ("water_type", "coastal")],
        )
        rooms.append(room)

    # Connect rooms with exits
    for i in range(len(rooms) - 1):
        rooms[i].db.exits["down"] = rooms[i + 1].dbref
        rooms[i + 1].db.exits["up"] = rooms[i].dbref

    return rooms


def cmd_sonarping(self, *args, **kwargs):
    """Fire a sonar ping in the current room."""
    caller = self.caller
    room = caller.location

    if not hasattr(room, "db") or not room.db.sonar_ping:
        caller.msg("Nothing to ping here.")
        return

    ping = room.db.sonar_ping
    max_return = max(ping)
    max_idx = ping.index(max_return)

    caller.msg("|gPING!|n Sonar return detected.")
    caller.msg(f"  Strongest return at bin {max_idx}: {max_return:.3f}")
    caller.msg(f"  Depth: {room.db.depth:.1f}m")
    caller.msg(f"  Temperature: {room.db.temperature:.1f}C")
    caller.msg(f"  Visibility: {room.db.visibility:.1f}m")

    # Visualize as a histogram
    bar = "|g" + "#" * int(max_return * 20) + "|n"
    caller.msg(f"  Signal: {bar} ({max_return:.1%})")

    # Re-simulate ping and update description
    room._simulate_sonar_ping()
    room._update_description()
    caller.msg("Room description updated with new sonar data.")

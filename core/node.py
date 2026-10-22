"""core/node.py - one glowing circle on the map.

What it is for : a tiny record (a @dataclass) holding everything a node knows about itself.
Uses            : config.py.
Used by         : core/mapgen.py (creates them), core/world.py, core/ai.py, graphics/, ui/.

A @dataclass is Python writing the boring __init__ for us: list the fields and you can
write Node(x=10, y=20, ...).
"""
from dataclasses import dataclass

from config import NODE_RADIUS, CAP_PER_SIZE


@dataclass
class Node:
    x: float
    y: float
    size: int                  # 1, 2 or 3 (small / medium / big)
    owner: int = 0             # 0 = neutral, 1 = player, 2..4 = computer opponents
    garrison: float = 0.0      # ships stationed here (shown as a whole number)
    radius: int = 0
    cap: int = 0               # production stops when the garrison reaches this

    def __post_init__(self):
        # Fill radius and cap from the size unless the caller gave them.
        if not self.radius:
            self.radius = NODE_RADIUS[self.size]
        if not self.cap:
            self.cap = CAP_PER_SIZE * self.size

    @property
    def production(self):
        """Ships made per beat: 1, 2 or 3. Neutral nodes make none (checked by the World)."""
        return self.size

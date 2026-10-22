"""core/node.py - one glowing circle on the map.

What it is for : a tiny record (a @dataclass) holding everything a node knows about itself.
Uses            : config.py.
Used by         : core/mapgen.py (creates them), core/world.py, core/ai.py, graphics/, ui/.

A @dataclass is Python writing the boring __init__ for us: list the fields and you can
write Node(x=10, y=20, ...).

Special kinds (config.KIND_NAMES): a NORMAL node is the plain circle. A FORTRESS is hard to take (its
attackers need more ships per defender), a FACTORY makes twice the ships, a RELAY launches faster ships.
"""
from dataclasses import dataclass

from config import (NODE_RADIUS, CAP_PER_SIZE, NODE_NORMAL, NODE_FORTRESS, NODE_FACTORY, FORTRESS_BONUS, FACTORY_BOOST, PACE)


@dataclass
class Node:
    x: float
    y: float
    size: int                  # 1, 2 or 3 (small / medium / big)
    owner: int = 0             # 0 = neutral, 1 = player, 2..4 = computer opponents
    garrison: float = 0.0      # ships stationed here (shown as a whole number)
    radius: int = 0
    cap: int = 0               # production stops when the garrison reaches this
    kind: int = NODE_NORMAL    # NODE_NORMAL / NODE_FORTRESS / NODE_FACTORY / NODE_RELAY (config.py)
    absorbed: int = 0          # how many attackers have landed (used to count off the fortress shield)
    unrest: int = 0            # beats left until a freshly captured node makes ships again

    def __post_init__(self):
        # Fill radius and cap from the size unless the caller gave them.
        if not self.radius:
            self.radius = NODE_RADIUS[self.size]
        if not self.cap:
            self.cap = CAP_PER_SIZE * self.size

    @property
    def production(self):
        """Ships made per beat: 1, 2 or 3 (doubled for a factory). Neutral nodes make none (checked by the World)."""
        return self.size * (FACTORY_BOOST if self.kind == NODE_FACTORY else 1)

    @property
    def shield(self):
        """How many attacking ships it takes to remove ONE defender: the match-length setting (config.PACE), plus the
        FORTRESS_BONUS in a fortress."""
        return PACE["defence"] + (FORTRESS_BONUS if self.kind == NODE_FORTRESS else 0.0)

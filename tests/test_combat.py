"""tests/test_combat.py - mid-air clashes: equal swarms cancel, the bigger one keeps the difference."""
import numpy as np

import helpers
from helpers import check
from core.combat import resolve_clashes
from core.node import Node
from core.ships import Ships
from core.world import World


def duel(n_a, n_b, size=1, seed=1, ticks=250):
    """A (owner 1, left) and B (owner 2, right) send n_a / n_b ships at each other.
    Returns (survivors of owner 1, survivors of owner 2) while they are still in the air."""
    nodes = [Node(300, 500, size, owner=1, garrison=200), Node(1500, 500, size, owner=2, garrison=200)]
    w = World(seed=seed, n_factions=2, nodes=nodes)
    for node in w.nodes:
        node.cap = 0                                       # production off: garrison only changes through orders
    w.order([0], 1, n_a / 200, 1)
    w.order([1], 0, n_b / 200, 2)
    for _ in range(ticks):
        w.tick()
    by_owner = w.ships.count_by_owner()
    return int(by_owner[1]), int(by_owner[2]), w


def run():
    a, b, _ = duel(30, 30)
    check(a + b <= 4, f"30 vs 30 on the same line cancel out almost completely (left: {a} + {b})")
    a, b, _ = duel(30, 20)
    check(a >= 6 and b <= 3 and 6 <= a - b <= 14, f"30 vs 20 leaves about 10 (left: {a} vs {b})")
    a, b, w = duel(25, 25, size=3)
    check(a + b <= 8, f"big nodes (wide lanes): still mostly cancel (left {a} + {b})")
    check(w.stats.lost[1] >= 15 and w.stats.lost[2] >= 15, "stats count the ships lost in the clash")

    # clash events carry a position
    nodes = [Node(300, 500, 1, owner=1, garrison=200), Node(1500, 500, 1, owner=2, garrison=200)]
    w = World(seed=1, n_factions=2, nodes=nodes)
    for node in w.nodes:
        node.cap = 0
    w.order([0], 1, 0.2, 1)
    w.order([1], 0, 0.2, 2)
    clashes = []
    for _ in range(250):
        w.tick()
        clashes += [e for e in w.drain_events() if e[0] == "clash"]
    check(len(clashes) > 3, "clash events are emitted")
    check(all(500 < e[1] < 1300 and 400 < e[2] < 600 and e[3] >= 1 and {e[4], e[5]} == {1, 2} for e in clashes),
          "clash events: sensible position, kill count and both owners")

    # ships of the SAME owner never clash, even when they overlap exactly
    ships = Ships()
    rng = np.random.default_rng(3)
    n1, n2 = Node(100, 100, 1), Node(900, 100, 1)
    ships.launch(1, n1, 1, n2, 40, rng)
    ships.launch(1, n1, 1, n2, 40, rng)
    for t in range(4):
        records, killed = resolve_clashes(ships, t)
        check(records == [] and ships.count() == 80, "same-owner ships never clash")

    # the smallest group in a room decides: 3 vs 5 in one spot -> 2 of owner 2 survive
    ships = Ships()
    ships.pos[:8] = (500.0, 500.0)
    ships.owner[:8] = [1, 1, 1, 2, 2, 2, 2, 2]
    ships.alive[:8] = True
    records, killed = resolve_clashes(ships, 0)
    by_owner = ships.count_by_owner()
    check(by_owner[1] == 0 and by_owner[2] == 2, "3 vs 5 in one cell: the 3 die, 2 survive")
    check(len(records) == 1 and records[0][2] == 6 and killed[1] == 3 and killed[2] == 3, "one record, 6 killed")

    # a pair split by a cell border is caught on the odd tick (grid shifted by half a cell)
    ships = Ships()
    ships.pos[0] = (41.0, 500.0)                           # cell border at x = 42 (cell size 21)
    ships.pos[1] = (43.0, 500.0)
    ships.owner[:2] = [1, 2]
    ships.alive[:2] = True
    records, _ = resolve_clashes(ships, 0)
    check(records == [] and ships.count() == 2, "even tick: a border pair is missed")
    records, _ = resolve_clashes(ships, 1)
    check(len(records) == 1 and ships.count() == 0, "odd tick: the shifted grid catches it")


if __name__ == "__main__":
    run()
    raise SystemExit(0 if helpers.report("test_combat") else 1)

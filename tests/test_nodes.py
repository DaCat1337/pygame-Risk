"""tests/test_nodes.py - the special node types: FORTRESS, FACTORY and RELAY (rules, map generation and AI).

What it is for : proves each kind does what config.KIND_HELP says, that the map generator hands them out fairly,
                 and that the computer opponent knows about them.
Uses            : core/node.py, core/world.py, core/mapgen.py, core/ai.py.
Used by         : tests/run_all.py.
"""
import math

import helpers
from helpers import check

from config import (SHIP_SPEED, RELAY_SPEED, FACTORY_BOOST, FORTRESS_SHIELD, NODE_NORMAL, NODE_FORTRESS, NODE_FACTORY,
                    NODE_RELAY, KIND_MIX)
from core.ai import ai_think
from core.mapgen import generate_map
from core.node import Node
from core.world import World


def world_with(*nodes):
    return World(seed=1, n_factions=2, nodes=list(nodes))


def run():
    # --- FACTORY: twice the production, shown by Node.production and by the beat
    plain, factory = Node(300, 500, 2, owner=1, garrison=10), Node(300, 500, 2, owner=1, garrison=10, kind=NODE_FACTORY)
    check(plain.production == 2 and factory.production == 2 * FACTORY_BOOST, "a factory makes twice the ships")
    w = world_with(factory, Node(1600, 500, 2, owner=2, garrison=10))
    w.tick()                                                # tick 0 is a beat
    check(w.nodes[0].garrison == 10 + 4, "a size-2 factory gains 4 on the beat")

    # --- FORTRESS: only every second attacker hurts a defender
    fort = Node(800, 500, 2, owner=0, garrison=10, kind=NODE_FORTRESS)
    w = world_with(Node(300, 500, 2, owner=1, garrison=10), fort, Node(1600, 500, 2, owner=2, garrison=10))
    check(fort.shield == FORTRESS_SHIELD and w.nodes[0].shield == 1, "only a fortress has a shield")
    for _ in range(10):
        w._land(1, 1)
    check(fort.garrison == 5 and fort.owner == 0, "10 attackers remove only 5 defenders from a fortress")
    check(w.stats.lost[1] == 10, "every attacker counts as lost, also the ones that bounce off")
    for _ in range(10):
        w._land(1, 1)
    check(fort.garrison == 0 and fort.owner == 0, "20 attackers leave a 10-defender fortress at 0, not yet captured")
    w._land(1, 1)
    w._land(1, 1)
    check(fort.owner == 1 and fort.garrison == 1, "the next two attackers capture it (one bounces, one breaks through)")
    check(fort.absorbed == 0, "the wall counter starts again after a capture")
    own = Node(800, 500, 2, owner=1, garrison=10, kind=NODE_FORTRESS)
    w = world_with(Node(300, 500, 2, owner=1, garrison=10), own, Node(1600, 500, 2, owner=2, garrison=10))
    w._land(1, 1)
    check(own.garrison == 11, "your own ships reinforce a fortress as usual")
    neutral_fort = Node(800, 500, 2, owner=0, garrison=10, kind=NODE_FORTRESS)
    w = world_with(Node(300, 500, 2, owner=1, garrison=10), neutral_fort, Node(1600, 500, 2, owner=2, garrison=10))
    check(w.needed_to_capture(1, [0]) == 10 * 2 + 1, "'needs ~N' counts double for a fortress")

    # --- RELAY: ships launched from it fly faster
    relay = Node(300, 500, 2, owner=1, garrison=10, kind=NODE_RELAY)
    w = world_with(relay, Node(1600, 500, 2, owner=2, garrison=10), Node(800, 300, 1, owner=0, garrison=5))
    w.order([0], 2, 1.0, 1)
    for _ in range(70):
        w.tick()
    speeds = [math.hypot(*w.ships.vel[i]) for i in range(len(w.ships.alive)) if w.ships.alive[i]]
    check(speeds and all(abs(s - SHIP_SPEED * RELAY_SPEED) < 0.5 for s in speeds), "relay ships fly 1.5x faster")
    w = world_with(Node(300, 500, 2, owner=1, garrison=10), Node(1600, 500, 2, owner=2, garrison=10), Node(800, 300, 1, owner=0, garrison=5))
    w.order([0], 2, 1.0, 1)
    for _ in range(70):
        w.tick()
    speeds = [math.hypot(*w.ships.vel[i]) for i in range(len(w.ships.alive)) if w.ships.alive[i]]
    check(speeds and all(abs(s - SHIP_SPEED) < 0.5 for s in speeds), "normal ships keep the normal speed")

    # --- map generation: start nodes are plain, kinds are handed out, twins match, same seed = same kinds
    kinds_seen = {NODE_NORMAL: 0, NODE_FORTRESS: 0, NODE_FACTORY: 0, NODE_RELAY: 0}
    twins_ok = starts_ok = repeat_ok = True
    for seed in range(60):
        for factions in (2, 3, 4):
            nodes = generate_map(seed, factions, 1)
            starts_ok &= all(n.kind == NODE_NORMAL for n in nodes if n.owner)
            repeat_ok &= [n.kind for n in nodes] == [n.kind for n in generate_map(seed, factions, 1)]
            for n in nodes:
                if not n.owner:
                    kinds_seen[n.kind] += 1
            if factions == 2:
                for n in nodes:
                    if n.owner == 0:
                        twin = [m for m in nodes if m.owner == 0 and abs(m.x + n.x - 2 * 960) < 1e-6 and abs(m.y + n.y - 2 * 590) < 1e-6]
                        twins_ok &= len(twin) == 1 and twin[0].kind == n.kind
    check(starts_ok, "start nodes are always normal")
    check(twins_ok, "on a 2-faction map the mirrored twin has the same kind (fair)")
    check(repeat_ok, "the same seed gives the same kinds")
    total = sum(kinds_seen.values())
    for kind, share in zip((NODE_FORTRESS, NODE_FACTORY, NODE_RELAY), KIND_MIX):
        check(abs(kinds_seen[kind] / total - share) < 0.05, f"kind {kind}: about {share:.0%} of the neutral nodes ({kinds_seen[kind] / total:.0%})")

    # --- the AI knows a fortress is harder: it sends more ships at it than at a normal node
    def ai_sends(kind):
        nodes = [Node(300, 500, 3, owner=2, garrison=60), Node(1800, 900, 1, owner=1, garrison=10),
                 Node(900, 500, 2, owner=0, garrison=10, kind=kind)]
        world = World(seed=1, n_factions=2, nodes=nodes)
        orders = ai_think(world, 2, "EXTREME", world.rng)
        return sum(int(nodes[s].garrison * f) for s, t, f in orders if t == 2)

    check(ai_sends(NODE_NORMAL) > 0 and ai_sends(NODE_FORTRESS) > ai_sends(NODE_NORMAL), "the AI sends more ships against a fortress")


if __name__ == "__main__":
    run()
    raise SystemExit(0 if helpers.report("test_nodes") else 1)

"""tests/test_mapgen.py - maps must be deterministic, fair, non-overlapping and inside the margins."""
import math

import helpers
from helpers import check
from config import MAP_NODES, MIN_NODE_GAP, MARGIN, HUD_TOP, SCREEN_W, SCREEN_H
from core.mapgen import generate_map, CENTER


def _gap_ok(nodes):
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            if math.hypot(a.x - b.x, a.y - b.y) < a.radius + b.radius + MIN_NODE_GAP - 1e-6:
                return False
    return True


def _inside(nodes):
    return all(MARGIN <= n.x - n.radius and n.x + n.radius <= SCREEN_W - MARGIN
               and MARGIN + HUD_TOP <= n.y - n.radius and n.y + n.radius <= SCREEN_H - MARGIN for n in nodes)


def run():
    a, b = generate_map(5, 2, 1), generate_map(5, 2, 1)
    check([(n.x, n.y, n.size, n.owner, n.garrison) for n in a] == [(n.x, n.y, n.size, n.owner, n.garrison) for n in b],
          "same seed = identical map")
    c = generate_map(6, 2, 1)
    check([(n.x, n.y) for n in a] != [(n.x, n.y) for n in c], "different seed = different map")

    for factions in (2, 3, 4):
        for size in (0, 1, 2):
            nodes = generate_map(3, factions, size)
            check(len(nodes) == MAP_NODES[size], f"{factions} factions, map {size}: {MAP_NODES[size]} nodes (got {len(nodes)})")
            check(sorted(n.owner for n in nodes if n.owner) == list(range(1, factions + 1)), "exactly one start node per faction")
            check(all(n.size == 3 and n.garrison == 30 for n in nodes if n.owner), "start nodes: size 3, garrison 30")
            check(all(n.garrison >= n.size * 4 and n.garrison <= n.size * 10 for n in nodes if not n.owner),
                  "neutral garrison = size * 4..10")

    # many seeds: no overlaps, inside the margins, all generate
    ok_gap = ok_inside = ok_mirror = True
    for seed in range(200):
        for factions in (2, 3, 4):
            nodes = generate_map(seed, factions, 1 if seed % 3 else 2)
            ok_gap &= _gap_ok(nodes)
            ok_inside &= _inside(nodes)
        two = generate_map(seed, 2, seed % 3)
        for n in two:
            twin = [m for m in two if abs(m.x - (2 * CENTER[0] - n.x)) < 1e-6 and abs(m.y - (2 * CENTER[1] - n.y)) < 1e-6]
            ok_mirror &= len(twin) == 1 and twin[0].size == n.size and twin[0].garrison == n.garrison
    check(ok_gap, "200 seeds: nodes keep the minimum gap (42 px between edges)")
    check(ok_inside, "200 seeds: nodes stay inside the margins")
    check(ok_mirror, "200 seeds: the 2-faction map is point-symmetric (size and garrison too)")
    two = generate_map(9, 2, 1)
    check(abs(two[0].x + two[1].x - 2 * CENTER[0]) < 1e-6, "the two start nodes are mirror images")


if __name__ == "__main__":
    run()
    raise SystemExit(0 if helpers.report("test_mapgen") else 1)

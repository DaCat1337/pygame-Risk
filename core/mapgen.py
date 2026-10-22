"""core/mapgen.py - builds a fair, seeded map of nodes.

What it is for : generate_map(seed, n_factions, map_size) -> list of Node. Same seed + same
                 settings always gives the same map.
Uses            : config.py, core/node.py.
Used by         : core/world.py.

Fairness:
  * 2 factions: we build HALF the map and mirror it through the centre of the play area
    (point symmetry, like a playing card). Both players get the very same neighbourhood.
  * 3-4 factions: the start nodes sit evenly spaced on an ellipse; the rest is scattered.

Rejection sampling = "throw a dart at a random spot; if it overlaps something, throw again".
"""
import math

import numpy as np

from config import (SCREEN_W, SCREEN_H, MARGIN, HUD_TOP, MIN_NODE_GAP, MAP_NODES, SIZE_MIX, NODE_RADIUS,
                    START_SIZE, START_GARRISON, NEUTRAL_GARRISON_PER_SIZE, MAPGEN_MAX_TRIES)
from core.node import Node

# The rectangle the node CENTRES may move in is computed per node (it shrinks by the radius).
AREA_LEFT, AREA_RIGHT = MARGIN, SCREEN_W - MARGIN
AREA_TOP, AREA_BOTTOM = MARGIN + HUD_TOP, SCREEN_H - MARGIN
CENTER = ((AREA_LEFT + AREA_RIGHT) / 2, (AREA_TOP + AREA_BOTTOM) / 2)   # NOT the screen centre: the HUD takes the top


def _inside(x, y, r):
    """Is a circle of radius r at (x, y) fully inside the play area?"""
    return AREA_LEFT + r <= x <= AREA_RIGHT - r and AREA_TOP + r <= y <= AREA_BOTTOM - r


def _free(x, y, r, placed):
    """True if the circle keeps MIN_NODE_GAP from every already placed (x, y, r)."""
    for px, py, pr in placed:
        if math.hypot(x - px, y - py) < r + pr + MIN_NODE_GAP:
            return False
    return True


def _mirror(x, y):
    """Point reflection through the centre: (x, y) -> the opposite side."""
    return 2 * CENTER[0] - x, 2 * CENTER[1] - y


def _random_sizes(rng, count):
    """Sizes for the non-start nodes, ordered big to small (big circles are hardest to fit)."""
    sizes = rng.choice([1, 2, 3], size=count, p=SIZE_MIX)
    return sorted((int(s) for s in sizes), reverse=True)


def _neutral(x, y, size, rng):
    lo, hi = NEUTRAL_GARRISON_PER_SIZE
    return Node(x, y, size, owner=0, garrison=float(size * rng.integers(lo, hi)))


def _start(x, y, owner):
    return Node(x, y, START_SIZE, owner=owner, garrison=float(START_GARRISON))


def _try_two_factions(rng, total):
    """Half map + its mirror image. Returns the node list or None if we got stuck."""
    r_start = NODE_RADIUS[START_SIZE]
    # start node: somewhere in the left part of the map, its twin lands on the right
    sx = rng.uniform(AREA_LEFT + r_start, AREA_LEFT + 420)
    sy = rng.uniform(AREA_TOP + r_start, AREA_BOTTOM - r_start)
    mx, my = _mirror(sx, sy)
    nodes = [_start(sx, sy, 1), _start(mx, my, 2)]
    placed = [(sx, sy, r_start), (mx, my, r_start)]
    pairs = []                                   # the neutrals of the left half; the right half is a copy
    for size in _random_sizes(rng, total // 2 - 1):
        r = NODE_RADIUS[size]
        for _ in range(MAPGEN_MAX_TRIES):
            x = rng.uniform(AREA_LEFT + r, CENTER[0])
            y = rng.uniform(AREA_TOP + r, AREA_BOTTOM - r)
            mx, my = _mirror(x, y)
            # the twin must not touch the original either (matters near the centre line)
            if (_inside(x, y, r) and _free(x, y, r, placed) and _free(mx, my, r, placed)
                    and math.hypot(x - mx, y - my) >= 2 * r + MIN_NODE_GAP):
                placed += [(x, y, r), (mx, my, r)]
                pairs.append((x, y, size))
                break
        else:
            return None
    for x, y, size in pairs:
        left = _neutral(x, y, size, rng)
        mx, my = _mirror(x, y)
        nodes += [left, Node(mx, my, size, owner=0, garrison=left.garrison)]   # same garrison = fair
    return nodes


def _try_many_factions(rng, total, n_factions):
    """3-4 factions: start nodes on an ellipse (random rotation), the rest by rejection sampling."""
    r_start = NODE_RADIUS[START_SIZE]
    spin = rng.uniform(0, 2 * math.pi)
    nodes, placed = [], []
    for k in range(n_factions):
        a = spin + 2 * math.pi * k / n_factions
        x = CENTER[0] + 650 * math.cos(a)
        y = CENTER[1] + 280 * math.sin(a)
        nodes.append(_start(x, y, k + 1))
        placed.append((x, y, r_start))
    for size in _random_sizes(rng, total - n_factions):
        r = NODE_RADIUS[size]
        for _ in range(MAPGEN_MAX_TRIES):
            x = rng.uniform(AREA_LEFT + r, AREA_RIGHT - r)
            y = rng.uniform(AREA_TOP + r, AREA_BOTTOM - r)
            if _free(x, y, r, placed):
                placed.append((x, y, r))
                nodes.append(_neutral(x, y, size, rng))
                break
        else:
            return None
    return nodes


def generate_map(seed, n_factions, map_size):
    """Build the node list. n_factions counts the player too (2..4); map_size is 0/1/2."""
    total = MAP_NODES[map_size]
    if n_factions == 2 and total % 2:
        total += 1                               # a mirrored map needs an even count
    attempt_seed = seed
    while True:
        rng = np.random.default_rng(attempt_seed)
        if n_factions == 2:
            nodes = _try_two_factions(rng, total)
        else:
            nodes = _try_many_factions(rng, total, n_factions)
        if nodes is not None:
            return nodes
        attempt_seed += 1000                     # unlucky layout: retry with a different seed

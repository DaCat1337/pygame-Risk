"""core/ai.py - the computer opponents: a simple "greedy" AI.

What it is for : ai_think(world, faction, difficulty, rng) looks at the board and returns a short
                 list of orders. Greedy = "always take the best-looking move right now"; there is
                 no long-term plan, which keeps the code short and the opponent beatable.
Uses            : config.py, numpy.
Used by         : core/world.py (calls it on the beats; the orders go through world.order(), the
                 very same function the player uses - the AI never cheats).

Each order is a tuple (source_node, target_node, fraction_of_garrison_to_send).
The numbers that make EASY / NORMAL / HARD / EXTREME different live in config.AI_TABLE.
"""
import math
from dataclasses import dataclass

import numpy as np

from config import (AI_TABLE, AI_REACTION, DIFFICULTIES, AI_PLAYER_BIAS_EXTREME, AI_SURPLUS, AI_SURPLUS_FLAT, PACE, BEAT,
                    PLAYER, NEUTRAL, NODE_FACTORY)

def _per_beat():
    """Pixels a ship flies in one beat (it depends on the match-length setting)."""
    return PACE["speed"] * BEAT


@dataclass
class Opponent:
    """What the World remembers about one computer player."""
    difficulty: int                        # index into config.DIFFICULTIES
    rng: np.random.Generator               # its own dice: only used to break ties, so matches are repeatable
    reaction: int = 1                      # index into config.REACTION_NAMES: SLOW, NORMAL, FAST


MIN_THINK_EVERY = 2                    # beats: the fastest an AI may think


def ai_timing(difficulty_name, reaction=1):
    """(think_every, start_delay) in beats for a difficulty at a reaction speed: the table's numbers scaled by AI_REACTION.
    SLOW thinks less often and starts later, FAST thinks more often and starts sooner. It never thinks more often than every
    2 beats: measured, an AI that re-plans on every single beat plays WORSE (it keeps changing its mind), and EXTREME is
    already at that limit, so FAST only makes EXTREME start sooner (it already starts at once)."""
    cfg = AI_TABLE[difficulty_name]
    think_factor, delay_factor = AI_REACTION[reaction]
    return max(MIN_THINK_EVERY, round(cfg["think_every"] * think_factor)), round(cfg["start_delay"] * delay_factor)


def _dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def _ships_heading_to(world, faction):
    """What is on its way to each node, from this faction's point of view.

    Returns (mine, theirs, nearest):
      mine[t]    = ships of `faction` flying to node t, plus its own queued orders (it knows those)
      theirs[t][owner] = ships of each other owner that are FLYING to node t (the AI only sees what is on screen)
      nearest[t] = distance of the closest enemy ship to node t (inf if none)
    """
    n = len(world.nodes)
    ships = world.ships
    idx = np.flatnonzero(ships.alive)
    mine = np.zeros(n)
    theirs = np.zeros((n, world.n_factions + 1))
    nearest = np.full(n, np.inf)
    if len(idx):
        tgt, own = ships.target[idx].astype(np.int64), ships.owner[idx].astype(np.int64)
        mask = own == faction
        mine += np.bincount(tgt[mask], minlength=n)
        np.add.at(theirs, (tgt[~mask], own[~mask]), 1)
        d = np.hypot(*(ships.pos[idx][~mask] - world.node_xy[tgt[~mask]]).T)
        np.minimum.at(nearest, tgt[~mask], d)
    for batch in world.launching:
        if batch.owner == faction:
            mine[batch.target] += batch.left
    for owner, _, target, count in world.pending:
        if owner == faction:
            mine[target] += count
    return mine, theirs, nearest


def _take_ships(sources, sendable, want):
    """Collect `want` ships from the nearest sources first. Returns [(node, amount)] or None if there are too few."""
    chosen, total = [], 0
    for i in sources:
        amount = min(sendable[i], want - total)
        if amount > 0:
            chosen.append((i, amount))
            total += amount
        if total >= want:
            return chosen
    return None


def ai_think(world, faction, difficulty, rng):
    """Decide what `faction` should send right now. `difficulty` is an index (0/1/2) or a name."""
    name = DIFFICULTIES[difficulty] if isinstance(difficulty, int) else difficulty
    cfg = AI_TABLE[name]
    nodes = world.nodes
    own = world.owned(faction)
    if not own:
        return []
    mine, theirs, nearest = _ships_heading_to(world, faction)
    # 1. How many ships may each node send? Everything above the reserve it keeps at home.
    sendable = {i: int(math.floor(nodes[i].garrison * (1.0 - cfg["reserve"]))) for i in own}
    left = {i: nodes[i].garrison for i in own}          # garrison remaining as the orders are carried out in turn
    orders, missions = [], 0

    def send(chosen, target):
        for i, amount in chosen:
            sendable[i] -= amount
            fraction = min(1.0, (amount + 0.5) / left[i])              # +0.5: world.order() rounds down
            left[i] -= amount
            orders.append((i, target, fraction))

    # 2. Defend (NORMAL and up): if more enemy ships are flying at one of our nodes than it can
    #    hold (garrison + what it produces until they arrive), help from the nearest other node first.
    attackers = set()                                                  # factions that are flying ships at us
    for i in own:
        attackers.update(int(f) for f in np.flatnonzero(theirs[i]) if f != NEUTRAL)
    if cfg["defends"]:
        for i in own:
            enemy = theirs[i].sum()
            if enemy <= 0 or missions >= cfg["max_orders"]:
                continue
            beats = nearest[i] / _per_beat()
            holding = nodes[i].garrison + nodes[i].production * beats + mine[i]
            if enemy > holding:
                helpers = sorted((j for j in own if j != i), key=lambda j: _dist(nodes[i], nodes[j]))
                chosen = _take_ships(helpers, sendable, int(math.ceil(enemy - holding)) + 2)
                if chosen:
                    send(chosen, i)
                    missions += 1

    # 3. Score every node we do not own: big, cheap and close targets look best.
    weakest = {}                                                       # EXTREME: the weakest node of each attacker
    if cfg["counter"]:
        for f in attackers:
            theirs_nodes = world.owned(f)
            if theirs_nodes:
                weakest[min(theirs_nodes, key=lambda j: nodes[j].garrison)] = 1.5
    candidates = []
    for t, node in enumerate(nodes):
        if node.owner == faction:
            continue
        nearest_own = min(own, key=lambda j: _dist(nodes[j], node))
        distance = _dist(nodes[nearest_own], node)
        needed = node.garrison * node.shield - mine[t]                 # what we already sent counts (a fortress: more per defender)
        if node.owner != NEUTRAL:
            needed += (float(theirs[t][node.owner]) + node.production * distance / _per_beat()) * node.shield   # defender's help + its production
        if mine[t] > 0 and needed <= 0:
            continue                                                   # enough ships are already on the way
        needed = max(needed, 1.0)
        value = node.size * 3 + (8 if node.owner == NEUTRAL else 4) + (4 if node.kind == NODE_FACTORY else 0)   # factories are worth more
        score = value / (needed + 4 + distance / 90)
        if cfg["counter"] and world.has_player and node.owner == PLAYER:
            score *= AI_PLAYER_BIAS_EXTREME
        score *= weakest.get(t, 1.0)
        candidates.append((score + rng.uniform(0, 1e-6), t, needed))   # the tiny random number only breaks ties
    candidates.sort(reverse=True)

    # 4. Attack with the best target we can afford; stop after max_orders missions.
    for _, t, needed in candidates:
        if missions >= cfg["max_orders"]:
            break
        node = nodes[t]
        sources = sorted((j for j in own if sendable[j] > 0), key=lambda j: _dist(nodes[j], node))
        chosen = _take_ships(sources, sendable, int(math.ceil(needed * AI_SURPLUS + AI_SURPLUS_FLAT)))
        if chosen:
            send(chosen, t)
            missions += 1
    return orders

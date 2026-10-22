"""tests/test_ai.py - the computer opponents: legal orders, reserves, defence, and a repeatable AI-vs-AI match."""
import copy

import numpy as np

import helpers
from helpers import check
from config import AI_TABLE, DIFFICULTIES, MATCH_LIMIT_SECONDS, DT
from core.ai import ai_think
from core.node import Node
from core.world import World


def play(world, beats):
    for _ in range(beats * 30):
        world.tick()


def run():
    # --- legal orders at many moments of a real match, for every difficulty
    for d, name in enumerate(DIFFICULTIES):
        w = World(seed=4, n_factions=3, map_size=1, has_player=False)
        w.add_opponents(d)
        reserve = AI_TABLE[name]["reserve"]
        max_orders = AI_TABLE[name]["max_orders"]
        legal = reserve_ok = missions_ok = True
        for _ in range(40):
            play(w, 3)
            if w.over:
                break
            for f in w.factions():
                if f in w.eliminated:
                    continue
                orders = ai_think(w, f, d, np.random.default_rng(1))
                mine = set(w.owned(f))
                legal &= all(s in mine and 0 <= t < len(w.nodes) and s != t and 0 < frac <= 1.0 for s, t, frac in orders)
                missions_ok &= len({t for _, t, _ in orders}) <= max_orders
                before = {i: w.nodes[i].garrison for i in mine}
                trial = copy.deepcopy(w)                   # carry the orders out on a copy, the real match is untouched
                for s, t, frac in orders:
                    trial.order([s], t, frac, f)
                reserve_ok &= all(trial.nodes[i].garrison >= before[i] * reserve - 1e-6 for i in mine)
        check(legal, f"{name}: orders only from owned nodes, to real other nodes, fraction in (0, 1]")
        check(reserve_ok, f"{name}: never sends below its home reserve ({int(reserve * 100)}%)")
        check(missions_ok, f"{name}: at most {max_orders} missions per think")
    check(ai_think(w, 1, "EXTREME", np.random.default_rng(1)) is not None, "difficulty can be given by name")

    # --- a faction with nothing to command returns no orders
    w = World(seed=4, n_factions=2, map_size=1, has_player=False)
    for n in w.nodes:
        if n.owner == 2:
            n.owner = 1
    check(ai_think(w, 2, 1, np.random.default_rng(1)) == [], "no nodes = no orders")

    # --- it grabs a cheap neutral first
    nodes = [Node(200, 500, 3, owner=2, garrison=40), Node(500, 500, 2, owner=0, garrison=6),
             Node(900, 500, 3, owner=0, garrison=60), Node(1700, 500, 3, owner=1, garrison=30)]
    w = World(seed=1, n_factions=2, nodes=nodes, has_player=False)
    orders = ai_think(w, 2, 1, np.random.default_rng(1))
    check(orders and orders[0][1] == 1, "the first target is the cheap, close neutral node")

    # --- defence: 40 enemy ships are flying at a weak node while a strong node stands next to it
    def defence_world():
        nodes = [Node(200, 500, 2, owner=2, garrison=5), Node(400, 700, 3, owner=2, garrison=60),
                 Node(1500, 500, 3, owner=1, garrison=30), Node(1700, 300, 1, owner=0, garrison=50)]
        w = World(seed=1, n_factions=2, nodes=nodes, has_player=False)
        w.ships.launch(1, w.nodes[2], 0, w.nodes[0], 40, np.random.default_rng(2))
        for _ in range(60):                                # let the swarm get closer
            w.ships.pos += w.ships.vel / 60
        return w
    help_orders = [o for o in ai_think(defence_world(), 2, "NORMAL", np.random.default_rng(1)) if o[1] == 0]
    check(help_orders and help_orders[0][0] == 1, "NORMAL sends help from the strong node to the threatened one")
    easy_help = [o for o in ai_think(defence_world(), 2, "EASY", np.random.default_rng(1)) if o[1] == 0]
    check(not easy_help, "EASY does not react to attacks")

    # --- it does not pile on a target it already has ships flying to
    nodes = [Node(200, 500, 3, owner=2, garrison=80), Node(600, 500, 1, owner=0, garrison=10),
             Node(1700, 500, 3, owner=1, garrison=30)]
    w = World(seed=1, n_factions=2, nodes=nodes, has_player=False)
    w.ships.launch(2, w.nodes[0], 1, w.nodes[1], 25, np.random.default_rng(2))
    check(all(o[1] != 1 for o in ai_think(w, 2, "EXTREME", np.random.default_rng(1))), "no extra ships to a target that has enough on the way")

    # --- AI vs AI: finishes, and is repeatable (same seed = same winner and tick count)
    results = []
    for _ in range(2):
        w = World(seed=1, n_factions=2, map_size=1, has_player=False)
        w.add_opponents(1)
        while not w.over:
            w.tick()
        results.append((w.winner, w.ticks))
    check(results[0] == results[1], f"AI vs AI is deterministic: {results[0]} == {results[1]}")
    check(w.over and w.winner in (1, 2) and w.stats.match_ticks <= MATCH_LIMIT_SECONDS / DT + 1,
          "AI vs AI (seed 1, NORMAL) ends with a winner within 12 sim-minutes")
    # EXTREME vs EXTREME ends decisively (somebody is eliminated) well before the 12-minute safety rule
    w = World(seed=1, n_factions=2, map_size=1, has_player=False)
    w.add_opponents(DIFFICULTIES.index("EXTREME"))
    while not w.over:
        w.tick()
    check(w.eliminated and w.seconds < MATCH_LIMIT_SECONDS - 60, f"EXTREME vs EXTREME ends by elimination ({w.seconds:.0f} s)")

    # the difficulty levels really differ: the stronger AI wins every match (3 maps, sides swapped)
    def duel(strong, weak, seed, swap):
        w = World(seed=seed, n_factions=2, map_size=1, has_player=False)
        w.add_opponents(1)
        a, b = (weak, strong) if swap else (strong, weak)
        w.opponents[1].difficulty, w.opponents[2].difficulty = DIFFICULTIES.index(a), DIFFICULTIES.index(b)
        while not w.over:
            w.tick()
        return w.winner == (2 if swap else 1)
    for strong, weak in (("EXTREME", "HARD"), ("HARD", "NORMAL"), ("NORMAL", "EASY")):
        check(all(duel(strong, weak, seed, swap) for seed in (1, 2, 3) for swap in (False, True)),
              f"{strong} beats {weak} in 6 of 6 matches")
    think = [AI_TABLE[name]["think_every"] for name in DIFFICULTIES]
    check(think == sorted(think, reverse=True) and len(set(think)) == len(think), "the harder the AI, the more often it thinks")
    check(DIFFICULTIES == ("EASY", "NORMAL", "HARD", "EXTREME"), "four levels, HARD sits between NORMAL and EXTREME")
    check(AI_TABLE["HARD"]["max_orders"] <= AI_TABLE["EXTREME"]["max_orders"] and not AI_TABLE["HARD"]["counter"] and AI_TABLE["EXTREME"]["counter"],
          "HARD does not counter-attack and plays fewer missions than EXTREME")
    print(f"    AI vs AI seed 1 NORMAL: faction {results[0][0]} wins after {results[0][1] * DT:.0f} s of game time")


if __name__ == "__main__":
    run()
    raise SystemExit(0 if helpers.report("test_ai") else 1)

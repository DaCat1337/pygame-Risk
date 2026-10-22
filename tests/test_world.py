"""tests/test_world.py - production, orders, arrival, capture, elimination and win/lose."""
import helpers
from helpers import check
from config import MATCH_LIMIT_SECONDS, DT
from config import apply_pace
from core.node import Node
from core.world import World


def tiny_world(**kw):
    """A hand-made map: A (player), B (neutral) in the middle, C (computer) far away."""
    nodes = [Node(300, 500, 2, owner=1, garrison=10),      # 0 = A
             Node(800, 500, 1, owner=0, garrison=5),       # 1 = B
             Node(1600, 500, 2, owner=2, garrison=10)]     # 2 = C
    return World(seed=1, n_factions=2, nodes=nodes, **kw)


def run_ticks(world, n):
    for _ in range(n):
        world.tick()


def run():
    apply_pace(0)                                           # the rules are tested with the original SHORT pace (the game's default is LONG)
    # --- production happens on the beat only
    w = tiny_world()
    w.tick()                                               # tick 0 is a beat tick
    check(w.nodes[0].garrison == 12, "owned size-2 node gains 2 on the beat")
    check(w.nodes[1].garrison == 5, "neutral node never grows")
    run_ticks(w, 29)
    check(w.nodes[0].garrison == 12, "nothing grows between beats")
    w.tick()                                               # tick 30
    check(w.nodes[0].garrison == 14, "and again on the next beat")
    w.nodes[0].garrison = w.nodes[0].cap - 1
    run_ticks(w, 30)
    check(w.nodes[0].garrison == w.nodes[0].cap, "production stops at the cap")
    run_ticks(w, 30)
    check(w.nodes[0].garrison == w.nodes[0].cap, "...and stays there")

    # --- events
    w = tiny_world()
    w.tick()
    ev = w.drain_events()
    check(("beat", 0) in ev and ("step", 0) in ev, "tick 0 emits beat 0 and step 0")
    check(w.drain_events() == [], "events are handed over only once")

    # --- orders: garrison drops now, ships appear on the next beat, all out within one more beat
    w = tiny_world()
    run_ticks(w, 6)                                        # ticks 0..5 done, garrison is 12
    check(w.order([0], 1, 0.5, 1) == 6, "50% of 12 = 6 ships ordered")
    check(w.nodes[0].garrison == 6, "garrison drops immediately")
    run_ticks(w, 20)                                       # up to tick 25
    check(w.ships.count() == 0, "no ships before the next beat")
    run_ticks(w, 5)                                        # ticks 26..30 -> tick 30 (the beat) has run
    check(w.ships.count() >= 1, "ships appear on the next beat")
    run_ticks(w, 30)
    check(w.ships.count() == 6, "all 6 ships are out within one more beat")
    check(("launch", 1, 6) in w.events and ("order", 1, 6) in w.events, "order and launch events exist")
    check(w.order([2], 1, 0.5, 1) == 0, "cannot order from a node you do not own")
    check(w.order([1], 0, 0.5, 1) == 0, "cannot order from a neutral node")
    w2 = tiny_world()
    check(w2.order([0], 1, 1.0, 1) == 10 and w2.nodes[0].garrison == 0, "100% leaves 0")
    check(w2.order([0], 1, 1.0, 1) == 0, "an empty node cannot send")
    w3 = tiny_world()
    w3.nodes[0].garrison = 2
    check(w3.order([0], 1, 0.25, 1) == 1, "a small garrison still sends at least 1 ship")
    check(w3.order([0], 0, 1.0, 1) == 0, "cannot send a node to itself")

    # --- arrival: reinforce / attack / overflow captures with the right leftover
    w = tiny_world()
    w._land(1, 0)
    check(w.nodes[0].garrison == 11, "an own ship reinforces")
    for _ in range(5):
        w._land(1, 1)
    check(w.nodes[1].garrison == 0 and w.nodes[1].owner == 0, "5 attackers cancel a garrison of 5")
    w.drain_events()
    w._land(1, 1)
    check(w.nodes[1].owner == 1 and w.nodes[1].garrison == 1, "the 6th ship captures the node, leftover 1")
    check(("capture", 1, 0, 1) in w.drain_events(), "a capture event fires")
    w._land(2, 1)
    check(w.nodes[1].owner == 1 and w.nodes[1].garrison == 0, "an enemy ship attacks an owned node")

    # --- a whole attack in flight: 20 ships vs a garrison of 5 -> captured, 15 left
    w = tiny_world()
    w.nodes[1].garrison = 5
    w.nodes[0].garrison = 20
    w.nodes[0].cap = w.nodes[1].cap = 0                    # production off while we measure
    w.order([0], 1, 1.0, 1)
    seen_capture = False
    for _ in range(400):
        w.tick()
        seen_capture |= any(e[0] == "capture" for e in w.drain_events())
    check(seen_capture and w.nodes[1].owner == 1, "20 ships capture a neutral node with garrison 5")
    check(w.nodes[1].garrison == 15, "...and the 15 survivors become its garrison")

    # --- countdown
    w = World(seed=1, n_factions=2, countdown_beats=3, nodes=tiny_world().nodes)
    run_ticks(w, 89)
    check(w.nodes[0].garrison == 10, "no production during the 3-2-1 countdown")
    check(w.order([0], 1, 0.5, 1) == 0, "no orders during the countdown")
    check(w.countdown_number() == 1, "countdown shows 1 at the end")
    run_ticks(w, 2)
    check(w.live and w.nodes[0].garrison == 12, "production starts right after the countdown")

    # --- elimination and win / lose
    w = tiny_world()
    w.nodes[2].owner = 1
    w.tick()
    ev = w.drain_events()
    check(("eliminated", 2) in ev and ("win", 1) in ev, "faction 2 loses its last node: eliminated + player wins")
    check(w.over and w.result == "win" and w.winner == 1, "world is over, result win")
    w = tiny_world()
    w.nodes[0].owner = 2
    w.tick()
    ev = w.drain_events()
    check(("eliminated", 1) in ev and ("lose", 1) in ev and w.result == "lose", "player without nodes loses")
    w = tiny_world()
    w.nodes[0].owner = 2
    w.ships.launch(1, w.nodes[1], 2, w.nodes[2], 3, w.rng)
    w.tick()
    check(not w.over, "ships in flight keep a faction alive")
    w = tiny_world(has_player=False)
    w.nodes[0].owner = 2
    w.tick()
    check(w.over and w.winner == 2, "watch mode: the last faction standing wins")
    w = tiny_world()
    w.stats.match_ticks = int(MATCH_LIMIT_SECONDS / DT) - 1
    w.nodes[0].garrison = 3
    w.tick()
    check(w.over, "after 12 minutes the match ends")

    # --- flight cap: a faction never has more than 1200 ships in the air
    w = tiny_world()
    w.nodes[0].garrison = 5000
    w.nodes[0].cap = 6000
    for _ in range(3):
        w.order([0], 1, 0.5, 1)
        run_ticks(w, 60)
    check(int(w.ships.count_by_owner()[1]) <= 1200, "flight cap of 1200 per faction")


if __name__ == "__main__":
    run()
    raise SystemExit(0 if helpers.report("test_world") else 1)

"""core/world.py - the game rules in one place: the World advances one tick at a time.

What it is for : owns the nodes, the ships and the clock; applies production on the beat,
                 launch orders, arrivals, captures, elimination and the win/lose decision.
Uses            : config.py, core/beat.py, core/mapgen.py, core/ships.py, core/combat.py,
                 core/stats.py, core/ai.py.
Used by         : game.py, ui/, graphics/ (they only READ the world), tests.

The server-style rule: the screen only ASKS (world.order); the World decides what happens.
Nothing here imports pygame, so the whole game can be played in a test without a window.

Time: world.tick() is called 60 times per simulated second. Beats come from the tick
counter (core/beat.py), never from the wall clock, so a match is fully reproducible.
Whatever happens is reported as an "event" tuple in world.events (game.py drains them):
  ("beat", b) ("step", s) ("order", owner, n) ("launch", owner, n) ("clash", x, y, n, a, b)
  ("capture", node_index, old_owner, new_owner) ("eliminated", f) ("win", f) ("lose", f)
"""
import math
from dataclasses import dataclass

import numpy as np

from config import (TICKS_PER_BEAT, MATCH_LIMIT_SECONDS, STATS_EVERY_BEATS, PLAYER, DT, SHIP_SPEED, BEAT,
                    AI_TABLE, DIFFICULTIES)
from core.ai import ai_think, Opponent
from core.beat import beat_of, is_beat_tick, is_step_tick, step_of
from core.combat import resolve_clashes
from core.mapgen import generate_map
from core.ships import Ships
from core.stats import Stats


@dataclass
class Launch:
    """A batch of ships that is streaming out of a node (spread over one beat)."""
    owner: int
    source: int
    target: int
    left: int           # ships still to emit
    per_tick: int       # how many to emit each tick


class World:
    def __init__(self, seed=1, n_factions=2, map_size=1, countdown_beats=0, has_player=True, nodes=None):
        self.seed = seed
        self.n_factions = n_factions
        self.map_size = map_size
        self.has_player = has_player                      # False = "watch AI battle": every faction is a computer
        # `nodes` lets a test hand in a tiny hand-made map instead of a generated one
        self.nodes = nodes if nodes is not None else generate_map(seed, n_factions, map_size)
        self.node_xy = np.array([(n.x, n.y) for n in self.nodes], dtype=np.float32)
        self.node_r = np.array([n.radius for n in self.nodes], dtype=np.float32)
        self.ships = Ships()
        self.rng = np.random.default_rng(seed + 777)      # only used for ship lane offsets
        self.stats = Stats(n_factions)
        self.ticks = 0
        self.countdown_ticks = countdown_beats * TICKS_PER_BEAT   # clock runs, but nothing happens yet
        self.events = []
        self.pending = []           # orders waiting for the next beat: (owner, source, target, n)
        self.launching = []         # Launch batches currently streaming out
        self.eliminated = set()
        self.over = False
        self.result = None          # "win", "lose" or None while running
        self.winner = 0
        self.opponents = {}         # faction -> Opponent (core/ai.py); filled by add_opponents()

    # ------------------------------------------------------------------ small questions
    @property
    def live(self):
        """False during the 3-2-1 countdown."""
        return self.ticks >= self.countdown_ticks

    @property
    def seconds(self):
        """Match time in seconds (after the countdown)."""
        return max(0, self.ticks - self.countdown_ticks) * DT

    def countdown_number(self):
        """3, 2, 1 during the countdown, 0 afterwards."""
        if self.live:
            return 0
        return math.ceil((self.countdown_ticks - self.ticks) / TICKS_PER_BEAT)

    def factions(self):
        """All faction numbers: 1..n."""
        return range(1, self.n_factions + 1)

    def alive_factions(self):
        """Factions that have not been eliminated yet (these play the beat voices)."""
        return [f for f in self.factions() if f not in self.eliminated]

    def owned(self, faction):
        """Indices of the nodes this faction owns."""
        return [i for i, n in enumerate(self.nodes) if n.owner == faction]

    def ship_totals(self):
        """Array: per faction, all its ships = garrisons + flying + still queued to launch."""
        totals = np.zeros(self.n_factions + 1)
        for node in self.nodes:
            totals[node.owner] += node.garrison
        totals += self.ships.count_by_owner(self.n_factions + 1)[:self.n_factions + 1]
        for batch in self.launching:
            totals[batch.owner] += batch.left
        for owner, _, _, n in self.pending:
            totals[owner] += n
        return totals

    def shares(self):
        """Each faction's share (0..1) of all faction ships: drives the power bar and music volume."""
        totals = self.ship_totals()[1:]
        whole = totals.sum()
        return totals / whole if whole > 0 else np.full(self.n_factions, 1.0 / self.n_factions)

    def needed_to_capture(self, target, sources):
        """Rough number of ships needed to take `target`: its garrison + 1, plus what an ENEMY node
        produces while our ships are flying there (only neutral nodes stand still). Shown as "needs ~N"."""
        node = self.nodes[target]
        need = node.garrison + 1
        if node.owner != 0 and sources:
            nearest = min(math.hypot(node.x - self.nodes[s].x, node.y - self.nodes[s].y) for s in sources)
            need += node.production * nearest / (SHIP_SPEED * BEAT)
        return int(math.ceil(need))

    def drain_events(self):
        """Hand over (and forget) the events collected since the last call."""
        out, self.events = self.events, []
        return out

    # ------------------------------------------------------------------ orders
    def order(self, sources, target, fraction, owner):
        """Send `fraction` of the garrison of each source node to `target`.

        The ships leave the garrison NOW (so the numbers on screen are honest) but only start
        flying on the next beat. Returns the number of ships ordered (0 = nothing happened).
        """
        if self.over or not self.live or not (0 <= target < len(self.nodes)):
            return 0
        total = 0
        for s in sources:
            if s == target or not (0 <= s < len(self.nodes)):
                continue
            node = self.nodes[s]
            if node.owner != owner or node.garrison < 1:
                continue                                   # you can only command what you own
            n = max(1, int(math.floor(node.garrison * fraction)))
            node.garrison -= n
            self.pending.append((owner, s, target, n))
            total += n
        if total:
            self.events.append(("order", owner, total))
        return total

    # ------------------------------------------------------------------ the tick
    def tick(self):
        """Advance the world by 1/60 s."""
        t = self.ticks
        if is_step_tick(t):
            self.events.append(("step", step_of(t)))
        if is_beat_tick(t):
            self.events.append(("beat", beat_of(t)))
        if self.over:                                      # decided: only the metronome keeps going (the winner's
            self.ticks += 1                                # instrument plays the final fanfare), nothing else moves
            return
        if self.live:
            if is_beat_tick(t):
                self._on_beat(beat_of(t))
            self._emit_launches()
            self._move_ships(t)
            self.stats.match_ticks += 1
            self._check_end()
        self.ticks += 1

    def _on_beat(self, beat):
        """Everything that happens exactly on the beat."""
        # 1. orders given since the last beat start streaming out now
        launched = {}
        for owner, source, target, n in self.pending:
            self.launching.append(Launch(owner, source, target, n, math.ceil(n / TICKS_PER_BEAT)))
            launched[owner] = launched.get(owner, 0) + n
            self.stats.launched[owner] += n
        self.pending = []
        for owner, n in launched.items():
            self.events.append(("launch", owner, n))
        # 2. production: owned nodes grow by their size (neutral nodes never produce)
        for node in self.nodes:
            if node.owner != 0 and node.garrison < node.cap:
                node.garrison = min(node.cap, node.garrison + node.production)
        # 3. the computer opponents think (they use order(), exactly like the player)
        self._run_opponents(beat)
        # 4. bookkeeping for the graph
        if beat % STATS_EVERY_BEATS == 0:
            self.stats.snapshot(self.ticks, self.ship_totals())
        counts = [0] * (self.n_factions + 1)
        for node in self.nodes:
            counts[node.owner] += 1
        self.stats.note_nodes(counts)

    def add_opponents(self, difficulty):
        """Make every faction except the human player a computer opponent (all of them in watch mode).
        Each gets its own dice, seeded from the match seed, so a match is repeatable."""
        self.opponents = {}
        for f in self.factions():
            if f != PLAYER or not self.has_player:
                self.opponents[f] = Opponent(difficulty, np.random.default_rng(self.seed + f))

    def _run_opponents(self, beat):
        """Each opponent thinks every N beats (N depends on the difficulty). It only asks via order()."""
        for f, opp in self.opponents.items():
            if f in self.eliminated:
                continue
            cfg = AI_TABLE[DIFFICULTIES[opp.difficulty]]
            if beat < cfg["start_delay"]:
                continue                                   # a slow starter gives you a head start
            if (beat + f) % cfg["think_every"] == 0:       # "+ f" so the factions do not all think on the same beat
                for source, target, fraction in ai_think(self, f, opp.difficulty, opp.rng):
                    self.order([source], target, fraction, f)

    def _emit_launches(self):
        """Let ships out of the nodes: ceil(n/30) per tick, so a batch is out within one beat."""
        for batch in self.launching:
            k = min(batch.per_tick, batch.left)
            source, target = self.nodes[batch.source], self.nodes[batch.target]
            made = self.ships.launch(batch.owner, source, batch.target, target, k, self.rng)
            if made < k and source.owner == batch.owner:
                source.garrison += k - made                # flight cap reached: give the rest back
            batch.left -= k
        self.launching = [b for b in self.launching if b.left > 0]

    def _move_ships(self, t):
        """Fly, fight in mid-air, then land."""
        arrived = self.ships.step(self.node_xy, self.node_r)
        for i in arrived:
            self._land(int(self.ships.owner[i]), int(self.ships.target[i]))
        self.ships.kill(arrived)
        records, killed = resolve_clashes(self.ships, t)
        for x, y, n, a, b in records:
            self.events.append(("clash", x, y, n, a, b))
        for f in range(1, self.n_factions + 1):
            self.stats.lost[f] += int(killed[f])

    def _land(self, owner, target):
        """One ship reaches a node: reinforce it, or fight the garrison (and maybe capture it)."""
        node = self.nodes[target]
        if node.owner == owner:
            node.garrison += 1
            return
        node.garrison -= 1
        self.stats.lost[owner] += 1
        if node.owner != 0:
            self.stats.lost[node.owner] += 1               # a defender fell too
        if node.garrison < 0:                              # overflow: the node flips
            old = node.owner
            node.owner = owner
            node.garrison = abs(node.garrison)             # the ship that broke through stays as garrison
            self.stats.captured[owner] += 1
            self.events.append(("capture", target, old, owner))

    # ------------------------------------------------------------------ the end of a match
    def _has_forces(self, f):
        """Does faction f still own a node, a flying ship or a queued ship?"""
        if any(n.owner == f for n in self.nodes):
            return True
        if np.count_nonzero(self.ships.alive & (self.ships.owner == f)):
            return True
        return any(b.owner == f and b.left > 0 for b in self.launching) or any(p[0] == f for p in self.pending)

    def _check_end(self):
        for f in self.factions():
            if f not in self.eliminated and not self._has_forces(f):
                self.eliminated.add(f)
                self.events.append(("eliminated", f))
        remaining = self.alive_factions()
        if self.has_player and PLAYER in self.eliminated:
            self.winner = self._strongest(remaining)
            self._finish("lose", PLAYER)
        elif len(remaining) <= 1:
            self.winner = remaining[0] if remaining else 0
            self._finish("win", self.winner)
        elif self.stats.match_ticks >= MATCH_LIMIT_SECONDS / DT:
            self.winner = self._strongest(remaining)       # time is up: most nodes, then most ships
            lost = self.has_player and self.winner != PLAYER
            self._finish("lose" if lost else "win", PLAYER if lost else self.winner)

    def _strongest(self, factions):
        totals = self.ship_totals()
        return max(factions, key=lambda f: (len(self.owned(f)), totals[f]), default=0)

    def _finish(self, result, faction):
        self.over = True
        self.result = result
        self.events.append((result, faction))
        self.stats.snapshot(self.ticks, self.ship_totals())

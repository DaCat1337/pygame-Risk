"""core/ships.py - thousands of tiny ships stored as NumPy arrays.

What it is for : the Ships class keeps every ship's position, velocity, owner and target in
                 big arrays ("structure of arrays"), so moving 2000 ships is a few array
                 operations instead of 2000 Python loops.
Uses            : config.py, numpy.
Used by         : core/world.py, core/combat.py, graphics/draw_ships.py.

Analogy: instead of 2000 little notebooks (one object per ship), keep ONE spreadsheet with
2000 rows. Doing "x += speed" to a whole column is one fast operation.
A ship slot is reused when `alive` is False (a "free slot").
"""
import math

import numpy as np

from config import MAX_SHIPS, MAX_FLIGHT_PER_FACTION, SHIP_SPEED, LANE_SPREAD, DT


class Ships:
    def __init__(self, capacity=MAX_SHIPS):
        self.pos = np.zeros((capacity, 2), dtype=np.float32)
        self.vel = np.zeros((capacity, 2), dtype=np.float32)
        self.owner = np.zeros(capacity, dtype=np.int8)
        self.target = np.zeros(capacity, dtype=np.int16)      # index of the node it is flying to
        self.alive = np.zeros(capacity, dtype=bool)

    def count(self):
        """How many ships are flying."""
        return int(self.alive.sum())

    def count_by_owner(self, n_owners=5):
        """Array: ships in flight per owner (index = faction number)."""
        return np.bincount(self.owner[self.alive], minlength=n_owners)

    def room_for(self, owner):
        """How many more ships this faction may launch (faction cap and free array slots)."""
        flying = int(np.count_nonzero(self.alive & (self.owner == owner)))
        free = len(self.alive) - self.count()
        return max(0, min(MAX_FLIGHT_PER_FACTION - flying, free))

    def launch(self, owner, source, target_index, target, k, rng, speed_mult=1.0):
        """Create up to k ships on the rim of `source`, flying towards `target` (speed_mult 1.5 = a relay's faster ships).

        Each ship gets a small fixed sideways "lane offset" (up to 0.6 x the target's radius)
        so a swarm looks like a stream with some width, not a single line. The ship flies
        straight to its aim point and does not steer around other nodes (simple, looks fine).
        Returns how many were really created (the caller refunds the rest).
        """
        k = min(k, self.room_for(owner))
        if k <= 0:
            return 0
        slots = np.flatnonzero(~self.alive)[:k]
        dx, dy = target.x - source.x, target.y - source.y
        dist = math.hypot(dx, dy) or 1.0
        ux, uy = dx / dist, dy / dist                        # unit vector source -> target
        lane = rng.uniform(-LANE_SPREAD, LANE_SPREAD, k) * target.radius
        aim_x = target.x - uy * lane                         # aim point = target centre pushed sideways
        aim_y = target.y + ux * lane
        vx, vy = aim_x - source.x, aim_y - source.y
        norm = np.hypot(vx, vy)
        vx, vy = vx / norm, vy / norm                        # unit direction of each ship
        back = rng.uniform(0.0, SHIP_SPEED * DT, k)          # spawned somewhere inside this tick: no clumps
        self.pos[slots, 0] = source.x + vx * (source.radius - back)
        self.pos[slots, 1] = source.y + vy * (source.radius - back)
        self.vel[slots, 0] = vx * SHIP_SPEED * speed_mult
        self.vel[slots, 1] = vy * SHIP_SPEED * speed_mult
        self.owner[slots] = owner
        self.target[slots] = target_index
        self.alive[slots] = True
        return k

    def step(self, node_xy, node_r):
        """Move every ship one tick. Returns the indices of ships that reached their target node.

        node_xy is an (M, 2) array of node centres and node_r an (M,) array of radii.
        """
        idx = np.flatnonzero(self.alive)
        if len(idx) == 0:
            return idx
        self.pos[idx] += self.vel[idx] * DT
        tgt = self.target[idx]
        d = self.pos[idx] - node_xy[tgt]
        inside = (d[:, 0] ** 2 + d[:, 1] ** 2) <= node_r[tgt] ** 2
        return idx[inside]

    def kill(self, indices):
        """Remove ships (their slots become free again)."""
        self.alive[indices] = False

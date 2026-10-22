"""core/combat.py - ships of different owners annihilate each other in mid-air.

What it is for : resolve_clashes(ships, tick) removes enemy ships that meet and reports where.
Uses            : config.py, core/ships.py (only its arrays), numpy.
Used by         : core/world.py.

Analogy - "only check people in the same room for a fight":
checking every ship against every other would be 2000 x 2000 = 4 million pairs per tick.
Instead we cut the screen into small square "rooms" (grid cells, 21 px). Ships are sorted
into rooms, and only a room that contains ships of 2+ different owners has a fight.
In such a room every owner loses the same number of ships: the size of the SMALLEST group
(3 cyan vs 5 magenta -> 3 of each die, 2 magenta survive). One-for-one, like a trade.

Problem: two enemies on either side of a wall between rooms are never in the same room.
Fix: on odd ticks we shift the whole grid by half a cell, so those pairs meet next tick.
"""
import numpy as np

from config import CLASH_CELL

_STRIDE = 64          # cell number = column * 64 + row (the screen has fewer than 64 rows of cells)
_OWNER_SLOTS = 8      # key = cell * 8 + owner, so sorting keys groups by cell, then by owner


def resolve_clashes(ships, tick):
    """Kill enemy ships that share a cell. Returns (records, killed_per_owner).

    records: one tuple per fighting cell: (x, y, ships_killed, owner_a, owner_b)
             - x, y is the middle of the dead ships, a and b are the first two owners involved.
    killed_per_owner: array, index = faction number.
    """
    killed_per_owner = np.zeros(8, dtype=np.int64)
    idx = np.flatnonzero(ships.alive)
    if len(idx) < 2:
        return [], killed_per_owner
    pos = ships.pos[idx]
    owner = ships.owner[idx].astype(np.int64)

    # 1. which room is each ship in? (grid shifted by half a cell on odd ticks)
    shift = CLASH_CELL / 2 if tick % 2 else 0.0
    col = np.maximum(((pos[:, 0] + shift) // CLASH_CELL).astype(np.int64), 0)
    row = np.maximum(((pos[:, 1] + shift) // CLASH_CELL).astype(np.int64), 0)
    key = (col * _STRIDE + row) * _OWNER_SLOTS + owner

    # 2. count ships per (room, owner). np.unique sorts the keys, so a room's groups sit together.
    group_key, inverse, counts = np.unique(key, return_inverse=True, return_counts=True)
    group_cell = group_key // _OWNER_SLOTS
    group_owner = group_key % _OWNER_SLOTS
    room_start = np.flatnonzero(np.r_[True, group_cell[1:] != group_cell[:-1]])   # first group of each room
    owners_in_room = np.diff(np.r_[room_start, len(group_cell)])
    fight = owners_in_room >= 2
    if not fight.any():
        return [], killed_per_owner

    # 3. in a fighting room every owner loses `smallest group` ships
    smallest = np.minimum.reduceat(counts, room_start)
    lose_per_group = np.repeat(np.where(fight, smallest, 0), owners_in_room)

    # 4. pick the victims: the first `lose` ships of each group (rank inside the group < lose)
    order = np.argsort(inverse, kind="stable")                # ships sorted by group
    group_first = np.cumsum(counts) - counts                  # where each group starts in that order
    rank = np.arange(len(order)) - np.repeat(group_first, counts)
    victim_sorted = rank < np.repeat(lose_per_group, counts)
    victims = order[victim_sorted]                            # positions inside idx
    if len(victims) == 0:
        return [], killed_per_owner

    # 5. one record per fighting room: average position of its dead ships
    room_of_group = np.repeat(np.arange(len(room_start)), owners_in_room)
    room_of_ship = room_of_group[inverse[victims]]
    n_rooms = len(room_start)
    dead = np.bincount(room_of_ship, minlength=n_rooms)
    sx = np.bincount(room_of_ship, weights=pos[victims, 0], minlength=n_rooms)
    sy = np.bincount(room_of_ship, weights=pos[victims, 1], minlength=n_rooms)
    records = []
    for r in np.flatnonzero(dead):
        first = room_start[r]
        records.append((float(sx[r] / dead[r]), float(sy[r] / dead[r]), int(dead[r]),
                        int(group_owner[first]), int(group_owner[first + 1])))
    killed_per_owner += np.bincount(owner[victims], minlength=8)
    ships.kill(idx[victims])
    return records, killed_per_owner

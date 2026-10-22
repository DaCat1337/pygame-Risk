"""core/stats.py - the match diary: share history for the graph and per-faction counters.

What it is for : remember what happened so the game-over screen can tell the story.
Uses            : config.py.
Used by         : core/world.py (fills it), ui/screens/gameover.py (draws it).
"""


class Stats:
    def __init__(self, n_factions):
        self.n = n_factions
        # one snapshot every 2 beats: (tick, [share of faction 1, share of faction 2, ...]) shares add up to 1
        self.history = []
        self.captured = [0] * (n_factions + 1)       # nodes captured (index = faction)
        self.launched = [0] * (n_factions + 1)       # ships sent out
        self.lost = [0] * (n_factions + 1)           # ships destroyed (in the air or at a node)
        self.peak_nodes = [0] * (n_factions + 1)     # most nodes owned at one time
        self.match_ticks = 0

    def snapshot(self, tick, ship_totals):
        """Record each faction's share of all ships. ship_totals[f] = garrisons + flying + queued."""
        totals = [float(ship_totals[f]) for f in range(1, self.n + 1)]
        whole = sum(totals)
        shares = [t / whole for t in totals] if whole > 0 else [1.0 / self.n] * self.n
        self.history.append((tick, shares))

    def note_nodes(self, owned_counts):
        """Update the peak node count. owned_counts[f] = nodes owned by faction f now."""
        for f in range(1, self.n + 1):
            self.peak_nodes[f] = max(self.peak_nodes[f], owned_counts[f])

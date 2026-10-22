"""graphics/draw_ships.py - draws up to 3000 ships as 3x3 dots with a short trail.

What it is for : the fast way to draw thousands of tiny dots.
Uses            : config.py, core/ships.py (reads its arrays), numpy, pygame.
Used by         : ui/screens/play.py.

Why not pygame.draw in a loop? 2000 draw calls per frame are slow in Python. Instead we lock
the screen as a NumPy array (surfarray) and colour ALL pixels of a faction at once with
"fancy indexing": arr[xs, ys] = colour paints every (x, y) pair in one operation.
"""
import numpy as np
import pygame

from config import SCREEN_W, SCREEN_H, FACTION_COLORS

TRAIL_SAMPLES = 8          # the trail is 8 pixels along the flight path, fading out
TRAIL_SECONDS = 0.05       # trail length = velocity * 0.05 s (about 10 px)
HALO_STRENGTH = 0.30       # brightness of the glow ring around each ship (0 = none)
HALO_RING = [(dx, dy) for dx in range(-2, 3) for dy in range(-2, 3) if max(abs(dx), abs(dy)) == 2]   # the 16 pixels of a 5x5 border


def _add_light(pixels, x, y, light):
    """Brighten the pixels at (x, y) by `light` (ADDED to what is there, like real light, capped at 255).
    Where many ships overlap, the glows add up: a dense swarm shines brighter than one ship."""
    pixels[x, y] = np.minimum(pixels[x, y].astype(np.int16) + light, 255).astype(np.uint8)


def draw_ships(surf, ships, halo=True):
    """Paint every living ship onto `surf` (it must be a 24/32-bit surface, like the screen).
    halo=False leaves out the glow ring around each ship (the bloom switch)."""
    idx = np.flatnonzero(ships.alive)
    if len(idx) == 0:
        return
    pixels = pygame.surfarray.pixels3d(surf)              # a live view: writing to it draws on the surface
    try:
        owners = ships.owner[idx]
        for owner in np.unique(owners):
            sel = idx[owners == owner]
            pos, vel = ships.pos[sel], ships.vel[sel]
            base = np.array(FACTION_COLORS[int(owner)], dtype=np.float32)
            for k in range(TRAIL_SAMPLES, 0, -1):          # far end of the trail first, so the near end wins
                f = k / TRAIL_SAMPLES
                p = pos - vel * (TRAIL_SECONDS * f)
                x = np.clip(p[:, 0].astype(np.int32), 0, SCREEN_W - 1)
                y = np.clip(p[:, 1].astype(np.int32), 0, SCREEN_H - 1)
                pixels[x, y] = (base * (1.0 - f) * 0.7).astype(np.uint8)
            x = np.clip(pos[:, 0].astype(np.int32), 2, SCREEN_W - 3)
            y = np.clip(pos[:, 1].astype(np.int32), 2, SCREEN_H - 3)
            light = (base * HALO_STRENGTH).astype(np.int16)
            for dx, dy in (HALO_RING if halo else ()):
                _add_light(pixels, x + dx, y + dy, light)           # soft glow first, the solid dot goes on top
            body = base.astype(np.uint8)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    pixels[x + dx, y + dy] = body
            pixels[x, y] = (base + (255 - base) * 0.55).astype(np.uint8)    # bright core
    finally:
        del pixels                                         # unlock the surface again

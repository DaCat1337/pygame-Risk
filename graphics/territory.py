"""graphics/territory.py - a very faint colour glow that shows who controls which part of the map.

What it is for : every owned node casts a soft pool of its owner's colour onto the black sky, like a lamp.
                 Where two pools meet the colours simply mix (no hard border). Neutral nodes cast nothing.
Uses            : config.py, numpy, pygame.
Used by         : ui/screens/play.py (WorldView).

Three things keep it smooth (an earlier version looked blocky):
  1. No hard borders: each node's light fades out gently (a bell curve), and lights ADD up.
  2. Dithering: at 10% brightness there are only ~25 grey levels, which shows as visible steps ("banding").
     Adding a tiny fixed random noise BEFORE rounding to whole numbers hides the steps, like newspaper print.
  3. When a node changes hands, the glow cross-fades to the new picture (0.8 s) instead of popping.
It is worked out on a 480 x 270 grid (one cell = 4 x 4 pixels) and enlarged with pygame's smoothscale.
"""
import numpy as np
import pygame

from config import SCREEN_W, SCREEN_H, FACTION_COLORS

CELLS_X, CELLS_Y = 480, 270
STRENGTH = 0.08                 # brightest the glow gets: 8% of the faction colour
REACH = 210.0                   # pixels: a node's light is down to 37% this far away (and almost gone at 2x)
FADE_SECONDS = 0.8              # cross-fade after a capture
FADE_STEP = 0.05                # the fade is redrawn 20 times a second (a redraw costs ~10 ms; the fade is slow anyway)


class Territory:
    def __init__(self):
        cell = SCREEN_W / CELLS_X
        self.xs = ((np.arange(CELLS_X) + 0.5) * cell).astype(np.float32)        # pixel x of every grid column
        self.ys = ((np.arange(CELLS_Y) + 0.5) * cell).astype(np.float32)        # pixel y of every grid row
        self.noise = np.random.default_rng(4).uniform(0.0, 1.0, (CELLS_Y, CELLS_X, 1)).astype(np.float32)   # the dither
        self.small = pygame.Surface((CELLS_X, CELLS_Y), 0, 32)                  # the coarse picture, enlarged into `image`
        self.image = pygame.Surface((SCREEN_W, SCREEN_H), 0, 32)                # the finished picture
        self.shown = False                                                      # has anything been rendered yet?
        self.last_owners = None
        self.field = None                                                       # what is shown now: float RGB, 0..255
        self.start = self.target = None                                         # the two pictures of a cross-fade
        self.fade = 1.0                                                         # 0 -> 1 during a cross-fade
        self.since_render = 0.0

    def _compute(self, world):
        """The glow picture for the current owners, as float RGB (rows, cols, 3).

        A node's light is exp(-(dx^2 + dy^2) / R^2), which equals exp(-dx^2/R^2) * exp(-dy^2/R^2): one curve per
        column times one curve per row. So all lamps of a faction are added with ONE matrix product (rows x lamps) @ (lamps x cols).
        """
        field = np.zeros((CELLS_Y, CELLS_X, 3), dtype=np.float32)
        owners = np.array([n.owner for n in world.nodes])
        for faction in range(1, world.n_factions + 1):
            lamps = world.node_xy[owners == faction]
            if len(lamps) == 0:
                continue
            across = np.exp(-((self.xs[None, :] - lamps[:, 0:1]) ** 2) / (REACH * REACH))     # (lamps, cols)
            down = np.exp(-((self.ys[:, None] - lamps[:, 1][None, :]) ** 2) / (REACH * REACH))  # (rows, lamps)
            mine = down @ across                                                # all of this faction's lamps together
            strength = (1.0 - np.exp(-mine)) * STRENGTH                         # soft cap: many lamps never blow out
            field += strength[..., None] * np.array(FACTION_COLORS[faction], dtype=np.float32)
        return field

    def _render(self):
        """Dither, round to whole numbers, enlarge. Adding noise in 0..1 before rounding down is the dithering."""
        rgb = np.minimum(self.field + self.noise, 255).astype(np.uint8)
        pygame.surfarray.blit_array(self.small, rgb.transpose(1, 0, 2))         # (pygame wants [x, y])
        pygame.transform.smoothscale(self.small, (SCREEN_W, SCREEN_H), self.image)
        self.shown = True
        self.since_render = 0.0

    def update(self, world, instant=False):
        """Call after captures. Starts a cross-fade to the new owners (instant=True: show it at once, for a new map)."""
        owners = tuple(n.owner for n in world.nodes)
        if owners == self.last_owners:
            return
        self.last_owners = owners
        self.target = self._compute(world)
        if instant or self.field is None:
            self.field, self.fade = self.target, 1.0
            self._render()
        else:
            self.start, self.fade = self.field, 0.0

    def tick(self, dt):
        """Advance a cross-fade (called every frame; does nothing when no fade is running)."""
        if self.fade >= 1.0:
            return
        self.fade = min(1.0, self.fade + dt / FADE_SECONDS)
        self.since_render += dt
        if self.fade >= 1.0 or self.since_render >= FADE_STEP:                  # (always draw the last step)
            k = self.fade * self.fade * (3.0 - 2.0 * self.fade)                 # "smoothstep": gentle start and end
            self.field = self.start + (self.target - self.start) * k
            self._render()

    def draw(self, surf):
        if self.shown:
            surf.blit(self.image, (0, 0), special_flags=pygame.BLEND_ADD)

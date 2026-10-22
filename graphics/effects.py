"""graphics/effects.py - short-lived eye candy: expanding rings, sparks, flashes and screen shake.

What it is for : the "juice". A clash throws sparks in both colours; a capture sends out a ring,
                 a burst of particles and a light screen shake.
Uses            : config.py, numpy, pygame.
Used by         : ui/screens/play.py.

Everything advances one step per frame (no clock inside), which keeps it simple to test.
"""
import math

import numpy as np
import pygame

from config import FACTION_COLORS, SHAKE_PIXELS
from graphics.glow import build_glow

MAX_SPARKS = 600          # never let a huge battle slow the game down


class Effects:
    def __init__(self):
        self.rings = []        # [x, y, radius, max_radius, speed, colour]
        self.sparks = []       # [x, y, vx, vy, life, max_life, colour]
        self.flashes = []      # [x, y, life, max_life, radius, colour]   additive light flashes
        self.shake = 0.0
        self.rng = np.random.default_rng(5)
        self._flash_sprites = {}

    def clear(self):
        self.rings, self.sparks, self.flashes, self.shake = [], [], [], 0.0

    def ring(self, x, y, color, max_r=150, speed=9.0):
        self.rings.append([x, y, 0.0, max_r, speed, color])

    def burst(self, x, y, colors, n=20, speed=(2.0, 9.0)):
        """n sparks flying out in all directions, coloured at random from `colors`."""
        for _ in range(n):
            if len(self.sparks) >= MAX_SPARKS:
                return
            ang = self.rng.uniform(0, 2 * math.pi)
            spd = self.rng.uniform(*speed)
            life = int(self.rng.integers(14, 32))
            col = colors[int(self.rng.integers(0, len(colors)))]
            self.sparks.append([x, y, math.cos(ang) * spd, math.sin(ang) * spd, life, life, col])

    def flash(self, x, y, radius, color, life=8):
        """A soft burst of light that fades out (drawn additively, so it glows)."""
        self.flashes.append([x, y, life, life, radius, color])

    def clash(self, x, y, owner_a, owner_b, killed):
        """Two swarms annihilate: 6-10 sparks in BOTH colours, a little ring and a flash. Bigger clash = bigger show."""
        colors = (FACTION_COLORS[owner_a], FACTION_COLORS[owner_b], (255, 255, 255))
        big = min(1.0, killed / 14)
        self.burst(x, y, colors, n=int(self.rng.integers(6, 11)) + int(6 * big), speed=(1.5, 6.0 + 3 * big))
        self.flash(x, y, 20 + int(22 * big), (255, 255, 255), life=6)
        if killed >= 4:
            self.ring(x, y, FACTION_COLORS[owner_a if self.rng.random() < 0.5 else owner_b], max_r=28 + int(40 * big), speed=3.5)

    def capture(self, x, y, color, radius):
        """A node changes hands: ring in the new colour, particle burst, a 3 px shake."""
        self.ring(x, y, color, max_r=radius * 3 + 90, speed=10.0)
        self.ring(x, y, (255, 255, 255), max_r=radius * 2 + 40, speed=7.0)
        self.ring(x, y, color, max_r=radius * 4 + 60, speed=5.0)
        self.burst(x, y, (color, color, (255, 255, 255)), n=48, speed=(2.0, 11.0))
        self.flash(x, y, int(radius * 2.6), color, life=14)                 # the whole node lights up
        self.shake = 1.0

    def update(self):
        for r in self.rings:
            r[2] += r[4] * (1.0 - 0.75 * r[2] / r[3]) + 0.4        # fast at first, slowing down
        self.rings = [r for r in self.rings if r[2] < r[3]]
        for s in self.sparks:
            s[0] += s[2]
            s[1] += s[3]
            s[2] *= 0.93
            s[3] *= 0.93
            s[4] -= 1
        self.sparks = [s for s in self.sparks if s[4] > 0]
        for f in self.flashes:
            f[2] -= 1
        self.flashes = [f for f in self.flashes if f[2] > 0]
        self.flashes = self.flashes[-60:]
        self.shake *= 0.86

    def shake_offset(self):
        """(dx, dy) in pixels for this frame; (0, 0) when calm."""
        if self.shake < 0.05:
            return 0, 0
        amp = SHAKE_PIXELS * self.shake
        return int(self.rng.uniform(-amp, amp)), int(self.rng.uniform(-amp, amp))

    def draw(self, surf, bloom=True):
        """bloom=False skips the additive light flashes (rings and sparks are still drawn)."""
        for x, y, r, max_r, _, col in self.rings:
            if r < 2:
                continue
            fade = 1.0 - r / max_r                       # dark colours on black = fading out
            pygame.draw.circle(surf, tuple(int(c * fade) for c in col), (int(x), int(y)), int(r), 3 if fade > 0.4 else 1)
        for x, y, vx, vy, life, max_life, col in self.sparks:
            f = life / max_life
            pygame.draw.line(surf, tuple(int(c * f) for c in col), (int(x), int(y)),
                             (int(x - vx * 1.6), int(y - vy * 1.6)), 2 if f > 0.5 else 1)
        for x, y, life, max_life, radius, color in (self.flashes if bloom else ()):
            sprite = self._flash_sprite(radius, color, life * 6 // max_life)
            surf.blit(sprite, (int(x) - radius, int(y) - radius), special_flags=pygame.BLEND_ADD)

    def _flash_sprite(self, radius, color, level):
        """A glow picture in `color` at one of 6 brightness levels (made once, then reused)."""
        key = (radius, color, level)
        sprite = self._flash_sprites.get(key)
        if sprite is None:
            k = (level + 1) / 6
            sprite = self._flash_sprites[key] = build_glow(radius, tuple(int(c * k) for c in color)).convert()
        return sprite

"""graphics/starfield.py - the night sky behind the battle: a dim nebula, twinkling stars, a rare shooting star.

What it is for : a living background that stays far darker than the nodes and ships, so the game still
                 reads clearly. Stars sit on three "depth layers": far ones are small and drift slowly,
                 near ones are brighter and drift faster (parallax, like looking out of a train window).
Uses            : config.py, numpy, pygame.
Used by         : ui/screens/play.py (WorldView).

The nebula is made once with NumPy (a few soft coloured blobs); every frame it is one cheap blit.
"""
import math

import numpy as np
import pygame

from config import SCREEN_W, SCREEN_H
from graphics.glow import build_glow

STARS = 340
BIG_STARS = 14                             # the nearest layer: a few brighter stars with a little halo
NEBULA_PEAK = 22                           # brightest nebula pixel (of 255): it is only a hint of colour
BLOBS = [(0.22, 0.30, 0.34, (40, 70, 255)), (0.78, 0.72, 0.38, (150, 40, 220)),      # x, y, size, colour
         (0.55, 0.15, 0.25, (20, 90, 230)), (0.10, 0.85, 0.28, (90, 50, 200))]


def build_nebula(seed=3):
    """Soft cloudy colour patches: random blobs drawn small (96 x 54) and enlarged, which blurs them for free."""
    rng = np.random.default_rng(seed)
    w, h = 96, 54
    y, x = np.mgrid[0:h, 0:w]
    img = np.zeros((h, w, 3), dtype=np.float32)
    for bx, by, size, color in BLOBS:
        for _ in range(3):                                       # three overlapping lumps per blob make an uneven cloud
            cx = (bx + rng.uniform(-0.08, 0.08)) * w
            cy = (by + rng.uniform(-0.08, 0.08)) * h
            d2 = ((x - cx) / (w * size * rng.uniform(0.5, 1.0))) ** 2 + ((y - cy) / (h * size * rng.uniform(0.5, 1.0))) ** 2
            img += np.exp(-d2)[..., None] * np.array(color, dtype=np.float32) / 255.0
    img = np.clip(img, 0, 1.0) * NEBULA_PEAK
    small = pygame.image.frombuffer(img.astype(np.uint8).tobytes(), (w, h), "RGB")
    return pygame.transform.smoothscale(small, (SCREEN_W, SCREEN_H)).convert()


class Starfield:
    def __init__(self, seed=11):
        rng = np.random.default_rng(seed)
        self.nebula = build_nebula()
        self.x = rng.uniform(0, SCREEN_W, STARS)
        self.y = rng.uniform(0, SCREEN_H, STARS)
        depth = np.concatenate([rng.uniform(0.2, 0.7, STARS - BIG_STARS), rng.uniform(0.85, 1.0, BIG_STARS)])
        self.depth = depth                                       # 0.2 = far and slow ... 1.0 = near and faster
        self.drift = 3.0 + 13.0 * depth                          # pixels per second, to the left
        self.base = 75 + 100 * depth ** 2                        # brightness (0..255) before twinkling
        self.phase = rng.uniform(0, 2 * math.pi, STARS)
        self.speed = rng.uniform(0.6, 2.2, STARS)                # twinkle speed
        warmth = rng.uniform(0, 1, STARS)                        # 0 = bluish white, 1 = warm white
        self.tint = np.stack([0.8 + 0.2 * warmth, np.full(STARS, 0.9), 1.0 - 0.25 * warmth], axis=1)
        self.halo = build_glow(9, (110, 125, 170)).convert()       # (the window exists by now, so convert() works)
        self.time = 0.0
        self.shooting = None                                     # [x, y, vx, vy, life] while a shooting star flies
        self.next_shot = 6.0
        self.rng = rng

    def update(self, dt):
        self.time += dt
        if self.shooting is not None:
            s = self.shooting
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[4] -= dt
            if s[4] <= 0:
                self.shooting = None
        elif self.time > self.next_shot:                         # every 10-25 s a streak crosses the sky
            ang = self.rng.uniform(0.2, 0.6)
            speed = self.rng.uniform(900, 1300)
            self.shooting = [self.rng.uniform(300, SCREEN_W), self.rng.uniform(0, 300), -math.cos(ang) * speed,
                             math.sin(ang) * speed, 0.7]
            self.next_shot = self.time + self.rng.uniform(10, 25)

    def draw(self, surf):
        """Paint the whole sky (this replaces filling the screen with black)."""
        surf.blit(self.nebula, (0, 0))
        t = self.time
        xs = ((self.x - t * self.drift) % SCREEN_W).astype(int).tolist()
        ys = self.y.astype(int).tolist()
        level = self.base * (0.7 + 0.3 * np.sin(t * self.speed + self.phase))                  # twinkle
        colors = np.clip(level[:, None] * self.tint, 0, 255).astype(int).tolist()
        for i in range(STARS):
            size = 3 if self.depth[i] > 0.85 else (2 if self.depth[i] > 0.5 else 1)
            surf.fill(colors[i], (xs[i], ys[i], size, size), special_flags=pygame.BLEND_ADD)
            if size == 3:
                surf.blit(self.halo, (xs[i] - 9, ys[i] - 9), special_flags=pygame.BLEND_ADD)
        s = self.shooting
        if s is not None:
            fade = max(0.0, s[4] / 0.7)
            tail = (s[0] - s[2] * 0.06, s[1] - s[3] * 0.06)
            pygame.draw.line(surf, (int(70 * fade),) * 3, tail, (s[0], s[1]), 3)
            pygame.draw.line(surf, (int(200 * fade),) * 3, (s[0] - s[2] * 0.025, s[1] - s[3] * 0.025), (s[0], s[1]), 1)

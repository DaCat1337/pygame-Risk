"""graphics/glow.py - glow sprites, the faint dot grid, the vignette and the window icon.

What it is for : pre-rendered pictures that make the black screen glow. They are built once
                 with NumPy and then only blitted (copied to the screen), which is cheap.
Uses            : config.py, numpy, pygame.
Used by         : graphics/draw_nodes.py, ui/screens/play.py, main.py.

A "glow sprite" is a soft round picture that we draw with BLEND_ADD: the colours are ADDED to
what is already on screen, so overlapping light gets brighter, like real light.
"""
import math

import numpy as np
import pygame

from config import SCREEN_W, SCREEN_H, GRID_SPACING, GRID_BRIGHTNESS, GRID_FLASH_BRIGHTNESS, FACTION_COLORS

_glow_cache = {}


def build_glow(radius, color):
    """Soft radial glow sprite (bright in the middle, fading to black at `radius`). For BLEND_ADD."""
    size = radius * 2
    y, x = np.mgrid[0:size, 0:size]
    d = np.hypot(x - radius + 0.5, y - radius + 0.5) / radius
    a = np.clip(1.0 - d, 0.0, 1.0) ** 1.6
    rgb = np.zeros((size, size, 3), dtype=np.uint8)
    for i in range(3):
        rgb[..., i] = (a * color[i]).astype(np.uint8)
    return pygame.image.frombuffer(rgb.tobytes(), (size, size), "RGB")    # no convert(): the window icon is made BEFORE the window exists


def node_glow(node_radius, color):
    """Halo for a node: a faint plateau inside, brightest at the rim, fading out to ~2.6 radii.

    Cached per (radius, colour). The colour is rounded to steps of 8, so a colour cross-fade
    reuses a few dozen sprites instead of making a new one every frame.
    """
    color = tuple(min(255, int(c) // 8 * 8) for c in color)
    key = (node_radius, color)
    sprite = _glow_cache.get(key)
    if sprite is None:
        extent = int(node_radius * 2.6)
        size = extent * 2
        y, x = np.mgrid[0:size, 0:size]
        u = np.hypot(x - extent + 0.5, y - extent + 0.5) / node_radius          # distance in node radii
        a = np.where(u < 1.0, 0.16 + 0.12 * u, 0.28 * np.exp(-(u - 1.0) * 2.4))
        a = np.where(u > 2.6, 0.0, a)
        rgb = np.zeros((size, size, 3), dtype=np.uint8)
        for i in range(3):
            rgb[..., i] = np.clip(a * color[i] * 2.0, 0, 255).astype(np.uint8)
        sprite = _glow_cache[key] = pygame.image.frombuffer(rgb.tobytes(), (size, size), "RGB").convert()
    return sprite


def build_vignette():
    """Gentle radial darkening, stored as a "multiplier" picture (255 = unchanged, lower = darker).
    Applied with BLEND_MULT, which is far cheaper than an alpha blend of the whole screen."""
    y, x = np.mgrid[0:SCREEN_H, 0:SCREEN_W]
    r = np.hypot(x - SCREEN_W / 2, y - SCREEN_H / 2) / math.hypot(SCREEN_W / 2, SCREEN_H / 2)
    a = np.clip((r - 0.55) / 0.45, 0.0, 1.0) ** 2.0
    mult = (255 * (1.0 - 0.55 * a)).astype(np.uint8)
    rgb = np.repeat(mult.T[:, :, None], 3, axis=2)                 # pygame wants [x, y]
    surf = pygame.Surface((SCREEN_W, SCREEN_H), 0, 32)             # 32 bit = same format as the screen = fast blits
    pygame.surfarray.blit_array(surf, rgb)
    return surf


_dim_cache = {}


def dim(surf, level):
    """Darken the whole screen to level/255 of its brightness (255 = unchanged, 0 = black).

    Speed lesson: `surf.fill(colour, special_flags=BLEND_MULT)` over the whole screen costs ~15 ms, but blitting
    a ready-made flat picture with BLEND_MULT costs ~0.5 ms (same trick as the vignette). So the picture is cached.
    """
    flat = _dim_cache.get(level)
    if flat is None:
        flat = _dim_cache[level] = pygame.Surface((SCREEN_W, SCREEN_H), 0, 32)
        flat.fill((level, level, level))
    surf.blit(flat, (0, 0), special_flags=pygame.BLEND_MULT)


_GRID_DOTS = [(x - 1, y - 1, 2, 2) for x in range(GRID_SPACING // 2, SCREEN_W, GRID_SPACING)
              for y in range(GRID_SPACING // 2, SCREEN_H, GRID_SPACING)]


def draw_grid(surf, flash=0.0):
    """The faint dot grid (a dot every 60 px). flash 0..1 brightens it on a chord change.

    The dots are ADDED to what is already on screen (BLEND_ADD), so they never darken the sky or the territory
    wash underneath. (An earlier version blitted a whole-screen grid picture with an alpha: that dimmed everything
    behind it, and the chord-change flash even blacked the background out for a moment.)
    """
    level = int(255 * (GRID_BRIGHTNESS + (GRID_FLASH_BRIGHTNESS - GRID_BRIGHTNESS) * flash))
    color = (level, level, int(level * 1.2))
    for dot in _GRID_DOTS:
        surf.fill(color, dot, special_flags=pygame.BLEND_ADD)


def make_icon(size=64):
    """Window icon: a cyan node with a magenta one beside it, glowing on black."""
    surf = pygame.Surface((size, size))
    for (cx, cy, r, color) in ((size * 0.36, size * 0.5, size * 0.24, FACTION_COLORS[1]),
                               (size * 0.74, size * 0.34, size * 0.13, FACTION_COLORS[2])):
        halo = build_glow(int(r * 2.4), tuple(int(c * 0.5) for c in color))
        surf.blit(halo, (int(cx - r * 2.4), int(cy - r * 2.4)), special_flags=pygame.BLEND_ADD)
        pygame.draw.circle(surf, color, (int(cx), int(cy)), int(r), max(2, size // 16))
    return surf

"""graphics/fonts.py - loads the fonts once; a missing font never crashes the game.

What it is for : the Fonts class (hud / menu / title / small / one per node size) and a text cache.
Uses            : config.py, pygame.
Used by         : game.py, graphics/draw_nodes.py, ui/hud.py, ui/menu.py, ui/screens/*.

Rendering text is slow-ish, so Fonts.text() remembers pictures it already made.
"""
import pygame

from config import FONT_HUD, FONT_MENU, FONT_TITLE, FONT_NODE

FONT_NAMES = "consolas,menlo,dejavusansmono"     # the first one that exists on this computer is used


class _BlankFont:
    """Stand-in used when no font can be loaded at all: draws nothing, but the game keeps running."""

    def __init__(self, size):
        self.size_px = size

    def render(self, text, antialias, color, background=None):
        return pygame.Surface((max(1, len(text) * self.size_px // 2), self.size_px), pygame.SRCALPHA)

    def size(self, text):
        return (len(text) * self.size_px // 2, self.size_px)

    def get_height(self):
        return self.size_px


def _load(size, bold=False):
    try:
        if not pygame.font.get_init():
            pygame.font.init()
        return pygame.font.SysFont(FONT_NAMES, size, bold=bold)
    except Exception:
        pass
    try:
        return pygame.font.Font(None, int(size * 1.2))          # pygame's built-in default font
    except Exception:
        return _BlankFont(size)


class Fonts:
    def __init__(self):
        self.hud = _load(FONT_HUD)
        self.menu = _load(FONT_MENU)
        self.title = _load(FONT_TITLE, bold=True)
        self.small = _load(18)
        self.node = {size: _load(px, bold=True) for size, px in FONT_NODE.items()}
        self._cache = {}

    def text(self, font, string, color):
        """A rendered text picture (remembered, so drawing the same number again is free)."""
        key = (id(font), string, tuple(color))
        img = self._cache.get(key)
        if img is None:
            if len(self._cache) > 800:
                self._cache.clear()
            img = self._cache[key] = font.render(string, True, color)
        return img

    def draw(self, surf, font, string, color, pos, anchor="topleft"):
        """Draw text with its `anchor` point (e.g. "center", "midtop", "topright") at pos."""
        img = self.text(font, string, color)
        rect = img.get_rect(**{anchor: pos})
        surf.blit(img, rect)
        return rect

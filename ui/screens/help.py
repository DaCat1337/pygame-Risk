"""ui/screens/help.py - the how-to-play page with a tiny animated diagram.

What it is for : five short lines of rules and a looping picture of two swarms meeting.
Uses            : config.py, pygame.
Used by         : game.py (an overlay; opened with F1 or from the title menu).
"""
import math

import pygame
from pygame import gfxdraw

from config import SCREEN_W, SCREEN_H, FACTION_COLORS, C_TEXT, C_DIM
from graphics.glow import dim

LINES = [
    "DRAG from one of your glowing nodes onto another node to send ships. Space = all your nodes.",
    "Every beat your nodes make ships (big nodes more). Ships you order leave on the next beat.",
    "Enemy swarms that meet in mid-air destroy each other. What gets through lowers the node; at zero it is yours.",
    "Each colour plays its own instrument, louder the more it owns. Captures ring a bell.",
    "Special nodes: FORTRESS (double ring) is very hard to take, FACTORY (gear) makes twice the ships, RELAY (diamond) launches faster ships.",
    "Mouse wheel or keys 1-4 = send 25 / 50 / 75 / 100%.   P = pause   M = music   B = bloom   C = colour-blind   Esc = menu.",
]
LEFT, RIGHT, ROW = (620, 830), (1300, 830), 830


class HelpScreen:
    def __init__(self, game, pauses=False):
        self.game = game
        self.pauses = pauses                  # True when opened during a match (the match is paused meanwhile)
        self.time = 0.0

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and e.key in (pygame.K_ESCAPE, pygame.K_F1, pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER) \
                or e.type == pygame.MOUSEBUTTONDOWN:
            self.game.close_overlay()

    def update(self, dt):
        self.time += dt

    def draw(self, surf):
        fonts = self.game.fonts
        dim(surf, 16)
        fonts.draw(surf, fonts.title, "HOW TO PLAY", FACTION_COLORS[1], (SCREEN_W // 2, 130), "center")
        for i, line in enumerate(LINES):
            fonts.draw(surf, fonts.hud, f"{i + 1}.  {line}", C_TEXT, (SCREEN_W // 2, 280 + i * 62), "center")
        self._diagram(surf)
        fonts.draw(surf, fonts.small, "press any key or click to close", C_DIM, (SCREEN_W // 2, SCREEN_H - 50), "center")

    def _diagram(self, surf):
        """Cyan swarm flies right, magenta flies left; where they meet they burst into sparks."""
        cyan, magenta, grey = FACTION_COLORS[1], FACTION_COLORS[2], FACTION_COLORS[0]
        for (x, y), color in ((LEFT, cyan), (RIGHT, grey)):
            gfxdraw.aacircle(surf, x, y, 46, color)
            gfxdraw.aacircle(surf, x, y, 45, color)
            gfxdraw.filled_circle(surf, x, y, 44, (*color, 30))
        span = RIGHT[0] - LEFT[0] - 90
        mid = LEFT[0] + 45 + span // 2
        for i in range(10):
            phase = ((self.time * 0.55 + i * 0.1) % 1.0) * 0.5                     # each dot travels half the distance
            pygame.draw.circle(surf, cyan, (int(LEFT[0] + 45 + span * phase), ROW + (i % 3 - 1) * 8), 3)
            pygame.draw.circle(surf, magenta, (int(RIGHT[0] - 45 - span * phase), ROW + (i % 3 - 1) * 8 + 4), 3)
        flash = (math.sin(self.time * 5.5) + 1) / 2
        pygame.draw.circle(surf, (int(255 * flash),) * 3, (mid, ROW), int(4 + 8 * flash), 1)

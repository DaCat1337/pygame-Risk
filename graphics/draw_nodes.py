"""graphics/draw_nodes.py - draws the glowing nodes, their beat pulse, rings, and selection feedback.

What it is for : NodeView keeps the *visual* state of each node (pulse, colour fade); draw_nodes
                 and draw_selection paint them. The World is only read, never changed.
Uses            : config.py, graphics/glow.py, graphics/fonts.py, pygame (gfxdraw).
Used by         : ui/screens/play.py.

Visual state lives here, not in core/node.py, because the rules must not care what colour
something is *currently shown* in while it cross-fades after a capture.
"""
import math

import pygame
from pygame import gfxdraw

from config import FACTION_COLORS, PULSE_PIXELS, PULSE_DECAY, CAPTURE_FADE, PLAYER, C_TEXT
from graphics.glow import node_glow


class NodeView:
    def __init__(self, nodes):
        self.pulse = [0.0] * len(nodes)                       # 1.0 right on the beat, then eases to 0
        self.wave = [0.0] * len(nodes)                        # a ripple that leaves the node on the beat: 1.0 -> 0
        self.color = [tuple(map(float, FACTION_COLORS[n.owner])) for n in nodes]   # colour shown right now
        self.fade_from = list(self.color)
        self.fade_to = list(self.color)
        self.fade = [1.0] * len(nodes)                        # 0 -> 1 during a cross-fade

    def on_beat(self, nodes):
        """Every OWNED node pops on the beat: the whole map breathes with the music."""
        for i, node in enumerate(nodes):
            if node.owner:
                self.pulse[i] = 1.0
                self.wave[i] = 1.0

    def on_capture(self, index, new_owner):
        """Start a 0.3 s cross-fade from the old colour to the new owner's colour."""
        self.fade_from[index] = self.color[index]
        self.fade_to[index] = tuple(map(float, FACTION_COLORS[new_owner]))
        self.fade[index] = 0.0
        self.pulse[index] = 1.0

    def update(self, dt):
        decay = math.exp(-dt / PULSE_DECAY)
        for i in range(len(self.pulse)):
            self.pulse[i] *= decay
            self.wave[i] = max(0.0, self.wave[i] - dt / WAVE_SECONDS)
            if self.fade[i] < 1.0:
                self.fade[i] = min(1.0, self.fade[i] + dt / CAPTURE_FADE)
                a, b, f = self.fade_from[i], self.fade_to[i], self.fade[i]
                self.color[i] = tuple(a[k] + (b[k] - a[k]) * f for k in range(3))


WAVE_SECONDS = 0.6                                              # how long a beat ripple lives
WAVE_REACH = 46                                                 # how far it travels beyond the node's edge


def _scaled(color, k):
    return tuple(min(255, int(c * k)) for c in color)


def _arc_points(x, y, r, start, sweep, steps):
    return [(x + r * math.cos(start + sweep * k / steps), y + r * math.sin(start + sweep * k / steps))
            for k in range(steps + 1)]


def draw_nodes(surf, nodes, nv, fonts, t, bloom=True):
    """Draw every node. t = seconds (for the orbiting dots). bloom=False leaves out the soft glow around nodes."""
    for i, node in enumerate(nodes):
        owned = node.owner != 0
        color = tuple(int(c) for c in nv.color[i])
        pulse = nv.pulse[i] if owned else 0.0
        x, y = int(node.x), int(node.y)

        # additive glow behind the node; it flares only a little on the beat (it happens twice a second)
        if bloom:
            glow = node_glow(node.radius, _scaled(color, 0.55 + 0.2 * pulse if owned else 0.45))
            surf.blit(glow, (x - glow.get_width() // 2, y - glow.get_height() // 2), special_flags=pygame.BLEND_ADD)

        # body: very faint fill + a 3 px antialiased outline that pops outwards on the beat
        r = int(node.radius + PULSE_PIXELS * pulse)
        gfxdraw.filled_circle(surf, x, y, r, (*color, 25))
        for k in range(3):
            gfxdraw.aacircle(surf, x, y, r - k, color)

        if owned and nv.wave[i] > 0.02:
            travelled = 1.0 - nv.wave[i]                        # 0 = at the node, 1 = fully spread and gone
            gfxdraw.aacircle(surf, x, y, int(node.radius + 8 + WAVE_REACH * travelled), (*color, int(55 * (1.0 - travelled) ** 2)))
        if owned:
            # capacity ring: an arc that fills up as the garrison approaches the cap
            frac = min(1.0, node.garrison / node.cap)
            if frac > 0.01:
                steps = max(2, int(frac * 48))
                pygame.draw.lines(surf, _scaled(color, 0.8), False,
                                  _arc_points(x, y, node.radius + 10, -math.pi / 2, 2 * math.pi * frac, steps), 2)
            # orbiting dots: one per 4 ships, at most 10 (cosmetic only)
            n_dots = min(10, int(node.garrison // 4))
            spin = t * (0.9 if i % 2 else -0.9)
            for k in range(n_dots):
                a = spin + 2 * math.pi * k / n_dots
                surf.fill(_scaled(color, 0.9), (int(x + (node.radius + 20) * math.cos(a)) - 1,
                                                int(y + (node.radius + 20) * math.sin(a)) - 1, 3, 3))

        fonts.draw(surf, fonts.node[node.size], str(int(max(0, node.garrison))), C_TEXT, (x, y), "center")


def draw_selection(surf, nodes, selection, hover, cursor, label, fonts, t):
    """Selection feedback: dashed rotating rings, glowing drag lines, hover ring with a label.

    selection = list of node indices, hover = node index or None, cursor = mouse position or None
    (a line is only drawn while dragging), label = text such as "needs ~12" or "".
    """
    color = FACTION_COLORS[PLAYER]
    for i in selection:
        node = nodes[i]
        for k in range(10):                                    # 10 dashes, slowly turning
            a0 = t * 1.3 + k * 2 * math.pi / 10
            pygame.draw.lines(surf, (255, 255, 255), False,
                              _arc_points(node.x, node.y, node.radius + 14, a0, 0.38, 5), 2)
        if cursor is not None:
            pygame.draw.line(surf, _scaled(color, 0.35), (node.x, node.y), cursor, 7)
            pygame.draw.line(surf, _scaled(color, 0.8), (node.x, node.y), cursor, 3)
            pygame.draw.line(surf, (255, 255, 255), (node.x, node.y), cursor, 1)
    if hover is not None:
        node = nodes[hover]
        gfxdraw.aacircle(surf, int(node.x), int(node.y), node.radius + 9, (255, 255, 255))
        gfxdraw.aacircle(surf, int(node.x), int(node.y), node.radius + 10, (255, 255, 255))
        if label:
            fonts.draw(surf, fonts.hud, label, (255, 255, 255), (node.x, node.y - node.radius - 18), "midbottom")

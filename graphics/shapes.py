"""graphics/shapes.py - the four faction symbols (circle, square, triangle, diamond).

What it is for : colour-blind mode marks every faction with a shape as well as a colour, so you never have to
                 tell two colours apart. circle = faction 1, square = 2, triangle = 3, diamond = 4 (config.FACTION_SHAPES).
Uses            : pygame (gfxdraw for smooth edges).
Used by         : graphics/draw_nodes.py, ui/hud.py, ui/screens/gameover.py.
"""
from pygame import gfxdraw


def draw_shape(surf, shape, center, size, color):
    """Draw a small filled symbol. `size` is its half-width in pixels."""
    x, y = int(center[0]), int(center[1])
    if shape == "circle":
        gfxdraw.aacircle(surf, x, y, size, color)
        gfxdraw.filled_circle(surf, x, y, size, color)
        return
    if shape == "square":
        points = [(x - size, y - size), (x + size, y - size), (x + size, y + size), (x - size, y + size)]
    elif shape == "triangle":
        points = [(x, y - size - 1), (x + size + 1, y + size), (x - size - 1, y + size)]
    else:                                                    # diamond
        points = [(x, y - size - 1), (x + size + 1, y), (x, y + size + 1), (x - size - 1, y)]
    gfxdraw.aapolygon(surf, points, color)
    gfxdraw.filled_polygon(surf, points, color)

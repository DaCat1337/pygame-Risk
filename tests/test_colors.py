"""tests/test_colors.py - colour-blind mode: a palette that stays readable, a symbol per faction, switching on and off.

What it is for : the palette is judged by SIMULATING colour blindness (Machado et al. 2009 matrices for protanopia,
                 deuteranopia and tritanopia) and measuring how far apart the factions stay in the CIELAB colour space
                 ("dE": about 2 is just noticeable, 20+ is clearly different, 40+ is very different).
Uses            : config.py, graphics/shapes.py, game.py.
Used by         : tests/run_all.py.
"""
import itertools
import tempfile

import helpers
from helpers import check
import numpy as np
import pygame

import config
from config import FACTION_COLORS, FACTION_NAMES, COLOR_NAMES, FACTION_SHAPES, apply_palette, color_choices
from game import Game

SIMULATE = {                                        # colour-vision simulation, applied in linear RGB (severity 1.0)
    "protan": np.array([[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]]),
    "deutan": np.array([[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]]),
    "tritan": np.array([[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]]),
    "normal": np.eye(3),
}


def _linear(rgb):
    c = np.array(rgb) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _lab(linear_rgb):
    xyz = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]) @ np.clip(linear_rgb, 0, 1)
    xyz = xyz / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def worst_difference(colors, kind):
    """The smallest colour difference between any two of `colors` as seen with colour vision `kind`."""
    labs = [_lab(SIMULATE[kind] @ _linear(c)) for c in colors]
    return min(float(np.linalg.norm(a - b)) for a, b in itertools.combinations(labs, 2))


def run():
    apply_palette(False)
    default = [FACTION_COLORS[f] for f in range(5)]                 # neutral grey + the four factions
    default_names = dict(FACTION_NAMES)
    apply_palette(True)
    cb = [FACTION_COLORS[f] for f in range(5)]
    cb_names = dict(FACTION_NAMES)

    check(default != cb and default[0] == cb[0], "colour-blind mode changes the four faction colours, not the grey neutral")
    check(cb_names != default_names and COLOR_NAMES[2] == "RED", "...and the colour names shown in watch mode / the HUD")
    for kind in ("normal", "protan", "deutan", "tritan"):
        gap = worst_difference(cb, kind)
        check(gap > 35, f"colour-blind palette: every pair stays clearly different for {kind} vision (smallest dE {gap:.0f})")
    check(worst_difference(cb, "protan") > 3 * worst_difference(default, "protan"),
          f"...far better than the normal palette for protanopia ({worst_difference(cb, 'protan'):.0f} vs {worst_difference(default, 'protan'):.0f})")
    check(all(max(c) >= 190 for c in cb[1:]), "all four colours are bright enough to glow on black")
    check(len(set(FACTION_SHAPES.values())) == 4 and sorted(FACTION_SHAPES) == [1, 2, 3, 4], "four different symbols, one per faction")
    apply_palette(False)
    check([FACTION_COLORS[f] for f in range(5)] == default and dict(FACTION_NAMES) == default_names, "switching back restores the original palette")

    # --- choosing your colour: YOU get the picked colour, the opponents the rest in menu order
    for cb in (False, True):
        choices = color_choices(cb)
        names = [name for _, name in choices]
        for pick in range(4):
            apply_palette(cb, pick)
            order = [pick] + [i for i in range(4) if i != pick]
            check([FACTION_COLORS[f] for f in range(1, 5)] == [choices[i][0] for i in order],
                  f"{'colour-blind' if cb else 'normal'} set, you = {names[pick]}: your colour first, the others in menu order")
            check([COLOR_NAMES[f] for f in range(1, 5)] == [names[i] for i in order] and FACTION_NAMES[1] == "YOU"
                  and [FACTION_NAMES[f] for f in (2, 3, 4)] == [names[i] for i in order[1:]],
                  f"the names follow the colours (you = {names[pick]}), and you are still called YOU")
            check(len(set(FACTION_COLORS[f] for f in range(1, 5))) == 4 and FACTION_COLORS[0] == default[0], "four different colours, grey neutral untouched")
        check(worst_difference([FACTION_COLORS[0]] + [FACTION_COLORS[f] for f in range(1, 5)], "deutan") == worst_difference(
            [default[0]] + [c for c, _ in choices], "deutan"), "the same four colours are in play whoever you are (same distinctness)")
    apply_palette(False, 7)
    check(FACTION_COLORS[1] == color_choices(False)[3][0], "a too-big colour number wraps round instead of crashing")
    apply_palette(False)

    # --- the shapes are really different pictures
    from graphics.shapes import draw_shape
    pygame.init()
    screen = pygame.display.set_mode((1920, 1080))
    pictures = []
    for shape in FACTION_SHAPES.values():
        surf = pygame.Surface((40, 40))
        draw_shape(surf, shape, (20, 20), 8, (255, 255, 255))
        pictures.append(pygame.image.tostring(surf, "RGB"))
        check(surf.get_at((20, 20))[:3] == (255, 255, 255), f"the {shape} is filled in the middle")
    check(len(set(pictures)) == 4, "the four symbols look different")

    # --- the game: C switches mode, everything repaints, the setting is remembered
    game = Game(screen, audio=None, settings_path=None, shots_dir=tempfile.mkdtemp())
    game.start_match(11)
    for _ in range(40):
        game.update(1 / 60)
        game.draw()
    world = game.play.world
    mine = next(n for n in world.nodes if n.owner == 1)
    x, y = int(mine.x), int(mine.y)
    mark = (x, y - max(15, int(mine.radius * 0.62)))
    before = FACTION_COLORS[1]
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c, mod=0, unicode="c"))
    check(game.settings["colorblind"] is True and FACTION_COLORS[1] != before, "C switches colour-blind mode on")
    check(game.play.view.nv.color[world.nodes.index(mine)] == tuple(map(float, FACTION_COLORS[1])), "nodes are repainted at once (no slow cross-fade)")
    game.draw()
    check(sum(game.screen.get_at(mark)[:3]) > 300, "the player's node shows its circle symbol above the number")
    game.show_game_over(world)
    game.draw()
    game.close_overlay()
    from ui.screens.pause import PauseScreen
    check(any(item.key == "colorblind" for item in PauseScreen(game).menu.items), "the Esc menu has a COLOUR-BLIND MODE toggle")
    game.set_setting("colorblind", False)
    check(FACTION_COLORS[1] == before, "switching it off (menu) restores the colours")
    game.draw()
    check(sum(game.screen.get_at(mark)[:3]) < 300, "...and the symbols disappear")
    game.enter_title()
    for _ in range(20):
        game.update(1 / 60)
        game.draw()
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c, mod=0, unicode="c"))
    for _ in range(5):
        game.update(1 / 60)
        game.draw()
    check(game.settings["colorblind"] is True, "C works on the title screen too")
    game.set_setting("colorblind", False)
    check(FACTION_COLORS[1] == before, "palette restored")

    # --- YOUR COLOUR in the title menu: the choice labels follow the palette, picking applies at once, the new match uses it
    menu = game.title.menu
    item = next(it for it in menu.items if it.key == "player_color")
    check(menu.value_text(item) == "CYAN", "YOUR COLOUR starts on CYAN")
    game.settings["colorblind"] = True
    check(menu.labels_of(item) == ("CYAN", "RED", "YELLOW", "MAGENTA"), "the colour names change with colour-blind mode")
    game.settings["colorblind"] = False
    menu.sel = menu.items.index(item)
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT, mod=0, unicode=""))
    check(game.settings["player_color"] == 1 and FACTION_COLORS[1] == color_choices(False)[1][0], "Right = MAGENTA: you are magenta at once")
    check(FACTION_COLORS[2] == color_choices(False)[0][0], "...and the first opponent takes the colour you gave up (cyan)")
    for _ in range(20):
        game.update(1 / 60)
        game.draw()
    check(game.title.menu.value_text(item) == "MAGENTA", "the menu shows the new colour")
    game.start_match(11)
    for _ in range(40):
        game.update(1 / 60)
        game.draw()
    mine = next(n for n in game.play.world.nodes if n.owner == 1)
    shown = game.screen.get_at((int(mine.x) + mine.radius, int(mine.y)))[:3]
    check(shown[0] > shown[1] and shown[2] > shown[1], f"in the match your node is magenta-ish ({shown})")
    check(game.play.view.nv.color[game.play.world.nodes.index(mine)] == tuple(map(float, color_choices(False)[1][0])), "the node view uses the chosen colour")
    game.set_setting("player_color", 0)
    check(FACTION_COLORS[1] == before, "colour back to cyan at the end of the test")


if __name__ == "__main__":
    run()
    raise SystemExit(0 if helpers.report("test_colors") else 1)

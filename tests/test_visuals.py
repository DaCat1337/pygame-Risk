"""tests/test_visuals.py - the eye candy: effects, ships, starfield and territory wash (headless).

What it is for : proves the visual helpers stay bounded, fade away, draw without errors and stay dim
                 enough not to compete with the game. It cannot judge how things LOOK (look at the screen for that).
Uses            : graphics/*, core/ships.py, game.py.
Used by         : tests/run_all.py.
"""
import tempfile

import helpers
from helpers import check
import pygame

from game import Game


def run():
    pygame.init()
    screen = pygame.display.set_mode((1920, 1080))
    game = Game(screen, audio=None, settings_path=None, shots_dir=tempfile.mkdtemp())
    game.start_match(11)
    for _ in range(20):
        game.update(1 / 60)
        game.draw()

    # --- visual effects: bounded, they fade away completely, and draw without errors
    from graphics.effects import Effects, MAX_SPARKS
    fx = Effects()
    for _ in range(200):
        fx.clash(500, 500, 1, 2, 14)
    fx.capture(900, 500, (255, 60, 140), 39)
    check(len(fx.sparks) <= MAX_SPARKS, f"a huge battle never creates more than {MAX_SPARKS} sparks")
    fx.update()
    fx.draw(screen)
    for _ in range(120):
        fx.update()
    check(not fx.sparks and not fx.rings and not fx.flashes and fx.shake < 0.05, "all effects fade away completely")
    from graphics.draw_ships import draw_ships
    from core.ships import Ships
    import numpy as np
    ships = Ships()
    ships.launch(1, game.play.world.nodes[0], 1, game.play.world.nodes[1], 40, np.random.default_rng(1))
    ships.pos[0] = (0.0, 0.0)                               # right in the corner: the glow must not read outside the screen
    draw_ships(screen, ships)
    check(screen.get_at((960, 540))[:3] != (255, 0, 255), "ships (even in the corner) draw without errors")

    # --- the starfield: draws, drifts, and a shooting star appears after a few seconds
    from graphics.starfield import Starfield
    sky = Starfield()
    sky.update(0.5)
    sky.draw(screen)
    check(screen.get_at((960, 540))[:3] != (255, 0, 255), "the starfield draws without errors")
    check(max(screen.get_at((x, 540))[0] for x in range(0, 1920, 7)) < 60, "the sky is dim: it never competes with the game")
    sky.update(7.0)
    check(sky.shooting is not None, "a shooting star appears after a few seconds")
    for _ in range(100):
        sky.update(0.02)
    sky.draw(screen)
    check(sky.shooting is None or sky.shooting[4] > 0, "the shooting star ends (or is still flying) without errors")

    # --- the territory glow: faint, in the owner's colour, smooth (no hard borders), cross-fades, black with no owners
    from graphics.territory import Territory
    from config import FACTION_COLORS as _FC
    terr_world = game.play.world
    terr = Territory()
    terr.update(terr_world, instant=True)
    owned = next((n for n in terr_world.nodes if n.owner == 1), None) or next(n for n in terr_world.nodes if n.owner)
    black = pygame.Surface((1920, 1080), 0, 32)
    terr.draw(black)
    px = black.get_at((int(owned.x), int(owned.y)))[:3]
    check(0 < max(px) <= 25, f"the territory glow is faint ({px}) but visible above a node")
    want = _FC[owned.owner]
    check(px.index(max(px)) == want.index(max(want)), "the glow has the owner's colour")

    def brightness(x, y, size=8):
        """Average brightness of a size x size patch (averaging hides the fine dither grain)."""
        total = sum(sum(black.get_at((x + i, y + j))[:3]) for i in range(size) for j in range(size))
        return total / (size * size)

    row = [brightness(x, int(owned.y)) for x in range(0, 1900, 8)]
    jumps = max(abs(a - b) for a, b in zip(row, row[1:]))
    check(jumps <= 4.0, f"no hard edges: the glow changes by at most {jumps:.1f} levels between neighbouring patches")
    inside = owned.x
    check(brightness(int(inside), int(owned.y)) > 3 * brightness(1900, 1060) or brightness(1900, 1060) < 2, "the glow fades out away from the node")

    target_before = terr.target
    terr.update(terr_world)
    check(terr.target is target_before, "the glow is not recomputed when nothing changed hands")
    saved = [(n, n.owner) for n in terr_world.nodes]            # (put back afterwards)
    for n in terr_world.nodes:
        n.owner = 0
    terr.update(terr_world)
    black.fill((0, 0, 0))
    terr.draw(black)
    check(black.get_at((int(owned.x), int(owned.y)))[:3] == px, "after a capture the old glow stays while the cross-fade has not started")
    terr.tick(0.3)
    black.fill((0, 0, 0))
    terr.draw(black)
    mid = sum(black.get_at((int(owned.x), int(owned.y)))[:3])
    check(0 < mid < sum(px), "halfway through the cross-fade the glow is dimmer, but not gone")
    terr.tick(2.0)
    black.fill((0, 0, 0))
    terr.draw(black)
    check(black.get_at((int(owned.x), int(owned.y)))[:3] == (0, 0, 0) and black.get_at((960, 540))[:3] == (0, 0, 0),
          "a map with no owners ends with no glow at all")
    for n, o in saved:
        n.owner = o

    # --- the dot grid only ADDS light: it never darkens the sky, even at the full chord-change flash
    # (regression: an alpha-blended grid picture used to black the background out every 16 beats)
    from graphics.glow import draw_grid
    base = pygame.Surface((1920, 1080), 0, 32)
    base.fill((30, 40, 60))
    spots = [(30 + 60 * i, 30 + 60 * j) for i in range(3) for j in range(3)] + [(45, 45), (500, 500)]   # dots and gaps
    for flash in (0.0, 0.5, 1.0):
        test = base.copy()
        draw_grid(test, flash)
        check(all(all(a >= b for a, b in zip(test.get_at(p)[:3], base.get_at(p)[:3])) for p in spots),
              f"the grid never darkens what is behind it (flash {flash})")
        check(test.get_at((30, 30))[0] > 30 and test.get_at((500, 500))[:3] == (30, 40, 60),
              "grid dots are brighter, the space between is untouched")

    # --- the bloom switch: off = no glow around nodes and ships, on = glow (B key and the settings menu)
    game.start_match(11)
    for _ in range(40):
        game.update(1 / 60)
        game.draw()
    node = next(n for n in game.play.world.nodes if n.owner == 1)
    area = pygame.Rect(int(node.x - 2.2 * node.radius), int(node.y - 2.2 * node.radius), int(4.4 * node.radius), int(4.4 * node.radius))

    def light_around():
        game.draw()
        return sum(sum(game.screen.get_at((x, y))[:3]) for x in range(area.left, area.right, 3) for y in range(area.top, area.bottom, 3))

    check(game.settings["bloom"] is True, "bloom is on by default")
    lit = light_around()
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b, mod=0, unicode="b"))
    check(game.settings["bloom"] is False, "B switches bloom off")
    dark = light_around()
    check(dark < lit * 0.85, f"bloom off: clearly less light around a node ({dark} < {lit})")
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b, mod=0, unicode="b"))
    check(game.settings["bloom"] is True and light_around() > dark * 1.15, "B switches bloom back on")
    from ui.screens.pause import PauseScreen
    check(any(item.key == "bloom" for item in PauseScreen(game).menu.items), "the Esc menu has a BLOOM toggle")


    # --- special nodes look different: each kind adds its own mark around the circle
    from config import NODE_NORMAL, NODE_FORTRESS, NODE_FACTORY, NODE_RELAY
    kind_world = game.play.world
    spare = [n for n in kind_world.nodes if n.owner == 0][:3]
    for n, k in zip(spare, (NODE_FORTRESS, NODE_FACTORY, NODE_RELAY)):
        n.kind = k
    game.draw()
    fort, gear, relay = spare

    def lit(x, y, r=4):
        return max(sum(game.screen.get_at((int(x) + dx, int(y) + dy))[:3]) for dx in range(-r, r + 1) for dy in range(-r, r + 1))

    check(lit(fort.x, fort.y - fort.radius - 8.5) > 90, "a fortress has its second ring")
    check(lit(relay.x, relay.y - relay.radius - 17, 3) > 60, "a relay has its diamond (the top corner)")
    check(lit(gear.x + gear.radius + 6, gear.y, 12) > 60, "a factory has its gear teeth")
    for n in spare:
        n.kind = NODE_NORMAL


if __name__ == "__main__":
    run()
    raise SystemExit(0 if helpers.report("test_visuals") else 1)

"""tests/test_perf.py - how fast is the game with a big battle? (2000 ships in the air)

What it is for : measures the average World.tick() time and the time of one full draw() at 1920x1080.
                 The plan wants tick < 3 ms and draw < 14 ms. Slow machines only get a WARNING, not a failure,
                 because speed depends on the computer (the dummy video driver also differs from a real window).
Uses            : core/world.py, game.py, graphics/*.
Used by         : tests/run_all.py.
"""
import time

import helpers
from helpers import check
import numpy as np
import pygame

from core.world import World
from game import Game

SHIPS = 2000
TICK_LIMIT_MS = 3.0
DRAW_LIMIT_MS = 14.0


def fill_the_sky(world, total=SHIPS):
    """Launch `total` ships between random pairs of nodes, owned by the factions in turn."""
    rng = np.random.default_rng(1)
    n = len(world.nodes)
    while world.ships.alive.sum() < total:
        a, b = rng.choice(n, 2, replace=False)
        owner = int(rng.integers(1, world.n_factions + 1))
        world.ships.launch(owner, world.nodes[a], int(b), world.nodes[b], 40, rng)


def average_ms(fn, repeats):
    start = time.perf_counter()
    for _ in range(repeats):
        fn()
    return (time.perf_counter() - start) / repeats * 1000


def run():
    pygame.init()
    screen = pygame.display.set_mode((1920, 1080))

    # --- the rules: World.tick() with 2000 ships flying (clash detection is the expensive part)
    world = World(seed=11, n_factions=4, map_size=2, countdown_beats=0)
    fill_the_sky(world)
    flying = int(world.ships.alive.sum())
    tick_ms = average_ms(world.tick, 45)                   # 45 ticks = 0.75 s: the ships are still mostly in the air
    still_flying = int(world.ships.alive.sum())
    check(flying >= 1500 and still_flying >= 600, f"the test really had a big battle in the air ({flying} ships, {still_flying} after)")
    print(f"    World.tick() with ~{flying} ships: {tick_ms:.2f} ms (plan: < {TICK_LIMIT_MS} ms; 60 FPS leaves 16.7 ms per frame)")
    if tick_ms >= TICK_LIMIT_MS:
        print(f"    WARNING: tick is slower than {TICK_LIMIT_MS} ms on this computer")

    # --- the picture: one full frame (sky, territory, nodes, ships, effects, HUD)
    game = Game(screen, audio=None, settings_path=None)
    game.start_match(11)
    for _ in range(60):                                    # let the screen fade finish so the PLAY screen is what we time
        game.update(1 / 60)
    check(game.current is game.play and game.fade is None, "the play screen is showing")
    fill_the_sky(game.play.world)
    game.draw()                                            # warm-up: builds the cached glow sprites
    draw_ms = average_ms(game.draw, 30)
    check(draw_ms > 0, "a full frame draws")
    print(f"    full draw() at 1920x1080 with ~{int(game.play.world.ships.alive.sum())} ships: {draw_ms:.2f} ms (plan: < {DRAW_LIMIT_MS} ms)")
    if draw_ms >= DRAW_LIMIT_MS:
        print(f"    WARNING: draw is slower than {DRAW_LIMIT_MS} ms on this computer")
    title_ms = average_ms(lambda: game.title.draw(screen), 20)       # the title draws a whole battle plus the dim panel and menu
    print(f"    title screen draw(): {title_ms:.2f} ms")
    if title_ms >= DRAW_LIMIT_MS:
        print(f"    WARNING: the title draw is slower than {DRAW_LIMIT_MS} ms on this computer")
    sum_ms = tick_ms + draw_ms
    print(f"    tick + draw = {sum_ms:.1f} ms of the 16.7 ms budget for 60 FPS")


if __name__ == "__main__":
    run()
    raise SystemExit(0 if helpers.report("test_perf") else 1)

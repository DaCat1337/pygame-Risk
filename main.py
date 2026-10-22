"""main.py - entry point: start pygame, choose the scaling, open the window, run the Game.

Run it from inside the game4 folder:   python main.py
Uses: settings.py, graphics/screen.py, graphics/glow.py, game.py.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)                        # so "from core.world import World" works from anywhere

import pygame  # noqa: E402

from audio.player import Audio  # noqa: E402
from game import Game  # noqa: E402
from graphics.glow import make_icon  # noqa: E402
from graphics.screen import apply_scaling_environment, make_screen  # noqa: E402
from settings import load_settings  # noqa: E402


def main():
    pygame.init()
    pygame.display.set_caption("Swarm Conquest")
    pygame.display.set_icon(make_icon())
    settings_path = os.path.join(HERE, "settings.json")
    # How the 1920x1080 picture is stretched must be decided BEFORE the window exists.
    apply_scaling_environment(load_settings(settings_path)["scaling"])
    screen = make_screen(fullscreen=True)
    audio = Audio(enabled=True)                     # no sound device? it just stays silent
    game = Game(screen, audio=audio, settings_path=settings_path, shots_dir=os.path.join(HERE, "screenshots"))
    game.wait_for_music()                           # the first track is built before the title appears
    game.run()
    sys.exit(0)


if __name__ == "__main__":
    main()

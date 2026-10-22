"""tests/helpers.py - the tiny test toolkit shared by every test file.

What it is for : check(condition, message) counts passes and failures; the dummy SDL drivers let
                 pygame run with no window and no sound card (so tests work anywhere).
Uses            : nothing from the game.
Used by         : every tests/test_*.py and tests/run_all.py.

IMPORTANT: this file must be imported BEFORE pygame, because the SDL environment variables are
read when pygame starts.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

# make "from core.world import World" work no matter where the test is started from
GAME_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if GAME_DIR not in sys.path:
    sys.path.insert(0, GAME_DIR)

CHECKS = 0
FAILS = []


def check(condition, message):
    """Count one check; remember it if it failed (the test keeps going so you see ALL failures)."""
    global CHECKS
    CHECKS += 1
    if not condition:
        FAILS.append(message)
        print("  FAIL:", message)


def report(name):
    """Print a one-line summary for the test file `name`."""
    print(f"{name}: {CHECKS} checks, {len(FAILS)} failed")
    return len(FAILS) == 0

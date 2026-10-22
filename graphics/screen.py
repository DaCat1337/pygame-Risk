"""graphics/screen.py - opening the window, how it is stretched, fullscreen toggle, screenshots.

What it is for : make_screen (1920x1080 logical size), screen_scaling_mode (smooth vs pixel-exact
                 stretching), toggle_fullscreen and save_screenshot.
Uses            : config.py, pygame.
Used by         : main.py, game.py.

"Logical resolution" = the size we DRAW at (always 1920x1080). pygame.SCALED then stretches that
picture to whatever the monitor is and keeps mouse coordinates in our 1920x1080 space.
"""
import os
import time

import pygame

from config import SCREEN_W, SCREEN_H, SCALINGS, WINDOW_SIZE


def screen_scaling_mode(setting_index, desktop=None):
    """Decide how pygame should stretch our 1920x1080 picture to the monitor.

    Returns "photo" (smooth) or None (pixel-exact). AUTO picks pixel-exact only when the monitor
    is a whole multiple of 1920x1080 (1080p = 1x, 4K = 2x): there every pixel becomes a clean
    square. On a 1440p monitor the factor is 1.33, so nearest-neighbour would make uneven
    pixels and we choose the smooth stretch instead. (Copied from game2, compared to 1920x1080.)
    """
    choice = SCALINGS[setting_index]
    if choice == "SMOOTH":
        return "photo"
    if choice == "PIXEL-EXACT":
        return None
    if desktop is None:
        try:
            desktop = pygame.display.get_desktop_sizes()[0]
        except (pygame.error, IndexError, AttributeError):
            return "photo"
    ratio = min(desktop[0] / SCREEN_W, desktop[1] / SCREEN_H)
    return None if abs(ratio - round(ratio)) < 0.01 else "photo"


def apply_scaling_environment(setting_index):
    """Must run BEFORE the window is created. PYGAME_FORCE_SCALE=photo asks pygame to smooth-scale."""
    if screen_scaling_mode(setting_index) == "photo":
        os.environ["PYGAME_FORCE_SCALE"] = "photo"
    else:
        os.environ.pop("PYGAME_FORCE_SCALE", None)


def make_screen(fullscreen=True):
    """Open the 1920x1080 logical screen. Falls back to a plain window if fullscreen fails."""
    if fullscreen:
        try:
            return pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.SCALED | pygame.FULLSCREEN)
        except pygame.error:
            pass
    try:
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.SCALED)
    except pygame.error:
        return pygame.display.set_mode((SCREEN_W, SCREEN_H))
    _shrink_window()
    return screen


def _shrink_window():
    """A SCALED window opens as big as the desktop allows; make it 1600x900 so it fits on screen.
    Uses pygame's window object, which exists in pygame and pygame-ce. Silently skipped if absent."""
    try:
        from pygame._sdl2.video import Window
        Window.from_display_module().size = WINDOW_SIZE
    except Exception:
        pass


def toggle_fullscreen(currently_fullscreen):
    """Switch between fullscreen and a 1600x900 window. Returns the new state (True = fullscreen)."""
    try:
        pygame.display.toggle_fullscreen()
    except pygame.error:
        return currently_fullscreen
    if currently_fullscreen:
        _shrink_window()
    return not currently_fullscreen


def save_screenshot(surface, folder):
    """Save the picture as a PNG in `folder`. Returns the file name, or None if it failed."""
    try:
        os.makedirs(folder, exist_ok=True)
        name = time.strftime("swarm_%Y%m%d_%H%M%S") + f"_{int(time.time() * 1000) % 1000:03d}.png"
        pygame.image.save(surface, os.path.join(folder, name))
        return name
    except (OSError, pygame.error):
        return None

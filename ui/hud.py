"""ui/hud.py - the heads-up display: power bar, timer, track name, beat dots, send %, hints.

What it is for : read-only drawing of match information on top of the world.
Uses            : config.py, core/beat.py, graphics/fonts.py, pygame.
Used by         : ui/screens/play.py.
"""
import pygame

from config import SCREEN_W, SCREEN_H, FACTION_COLORS, FACTION_NAMES, COLOR_NAMES, SEND_FRACTIONS, C_TEXT, C_DIM, PLAYER
from core.beat import beat_of, beat_phase

HINT_TEXT = "Drag from your node to send   |   Wheel / 1-4 = send %   |   Space = all nodes   |   M = music   |   Esc = menu"
BAR_HEIGHT = 10


def format_time(seconds):
    return f"{int(seconds) // 60}:{int(seconds) % 60:02d}"


def draw_power_bar(surf, world):
    """A thin stacked bar across the top: each faction's share of all ships."""
    x = 0.0
    for faction, share in zip(world.factions(), world.shares()):
        width = share * SCREEN_W
        pygame.draw.rect(surf, FACTION_COLORS[faction], (int(x), 0, max(0, int(x + width) - int(x)), BAR_HEIGHT))
        x += width


def draw_hud(surf, world, fonts, track_name, send_index, hints):
    draw_power_bar(surf, world)
    # left: time and track name
    fonts.draw(surf, fonts.hud, format_time(world.seconds), C_TEXT, (36, 30))
    if track_name:
        fonts.draw(surf, fonts.small, "MUSIC: " + track_name, C_DIM, (36, 62))
    # centre: ship counts per faction, in their colours
    totals = world.ship_totals()
    labels = FACTION_NAMES if world.has_player else COLOR_NAMES
    names = [(labels[f], int(totals[f]), FACTION_COLORS[f]) for f in world.factions() if f not in world.eliminated]
    x = SCREEN_W // 2 - 110 * len(names)
    for name, count, color in names:
        fonts.draw(surf, fonts.small, name, color, (x, 28))
        fonts.draw(surf, fonts.hud, str(count), color, (x, 48))
        x += 220
    # right: four beat dots that light up in turn, so the sync is visible
    beat = beat_of(world.ticks)
    glow = 1.0 - beat_phase(world.ticks)
    for k in range(4):
        cx = SCREEN_W - 190 + k * 40
        on = (beat % 4) == k
        level = 0.25 + 0.75 * glow if on else 0.15
        color = tuple(int(c * level) for c in (C_TEXT if k else (255, 255, 255)))
        pygame.draw.circle(surf, color, (cx, 44), 11 if on else 8, 0 if on else 2)
    fonts.draw(surf, fonts.small, f"SEND {int(SEND_FRACTIONS[send_index] * 100)}%", FACTION_COLORS[PLAYER],
               (SCREEN_W - 36, 66), "topright")
    if hints:
        fonts.draw(surf, fonts.small, HINT_TEXT, C_DIM, (SCREEN_W // 2, SCREEN_H - 30), "center")

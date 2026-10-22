"""ui/screens/difficulty.py - the DIFFICULTY page: how smart the computer is, how fast it acts, and how long a match lasts.

What it is for : the title menu has one DIFFICULTY entry that opens this page, so the main menu stays short.
                 There are two kinds of settings, and they are independent:
                   * the COMPUTER: AI LEVEL (how smart and aggressive) and AI REACTION (how quickly it acts);
                   * the BATTLEFIELD, which is the same for both sides: MATCH LENGTH (a preset) and the three brakes it
                     is made of (DEFENCE, CAPTURE UNREST, SHIP SPEED). Editing a brake switches the preset to CUSTOM.
Uses            : config.py, ui/menu.py, graphics/glow.py (dim), pygame.
Used by         : game.py (an overlay on top of the title screen).

Every change is applied at once through Game.set_setting (which keeps the preset and the three brakes in step).
"""
import pygame

from config import (DIFFICULTIES, REACTION_NAMES, PACE_NAMES, DEFENCE_CHOICES, UNREST_CHOICES, SPEED_CHOICES, C_DIM, SCREEN_W,
                    SCREEN_H)
from graphics.glow import dim
from ui.menu import Menu, action, choice

HINTS = {                                    # what the selected row means, shown under the menu
    "difficulty": "How smart and aggressive the computer is: how many attacks it plans at once, how many ships it keeps "
                  "at home, and whether it defends and counter-attacks.",
    "ai_reaction": "How quickly the computer acts: how often it makes decisions and how long it waits before its first move. "
                   "Independent of the level: a smart but slow opponent is possible. (EXTREME already acts as fast as it can.)",
    "pace": "A preset for the three battlefield rules below (they apply to both sides). SHORT: fast, the stronger side snowballs. "
            "LONG: slow and careful.",
    "custom_defence": "Attacking ships needed to remove ONE defender. Higher: every attack costs more, so matches last longer.",
    "custom_unrest": "Beats a freshly captured node makes no ships. Higher: conquering pays off more slowly, less snowballing.",
    "custom_speed": "How fast ships fly. Lower: a longer trip, so the defender has more time to react.",
}


def wrap(text, width=96):
    """Split text into lines of at most `width` characters, at spaces."""
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return lines + [line]


class DifficultyScreen:
    pauses = False

    def __init__(self, game):
        self.game = game
        items = [choice("AI LEVEL", "difficulty", DIFFICULTIES),
                 choice("AI REACTION", "ai_reaction", REACTION_NAMES),
                 choice("MATCH LENGTH", "pace", PACE_NAMES),
                 choice("  DEFENCE (ships per defender)", "custom_defence", [f"{d:g}" for d in DEFENCE_CHOICES]),
                 choice("  CAPTURE UNREST (beats)", "custom_unrest", ["OFF" if u == 0 else str(u) for u in UNREST_CHOICES]),
                 choice("  SHIP SPEED", "custom_speed", [f"{round(s * 100)}%" for s in SPEED_CHOICES]),
                 action("BACK", "back")]
        self.menu = Menu(items, game.fonts, game.settings.get, game.set_setting, sound=game.sfx, title="DIFFICULTY",
                         width=860, center=(SCREEN_W // 2, SCREEN_H // 2 - 40))

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.close()
            return
        result = self.menu.handle_event(e)
        if result and result[0] == "action" and result[1] == "back":
            self.close()

    def close(self):
        self.game.sfx("menu_close")
        self.game.close_overlay()

    def update(self, dt):
        pass

    def draw(self, surf):
        dim(surf, 10)                                           # dark enough that the title menu behind does not disturb the hints
        self.menu.draw(surf)
        fonts = self.game.fonts
        key = self.menu.items[self.menu.sel].key
        for i, line in enumerate(wrap(HINTS.get(key, ""))):
            fonts.draw(surf, fonts.small, line, C_DIM, (self.menu.rect.centerx, self.menu.rect.bottom + 30 + i * 24), "center")
        fonts.draw(surf, fonts.small, "Up/Down select    Left/Right change    Esc back", C_DIM,
                   (self.menu.rect.centerx, SCREEN_H - 40), "center")

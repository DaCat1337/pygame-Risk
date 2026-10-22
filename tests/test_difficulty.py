"""tests/test_difficulty.py - the DIFFICULTY page: AI level, AI reaction speed, and the match-length brakes.

What it is for : proves the AI REACTION dial really changes how the computer acts, that the MATCH LENGTH preset and its
                 three brakes (defence, capture unrest, ship speed) stay in step, and that the page works with keys.
Uses            : core/ai.py, core/world.py, game.py, ui/screens/difficulty.py, config.py.
Used by         : tests/run_all.py.
"""
import tempfile

import helpers
from helpers import check
import pygame

from config import (AI_TABLE, DIFFICULTIES, REACTION_NAMES, PACE, PACE_NAMES, CUSTOM_PACE, DEFENCE_CHOICES, UNREST_CHOICES,
                    SPEED_CHOICES, SHIP_SPEED, apply_pace, preset_choices, matching_preset)
from core.ai import ai_timing, MIN_THINK_EVERY
from core.world import World
from game import Game
from ui.screens.difficulty import DifficultyScreen, wrap


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def run():
    apply_pace(0)

    # --- AI reaction: the table's timing scaled; slower thinks less often and starts later
    for name in DIFFICULTIES:
        slow, normal, fast = (ai_timing(name, r) for r in range(3))
        check(normal == (AI_TABLE[name]["think_every"], AI_TABLE[name]["start_delay"]), f"{name}: NORMAL reaction = the table's own numbers")
        check(slow[0] >= normal[0] >= fast[0] and slow[1] >= normal[1] >= fast[1], f"{name}: slower reaction = thinks less often, starts later")
        check(fast[0] >= MIN_THINK_EVERY and slow[0] > fast[0], f"{name}: never thinks more often than every {MIN_THINK_EVERY} beats, and SLOW is slower than FAST")
    check(ai_timing("EXTREME", 0)[0] == 3 and ai_timing("EXTREME", 1)[0] == 2 == ai_timing("EXTREME", 2)[0],
          "EXTREME thinks every 2 beats: 3 when SLOW, and FAST cannot go faster")
    check(REACTION_NAMES == ("SLOW", "NORMAL", "FAST"), "three reaction speeds")

    # --- the reaction dial changes real matches: the same AI level wins when it is FAST against SLOW (sides swapped)
    def duel(fast_side):
        w = World(seed=3, n_factions=2, map_size=1, has_player=False)
        w.add_opponents(DIFFICULTIES.index("HARD"))
        w.opponents[1].reaction, w.opponents[2].reaction = (2, 0) if fast_side == 1 else (0, 2)
        while not w.over:
            w.tick()
        return w.winner == fast_side
    check(duel(1) and duel(2), "the same level wins when it reacts FAST against SLOW (2 of 2 matches, sides swapped)")

    # --- the preset and its three brakes
    check(matching_preset(*preset_choices(0)) == 0 and matching_preset(*preset_choices(2)) == 2, "each preset is recognised by its three brakes")
    check(matching_preset(0, 1, 0) == CUSTOM_PACE, "any other combination is CUSTOM")
    check(all(d in DEFENCE_CHOICES and u in UNREST_CHOICES and s in SPEED_CHOICES for d, u, s in [(1.0, 0, 1.0), (1.5, 8, 0.77), (2.0, 8, 0.77)]),
          "all presets use values the page can show")

    game = Game(pygame.display.set_mode((1920, 1080)), audio=None, settings_path=None, shots_dir=tempfile.mkdtemp())
    s = game.settings
    check(s["pace"] == 2 and PACE["defence"] == 2.0 and PACE["unrest"] == 8, "the default is LONG and it is live")
    game.set_setting("pace", 0)
    check((s["custom_defence"], s["custom_unrest"], s["custom_speed"]) == preset_choices(0) and PACE["defence"] == 1.0 and PACE["unrest"] == 0
          and PACE["speed"] == SHIP_SPEED, "choosing SHORT copies its brakes into the three rows and makes them live")
    game.set_setting("custom_defence", DEFENCE_CHOICES.index(1.5))
    check(s["pace"] == CUSTOM_PACE and PACE["defence"] == 1.5 and PACE["unrest"] == 0, "editing one brake switches MATCH LENGTH to CUSTOM")
    game.set_setting("custom_unrest", UNREST_CHOICES.index(8))
    game.set_setting("custom_speed", SPEED_CHOICES.index(0.77))
    check(s["pace"] == 1 and PACE_NAMES[s["pace"]] == "MEDIUM", "setting the brakes to MEDIUM's values shows MEDIUM again")
    game.set_setting("custom_speed", SPEED_CHOICES.index(0.65))
    check(s["pace"] == CUSTOM_PACE and abs(PACE["speed"] - SHIP_SPEED * 0.65) < 1e-9, "a speed of 65% is CUSTOM and live")
    game.set_setting("pace", CUSTOM_PACE)
    check(s["custom_speed"] == SPEED_CHOICES.index(0.65) and s["pace"] == CUSTOM_PACE, "choosing CUSTOM keeps the current brakes")

    # --- the settings are used when a match starts
    s["ai_reaction"] = 2
    s["difficulty"] = 2
    game.start_match(11)
    opp = game.play.world.opponents[2]
    check(opp.reaction == 2 and opp.difficulty == 2, "a new match gives the computer the chosen level and reaction")
    check(PACE["defence"] == 1.5 and abs(PACE["speed"] - SHIP_SPEED * 0.65) < 1e-9, "...and the CUSTOM brakes are live")

    # --- a settings file from before this page (only `pace` saved): the preset wins
    game2 = Game(pygame.display.set_mode((1920, 1080)), audio=None, settings_path=None, shots_dir=tempfile.mkdtemp())
    game2.settings["pace"] = 1
    game2.settings["custom_defence"] = 0                      # (a stale value)
    game2.sync_pace()
    check(game2.settings["custom_defence"] == preset_choices(1)[0] and PACE["defence"] == 1.5, "a saved preset overrides stale brake values")

    # --- the page itself, with the keyboard
    game2.enter_title()
    for _ in range(20):
        game2.update(1 / 60)
        game2.draw()
    menu = game2.title.menu
    item = next(it for it in menu.items if it.key == "difficulty")
    check(item.kind == "action" and "MEDIUM" in item.summary() and DIFFICULTIES[game2.settings["difficulty"]] in item.summary(),
          "the title menu shows the current level and match length next to DIFFICULTY")
    menu.sel = menu.items.index(item)
    game2.handle_event(key(pygame.K_RETURN))
    page = game2.overlay
    check(isinstance(page, DifficultyScreen) and not page.pauses, "Enter opens the difficulty page")
    keys = [it.key for it in page.menu.items]
    check(keys == ["difficulty", "ai_reaction", "pace", "custom_defence", "custom_unrest", "custom_speed", "back"], f"the page has the six settings and BACK: {keys}")
    page.menu.sel = keys.index("ai_reaction")
    game2.handle_event(key(pygame.K_LEFT))
    check(game2.settings["ai_reaction"] == 0, "AI REACTION can be set to SLOW")
    page.menu.sel = keys.index("pace")
    game2.handle_event(key(pygame.K_LEFT))
    check(game2.settings["pace"] == 0 and game2.settings["custom_defence"] == preset_choices(0)[0], "MATCH LENGTH to SHORT updates the three rows below it")
    page.menu.sel = keys.index("custom_unrest")
    game2.handle_event(key(pygame.K_RIGHT))
    check(game2.settings["pace"] == CUSTOM_PACE, "changing a brake on the page switches to CUSTOM")
    for _ in range(3):
        game2.update(1 / 60)
        game2.draw()
    row = page.menu.rows[page.menu.sel]
    check(any(game2.screen.get_at((x, row.centery))[:3] != (6, 10, 18) and game2.screen.get_at((x, row.centery))[0] > 150
              for x in range(row.x, row.right, 3)), "the page is drawn: the selected row's text is lit")
    check(game2.screen.get_at((200, 900))[0] < 20, "...and the title menu behind it is dimmed right down")
    page.menu.sel = keys.index("back")
    game2.handle_event(key(pygame.K_RETURN))
    check(game2.overlay is None, "BACK closes the page")
    check(all(len(line) <= 96 for line in wrap("word " * 80)) and wrap("a b") == ["a b"], "hint text wraps into short lines")
    apply_pace(0)                                           # leave the rules at SHORT, like the other rule tests expect


if __name__ == "__main__":
    run()
    raise SystemExit(0 if helpers.report("test_difficulty") else 1)

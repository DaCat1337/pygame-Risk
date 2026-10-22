"""ui/screens/pause.py - the Esc menu (also used for SETTINGS on the title screen).

What it is for : music / sound / display settings plus RESUME, RESTART, QUIT. In a match it pauses
                 the game; opened from the title it is just a settings page.
Uses            : config.py, audio/tracks.py, ui/menu.py.
Used by         : game.py (an overlay drawn on top of the current screen).
"""
import pygame

from audio.tracks import TRACK_NAMES
from config import SCREEN_W, SCREEN_H, SCALINGS, C_DIM
from graphics.glow import dim
from ui.menu import Menu, action, choice, slider, toggle


class PauseScreen:
    def __init__(self, game, from_title=False):
        self.game = game
        self.pauses = not from_title            # Game un-pauses the match when this closes
        items = [] if from_title else [action("RESUME", "resume")]
        items += [toggle("MUSIC", "music_on"),
                  choice("MUSIC TRACK", "music_track", TRACK_NAMES + ["SHUFFLE"]),
                  slider("MUSIC VOLUME", "music_vol"),
                  toggle("DYNAMIC MUSIC", "dynamic_music"),
                  toggle("SOUND EFFECTS", "sfx_on"),
                  slider("EFFECTS VOLUME", "sfx_vol"),
                  toggle("HINTS", "hints"),
                  toggle("BLOOM (GLOW)", "bloom"),
                  toggle("COLOUR-BLIND MODE", "colorblind"),
                  choice("SCREEN SCALING (restart)", "scaling", SCALINGS),
                  action("FULLSCREEN", "fullscreen")]
        if from_title:
            items.append(action("BACK", "resume"))
        else:
            items += [action("RESTART MATCH", "restart"), action("QUIT TO TITLE", "title"),
                      action("QUIT GAME", "quit", danger=True)]
        self.menu = Menu(items, game.fonts, game.settings.get, game.set_setting, sound=game.sfx,
                         title="SETTINGS" if from_title else "PAUSED", width=860, center=(SCREEN_W // 2, SCREEN_H // 2))

    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
            self.game.sfx("menu_close")
            self.game.close_overlay()
            return
        result = self.menu.handle_event(e)
        if result and result[0] == "action":
            self.do(result[1])

    def do(self, action_id):
        game = self.game
        if action_id == "resume":
            game.sfx("menu_close")
            game.close_overlay()
        elif action_id == "fullscreen":
            game.toggle_fullscreen()
        elif action_id == "restart":
            game.close_overlay()
            game.replay_map()
        elif action_id == "title":
            game.close_overlay()
            game.enter_title()
        elif action_id == "quit":
            game.quit()

    def update(self, dt):
        pass

    def draw(self, surf):
        dim(surf, 70)                                                            # darken what is behind
        self.menu.draw(surf)
        fonts = self.game.fonts
        fonts.draw(surf, fonts.small, "Up/Down select    Left/Right change    Enter choose    Esc close", C_DIM,
                   (self.menu.rect.centerx, self.menu.rect.bottom + 28), "center")
        audio = self.game.audio
        if audio is None or not audio.available:
            fonts.draw(surf, fonts.small, "No audio device found - sound is off", (255, 90, 110),
                       (self.menu.rect.centerx, self.menu.rect.bottom + 54), "center")

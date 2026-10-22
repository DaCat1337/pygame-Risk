"""ui/screens/title.py - the title screen with "attract mode" behind it.

What it is for : an AI-vs-AI battle runs dimmed in the background (great for a class demo), with
                 the big pulsing title and the main menu on top.
Uses            : config.py, core/world.py, audio/tracks.py, ui/menu.py, ui/screens/play.py (WorldView).
Used by         : game.py.

Changing the music track here switches the music on the next beat, so you can preview it.
The attract battles run one after another with a CONTINUING beat count, so the music never restarts.
"""
import random

import numpy as np
import pygame

from audio.tracks import TRACK_NAMES
from config import SCREEN_W, SCREEN_H, MAP_NAMES, DIFFICULTIES, C_DIM, FACTION_COLORS, color_choices
from core.beat import beat_phase
from core.world import World
from graphics.glow import dim
from ui.menu import Menu, action, choice
from ui.screens.play import WorldView

TITLE_TEXT = "SWARM CONQUEST"
DIM = 102                                  # background brightness: 102 / 255 = 40%


class TitleScreen:
    def __init__(self, game):
        self.game = game
        self.view = WorldView(game.fonts)
        self.world = None
        self.restart_timer = 0.0
        items = [action("PLAY", "play"),
                 choice("OPPONENTS", "opponents", ("1", "2", "3"), first=1),
                 choice("DIFFICULTY", "difficulty", DIFFICULTIES),
                 choice("MAP", "map_size", MAP_NAMES),
                 choice("MUSIC", "music_track", TRACK_NAMES + ["SHUFFLE"]),
                 choice("YOUR COLOUR", "player_color", lambda: [name for _, name in color_choices(game.settings["colorblind"])],
                        swatch=lambda i: color_choices(game.settings["colorblind"])[i][0]),
                 action("WATCH AI BATTLE", "watch"),
                 action("HOW TO PLAY", "help"),
                 action("SETTINGS", "settings"),
                 action("QUIT", "quit", danger=True)]
        self.menu = Menu(items, game.fonts, game.settings.get, game.set_setting, sound=game.sfx, panel=False,
                         width=760, center=(SCREEN_W // 2, 0), top=400)
        self._title_images = None

    # ------------------------------------------------------------------ attract mode
    def enter(self):
        """Called when the title becomes the current screen: start an attract battle and the music."""
        self.world = None
        self.new_attract()
        self.game.music.begin(self.world)

    def new_attract(self):
        """A fresh computer-vs-computer battle on a random map. The beat count carries on from the last one."""
        previous = self.world
        self.world = World(random.randrange(1_000_000), random.choice((2, 3)), 1, countdown_beats=0, has_player=False)
        self.world.add_opponents(DIFFICULTIES.index("EXTREME"))     # EXTREME vs EXTREME: lively, decisive battles for the background
        if previous is not None:
            self.world.ticks = previous.ticks             # exactly where the last battle stopped: the music must not notice
            self.game.music.follow(self.world)
        self.view.reset(self.world)
        self.restart_timer = 0.0

    # ------------------------------------------------------------------ input
    def handle_event(self, e):
        if e.type == pygame.KEYDOWN and e.key == pygame.K_m:
            self.game.next_track()
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_b:
            self.game.toggle_bloom()
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_c:
            self.game.toggle_colorblind()
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_F1:
            self.game.show_help()
        result = self.menu.handle_event(e)
        if result and result[0] == "action":
            self.do(result[1])

    def do(self, action_id):
        game = self.game
        if action_id == "play":
            game.start_match()
        elif action_id == "watch":
            game.start_match(has_player=False)
        elif action_id == "help":
            game.show_help()
        elif action_id == "settings":
            game.open_settings()
        elif action_id == "quit":
            game.quit()

    # ------------------------------------------------------------------ one frame
    def update(self, dt):
        events = self.game.run_world(self.world, dt)
        self.view.on_events(self.world, events)
        self.game.music.on_events(self.world, events, quiet=True)
        self.view.update(dt)
        if self.world.over:
            self.restart_timer += dt
            if self.restart_timer > 3.0:
                self.new_attract()

    def _build_title_images(self):
        """The title text, plus a blurred copy used as its glow (shrink then enlarge = cheap blur)."""
        fonts = self.game.fonts
        text = fonts.title.render(TITLE_TEXT, True, FACTION_COLORS[1])
        w, h = text.get_size()
        pad = 90                                                    # black margin so the blur can fade out to nothing
        canvas = pygame.Surface((w + 2 * pad, h + 2 * pad))
        canvas.blit(text, (pad, pad))                               # (drawn on opaque black: no transparent pixels to leak colour)
        small = pygame.transform.smoothscale(canvas, (canvas.get_width() // 10, canvas.get_height() // 10))
        halo = pygame.transform.smoothscale(small, canvas.get_size())    # shrink then enlarge = cheap blur
        halos = []                                                  # the glow at 8 brightness steps (70 .. 255 of 255), made once:
        for level in np.linspace(70, 255, 8).astype(int):           # darkening a big picture every frame would be slow
            step = halo.convert()
            step.fill((level, level, level), special_flags=pygame.BLEND_MULT)
            halos.append(step)
        self._title_images = (text, halos)
        panel = pygame.Surface(self.menu.rect.inflate(60, 40).size, pygame.SRCALPHA)       # a dark panel keeps the menu readable
        pygame.draw.rect(panel, (0, 0, 0, 175), panel.get_rect(), border_radius=18)
        self._panel = panel

    def draw(self, surf):
        self.view.bloom = self.game.settings["bloom"]
        self.view.shapes = self.game.settings["colorblind"]
        self.view.draw(surf, self.world)
        dim(surf, DIM)                                                            # dim the battle to 40%
        if self._title_images is None:
            self._build_title_images()
        text, halos = self._title_images
        pulse = 1.0 - beat_phase(self.world.ticks)                                  # biggest glow right on the beat
        glow = halos[int(pulse * pulse * (len(halos) - 1) + 0.5)]                   # one of a few ready-made brightness steps
        centre = (SCREEN_W // 2, 210)
        surf.blit(glow, glow.get_rect(center=centre), special_flags=pygame.BLEND_ADD)
        surf.blit(text, text.get_rect(center=centre))
        fonts = self.game.fonts
        surf.blit(self._panel, self._panel.get_rect(center=self.menu.rect.center))
        self.menu.draw(surf)
        fonts.draw(surf, fonts.small, "Arrows + Enter or mouse     M = next track     F1 = how to play     F11 = fullscreen",
                   C_DIM, (SCREEN_W // 2, SCREEN_H - 36), "center")

"""game.py - the Game class: the main loop, the tick accumulator and the glue between the parts.

What it is for : owns the window, the settings, the screens (title, play) and the overlays on top
                 of them (Esc menu, game over, help). It should read like a table of contents -
                 the details live in the other files.
Uses            : config.py, settings.py, core/world.py, audio/conductor.py, graphics/*, ui/screens/*.
Used by         : main.py.

Each frame:  handle_event(...)  ->  update(dt)  ->  draw()  ->  flip.
Screens have handle_event / update / draw (and enter, when they become current).
"""
import time

import pygame

from audio.conductor import Conductor
from config import apply_palette, FPS_TARGET, DT, MAX_TICKS_PER_FRAME, COUNTDOWN_BEATS, SEND_FRACTIONS, SCREEN_W, SCREEN_H, FADE_SECONDS
from core.world import World
from graphics.fonts import Fonts
from graphics.screen import save_screenshot, toggle_fullscreen
from settings import load_settings, save_settings
from ui.screens.gameover import GameOverScreen
from ui.screens.help import HelpScreen
from ui.screens.pause import PauseScreen
from ui.screens.play import PlayScreen
from ui.screens.title import TitleScreen


class Game:
    def __init__(self, screen, audio=None, settings_path=None, shots_dir=None):
        self.screen = screen
        self.audio = audio                          # None = silent
        self.settings_path = settings_path
        self.shots_dir = shots_dir
        self.settings = load_settings(settings_path)
        apply_palette(self.settings["colorblind"], self.settings["player_color"])           # before the screens are built, so they start with the right colours
        self.fonts = Fonts()
        self.clock = pygame.time.Clock()
        self.running = True
        self.fullscreen = True
        self.bank = 0.0                             # the accumulator ("piggy bank" of real time not yet simulated)
        self._toast = ("", 0.0)
        self.seed = 1
        self.music = Conductor(audio, self.settings)     # music + sound routing (audio/conductor.py)
        self.play = PlayScreen(self)
        self.title = TitleScreen(self)
        self.current = None                         # the screen being shown (title or play)
        self.overlay = None                         # something drawn on top: Esc menu, game over or help
        self.fade = None                            # [phase, seconds, target screen] during a screen transition
        self._black = pygame.Surface((SCREEN_W, SCREEN_H))
        self.enter_title()

    # ------------------------------------------------------------------ screens and transitions
    def go(self, screen):
        """Change screen with a short fade to black and back (0.25 s in total)."""
        if self.current is None:                    # the very first screen just fades in
            self._switch(screen)
            self.fade = ["in", 0.0, screen]
        else:
            self.fade = ["out", 0.0, screen]

    def _switch(self, screen):
        self.current = screen
        self.bank = 0.0
        screen.enter()

    def _update_fade(self, dt):
        phase, seconds, target = self.fade
        seconds += dt
        if seconds >= FADE_SECONDS / 2:
            if phase == "out":
                self._switch(target)
                self.fade = ["in", 0.0, target]
            else:
                self.fade = None
        else:
            self.fade[1] = seconds

    def _draw_fade(self):
        phase, seconds, _ = self.fade
        k = min(1.0, seconds / (FADE_SECONDS / 2))
        self._black.set_alpha(int(255 * (k if phase == "out" else 1.0 - k)))
        self.screen.blit(self._black, (0, 0))

    def enter_title(self):
        self.overlay = None
        self.music.set_paused(False)
        self.go(self.title)

    def start_match(self, seed=None, has_player=True):
        """Create a fresh World and show the play screen. seed=None picks a new random map."""
        self.seed = seed if seed is not None else int(time.time() * 1000) % 1_000_000
        s = self.settings
        world = World(self.seed, s["opponents"] + 1, s["map_size"], countdown_beats=COUNTDOWN_BEATS, has_player=has_player)
        world.add_opponents(s["difficulty"])
        self.overlay = None
        self.music.set_paused(False)                 # a restart from the pause menu must un-pause the sound too
        self.play.start(world)
        self.music.begin(world)
        self.go(self.play)

    def replay_map(self):
        self.start_match(self.seed, has_player=self.play.world.has_player)

    def new_match(self):
        self.start_match(has_player=self.play.world.has_player)

    def open_overlay(self, overlay):
        if self.overlay is None:
            if overlay.pauses:
                self.set_paused(True)
            self.overlay = overlay
            self.sfx("menu_open")

    def close_overlay(self):
        overlay, self.overlay = self.overlay, None
        if overlay is not None and overlay.pauses:
            self.set_paused(False)

    def open_menu(self):
        """Esc during a match: pause and show the menu."""
        if self.current is self.play and not self.play.world.over:
            self.open_overlay(PauseScreen(self))

    def open_settings(self):
        self.open_overlay(PauseScreen(self, from_title=True))

    def show_help(self):
        in_match = self.current is self.play and not self.play.world.over and not self.play.paused
        self.open_overlay(HelpScreen(self, pauses=in_match))

    def show_game_over(self, world):
        self.open_overlay(GameOverScreen(self, world))

    def quit(self):
        self.running = False

    # ------------------------------------------------------------------ time
    def run_world(self, world, dt):
        """The classic accumulator: add the real elapsed time to the bank, then run fixed 1/60 s
        ticks while the bank holds enough. A slow frame just runs a few ticks in a row (at most 8);
        after a long stall (window drag) the bank is clamped so the game never tries to catch up
        minutes of time. Returns the events the World produced."""
        self.bank = min(self.bank + dt, 0.25)
        ticks = 0
        while self.bank >= DT and ticks < MAX_TICKS_PER_FRAME:
            world.tick()
            self.bank -= DT
            ticks += 1
        return world.drain_events()

    def toggle_pause(self):
        self.set_paused(not self.play.paused)

    def set_paused(self, paused):
        """Stop (or resume) the simulation AND the sound. Time spent paused must not count."""
        if paused != self.play.paused:
            self.play.paused = paused
            self.bank = 0.0
            self.music.set_paused(paused)

    # ------------------------------------------------------------------ sound and settings
    def on_world_events(self, world, events):
        """Sound reacts to world events (see audio/conductor.py)."""
        self.music.on_events(world, events)

    def set_setting(self, key, value):
        """Change one setting and apply its side effects (audio, track)."""
        self.settings[key] = value
        self.music.setting_changed(key)
        if key == "music_track":
            self.toast_if_building()
        elif key in ("colorblind", "player_color"):
            self.apply_palette()

    def toast_if_building(self):
        """A track that was never played yet is synthesised in the background (a few seconds): say so."""
        if self.music.active and not self.music.is_ready(self.music.track):
            self.toast("Building the track... it starts on a beat when ready", 4.0)

    def wait_for_music(self):
        """Start-up: the first track takes ~2 s to synthesise. Doing it now (behind a short message) means the
        title music starts at once - built while the game is already drawing, it takes 4x longer and stutters."""
        if self.audio is None or not self.audio.available:
            return
        self.screen.fill((0, 0, 0))
        self.fonts.draw(self.screen, self.fonts.menu, "building the music...", (120, 120, 120),
                        (SCREEN_W // 2, SCREEN_H // 2), "center")
        pygame.display.flip()
        self.audio.join()
        self.clock.tick()                           # restart the frame timer: the wait must not count as one huge frame

    def sfx(self, name, volume=1.0):
        if self.audio is not None:
            self.audio.play(name, volume)

    def track_name(self):
        return self.music.name()

    def next_track(self):
        """M: switch to the next track on the next beat."""
        name = self.music.next_track()
        if not self.music.active:
            self.toast("No audio device - music is off")
        else:
            wait = "" if self.music.is_ready(self.music.track) else "  (building it first, starts when ready)"
            self.toast("Music: " + name + wait, 2.2 if not wait else 4.0)

    def set_send_fraction(self, index):
        self.settings["send_fraction"] = max(0, min(len(SEND_FRACTIONS) - 1, index))

    def toggle_hints(self):
        self.settings["hints"] = not self.settings["hints"]

    def apply_palette(self):
        """Colour-blind mode on / off: change the faction colours and repaint what remembers them."""
        apply_palette(self.settings["colorblind"], self.settings["player_color"])
        self.play.view.palette_changed(self.play.world)
        self.title.view.palette_changed(self.title.world)
        self.title._title_images = None                       # the big title text is cyan = faction 1's colour: draw it again

    def toggle_colorblind(self):
        """C: colour-blind mode (a palette that stays readable with colour blindness, plus a symbol per faction)."""
        self.set_setting("colorblind", not self.settings["colorblind"])
        self.toast("Colour-blind mode " + ("on" if self.settings["colorblind"] else "off"), 1.2)

    def toggle_bloom(self):
        """B: glow (bloom) around nodes, ships and flashes on / off. Everything else keeps its look."""
        self.settings["bloom"] = not self.settings["bloom"]
        self.toast("Bloom " + ("on" if self.settings["bloom"] else "off"), 1.2)

    def flush_settings(self):
        save_settings(self.settings_path, self.settings)

    # ------------------------------------------------------------------ window
    def toggle_fullscreen(self):
        self.fullscreen = toggle_fullscreen(self.fullscreen)

    def save_screenshot(self):
        name = save_screenshot(self.screen, self.shots_dir) if self.shots_dir else None
        self.toast(f"Saved screenshots/{name}" if name else "Could not save the screenshot")
        self.sfx("camera")

    def toast(self, text, seconds=2.2):
        self._toast = (text, time.monotonic() + seconds)

    def toast_text(self):
        text, until = self._toast
        return text if time.monotonic() < until else ""

    # ------------------------------------------------------------------ the loop
    def handle_event(self, e):
        if e.type == pygame.QUIT:
            self.running = False
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_F11:
            self.toggle_fullscreen()
        elif e.type == pygame.KEYDOWN and e.key == pygame.K_F12:
            self.save_screenshot()
        elif self.fade is None or self.fade[0] == "in":          # input is ignored while a screen fades out
            (self.overlay or self.current).handle_event(e)

    def update(self, dt):
        if self.audio is not None:
            self.audio.update()
        if self.fade is not None:
            self._update_fade(dt)
        self.current.update(dt)
        if self.overlay is not None:
            self.overlay.update(dt)

    def draw(self):
        self.current.draw(self.screen)
        if self.overlay is not None:
            self.overlay.draw(self.screen)
        text = self.toast_text()
        if text:
            rect = self.fonts.draw(self.screen, self.fonts.hud, text, (255, 214, 0), (SCREEN_W // 2, 130), "center")
            pygame.draw.rect(self.screen, (255, 214, 0), rect.inflate(30, 14), 1, border_radius=6)
        if self.fade is not None:
            self._draw_fade()

    def run(self):
        try:
            while self.running:
                for e in pygame.event.get():
                    self.handle_event(e)
                self.update(self.clock.tick(FPS_TARGET) / 1000.0)
                self.draw()
                pygame.display.flip()
        finally:
            self.flush_settings()
            pygame.quit()

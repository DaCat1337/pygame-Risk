"""ui/screens/play.py - the playing screen, plus WorldView (how a World is drawn).

What it is for : WorldView paints a World (grid, nodes, ships, effects). PlayScreen adds the HUD,
                 the countdown and the player's input. (The Esc menu and the game-over screen are overlays on top of it.)
Uses            : config.py, core/beat.py, graphics/*, ui/input.py, ui/hud.py.
Used by         : game.py. (WorldView is also used by the title screen's attract mode.)

PlayScreen never changes the rules itself: it asks the World (world.order) and the World decides.
"""
import pygame

from config import SCREEN_W, SCREEN_H, FACTION_COLORS, C_TEXT, C_DIM, PLAYER, SEND_FRACTIONS
from core.beat import beat_phase, is_chord_change
from graphics.draw_nodes import NodeView, draw_nodes, draw_selection
from graphics.draw_ships import draw_ships
from graphics.effects import Effects
from graphics.glow import build_vignette, dim, draw_grid
from graphics.starfield import Starfield
from graphics.territory import Territory
from ui.hud import draw_hud
from ui.input import InputState


class WorldView:
    """Draws a World. It keeps the purely visual state (pulses, sparks, grid flash)."""

    def __init__(self, fonts):
        self.fonts = fonts
        self.bloom = True                          # glow around nodes / ships / flashes (the screens set this from the settings)
        self.vignette = build_vignette()
        self.fx = Effects()
        self.sky = Starfield()                     # nebula + twinkling stars behind everything
        self.territory = Territory()               # a faint colour wash over the area each faction controls
        self.nv = None
        self.grid_flash = 0.0                      # 1.0 right after a chord change, fades to 0
        self.time = 0.0

    def reset(self, world):
        self.nv = NodeView(world.nodes)
        self.fx.clear()
        self.territory.last_owners = None          # (forces a fresh glow for the new map)
        self.territory.update(world, instant=True)
        self.grid_flash, self.time = 0.0, 0.0

    def on_events(self, world, events):
        """React to what the World reported: pulse on the beat, sparks on clashes, rings on captures."""
        for e in events:
            kind = e[0]
            if kind == "beat":
                self.nv.on_beat(world.nodes)
                if is_chord_change(e[1]):
                    self.grid_flash = 1.0
            elif kind == "clash":
                self.fx.clash(e[1], e[2], e[4], e[5], e[3])
            elif kind == "capture":
                node = world.nodes[e[1]]
                self.nv.on_capture(e[1], e[3])
                self.fx.capture(node.x, node.y, FACTION_COLORS[e[3]], node.radius)
                self.territory.update(world)       # the area around that node changes colour

    def update(self, dt):
        self.nv.update(dt)
        self.fx.update()
        self.sky.update(dt)
        self.territory.tick(dt)
        self.grid_flash = max(0.0, self.grid_flash - dt / 0.8)
        self.time += dt

    def draw(self, surf, world, selection=(), hover=None, cursor=None, label=""):
        self.sky.draw(surf)                        # (covers the whole screen, so no fill with C_BG is needed)
        self.territory.draw(surf)
        draw_grid(surf, self.grid_flash)
        draw_nodes(surf, world.nodes, self.nv, self.fonts, self.time, self.bloom)
        draw_ships(surf, world.ships, self.bloom)
        self.fx.draw(surf, self.bloom)
        surf.blit(self.vignette, (0, 0), special_flags=pygame.BLEND_MULT)
        dx, dy = self.fx.shake_offset()
        if dx or dy:
            surf.scroll(dx, dy)                    # a light screen shake
        if selection or hover is not None:
            draw_selection(surf, world.nodes, selection, hover, cursor, label, self.fonts, self.time)


class PlayScreen:
    GAME_OVER_DELAY = 1.6              # seconds the final moment stays visible before the game-over screen opens

    def __init__(self, game):
        self.game = game
        self.view = WorldView(game.fonts)
        self.input = InputState()
        self.world = None
        self.paused = False
        self.over_timer = 0.0
        self.over_shown = False            # the game-over screen opens only once per match

    def start(self, world):
        self.world = world
        self.view.reset(world)
        self.input.clear()
        self.paused = False
        self.over_timer = 0.0
        self.over_shown = False

    def enter(self):
        """Called when this screen becomes the current one."""

    # ------------------------------------------------------------------ input
    def handle_event(self, e):
        world = self.world
        can_command = world.has_player and not world.over and not self.paused
        for action in self.input.handle(e, world, can_command):
            self.perform(action)

    def perform(self, action):
        """Do what the input asked for. The World (not this screen) decides if it is allowed."""
        game, world = self.game, self.world
        kind = action[0]
        if kind == "order":
            if world.order(action[1], action[2], SEND_FRACTIONS[game.settings["send_fraction"]], PLAYER):
                game.sfx("send")
        elif kind == "select":
            game.sfx("click")
        elif kind == "hover":
            game.sfx("hover")
        elif kind == "fraction":
            game.set_send_fraction(action[1])
        elif kind == "fraction_step":
            game.set_send_fraction(game.settings["send_fraction"] + action[1])
        elif kind == "music_next":
            game.next_track()
        elif kind == "pause":
            if not world.over:
                game.toggle_pause()
        elif kind == "menu":
            game.enter_title() if world.over else game.open_menu()
        elif kind == "help":
            game.show_help()
        elif kind == "hints":
            game.toggle_hints()
        elif kind == "bloom":
            game.toggle_bloom()

    # ------------------------------------------------------------------ one frame
    def update(self, dt):
        if self.paused:
            return
        events = self.game.run_world(self.world, dt)
        self.view.on_events(self.world, events)
        self.game.on_world_events(self.world, events)
        self.view.update(dt)
        if self.world.over:                                   # the metronome keeps ticking (fanfare), the screen waits a moment
            self.over_timer += dt
            if self.over_timer >= self.GAME_OVER_DELAY and not self.over_shown:
                self.over_shown = True
                self.game.show_game_over(self.world)

    def draw(self, surf):
        world, inp = self.world, self.input
        label = ""
        if inp.selection and inp.hover is not None and inp.hover not in inp.selection \
                and world.nodes[inp.hover].owner != PLAYER:
            label = f"needs ~{world.needed_to_capture(inp.hover, inp.selection)}"
        self.view.bloom = self.game.settings["bloom"]
        self.view.draw(surf, world, inp.selection, inp.hover, inp.cursor if inp.dragging else None, label)
        draw_hud(surf, world, self.game.fonts, self.game.track_name(), self.game.settings["send_fraction"],
                 self.game.settings["hints"])
        if not world.live:
            self._draw_countdown(surf)
        if self.paused and self.game.overlay is None:
            self._draw_paused(surf)

    def _draw_countdown(self, surf):
        n = self.world.countdown_number()
        pulse = 1.0 - beat_phase(self.world.ticks)                    # brightest right on the beat
        level = int(90 + 165 * pulse)
        self.game.fonts.draw(surf, self.game.fonts.title, str(n), (level, level, level), (SCREEN_W // 2, SCREEN_H // 2), "center")

    def _draw_paused(self, surf):
        dim(surf, 70)
        self.game.fonts.draw(surf, self.game.fonts.title, "PAUSED", C_TEXT, (SCREEN_W // 2, SCREEN_H // 2), "center")
        self.game.fonts.draw(surf, self.game.fonts.menu, "P = continue", C_DIM, (SCREEN_W // 2, SCREEN_H // 2 + 80), "center")

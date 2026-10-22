"""ui/screens/gameover.py - the result screen: VICTORY / DEFEATED, the share graph and the stats.

What it is for : tell the story of the match: who had how big a share of all ships over time,
                 plus a small stats table, the map seed and the "what next" buttons.
Uses            : config.py, core/stats.py (read only), ui/hud.py (format_time), pygame.
Used by         : game.py (an overlay on top of the frozen match).
"""
import pygame

from config import SCREEN_W, FACTION_COLORS, FACTION_NAMES, COLOR_NAMES, PLAYER, C_TEXT, C_DIM, MAP_NAMES, DT
from graphics.glow import dim
from ui.hud import format_time

GRAPH = pygame.Rect(360, 290, 1200, 300)
BUTTONS = [("R", "REPLAY THIS MAP", "replay"), ("ENTER", "NEW MAP", "new"), ("ESC", "TITLE", "title")]


def draw_share_graph(surf, rect, history, factions, fonts):
    """Lines: each faction's share of all ships (0-100%) over the match, as thin glowing lines."""
    pygame.draw.rect(surf, (10, 14, 24), rect, border_radius=8)
    for pct in (0, 25, 50, 75, 100):                                           # faint horizontal guides
        y = rect.bottom - int(rect.h * pct / 100)
        pygame.draw.line(surf, (40, 48, 64) if pct not in (0, 50) else (70, 80, 100), (rect.x, y), (rect.right, y), 1)
        fonts.draw(surf, fonts.small, f"{pct}%", C_DIM, (rect.x - 10, y), "midright")
    pygame.draw.rect(surf, (70, 80, 100), rect, 1, border_radius=8)
    if len(history) < 2:
        fonts.draw(surf, fonts.hud, "not enough data - the match was very short", C_DIM, rect.center, "center")
        return
    t0, t1 = history[0][0], history[-1][0]
    span = max(1, t1 - t0)
    for k, faction in enumerate(factions):
        pts = [(rect.x + (tick - t0) / span * rect.w, rect.bottom - shares[k] * rect.h) for tick, shares in history]
        color = FACTION_COLORS[faction]
        pygame.draw.lines(surf, tuple(c // 3 for c in color), False, pts, 7)    # soft glow under...
        pygame.draw.lines(surf, color, False, pts, 2)                           # ...a thin bright line
    for k in range(5):                                                         # time axis
        tick = t0 + span * k / 4
        fonts.draw(surf, fonts.small, format_time((tick - t0) * DT), C_DIM, (rect.x + rect.w * k / 4, rect.bottom + 8), "midtop")


class GameOverScreen:
    pauses = False

    def __init__(self, game, world):
        self.game = game
        self.world = world
        self.rects = []

    def handle_event(self, e):
        game = self.game
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_r:
                game.close_overlay()
                game.replay_map()
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                game.close_overlay()
                game.new_match()
            elif e.key == pygame.K_ESCAPE:
                game.close_overlay()
                game.enter_title()
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for rect, (_, _, what) in zip(self.rects, BUTTONS):
                if rect.collidepoint(e.pos):
                    game.sfx("click")
                    game.close_overlay()
                    {"replay": game.replay_map, "new": game.new_match, "title": game.enter_title}[what]()

    def update(self, dt):
        pass

    def draw(self, surf):
        world, fonts = self.world, self.game.fonts
        dim(surf, 26)                                                           # the frozen match stays only as a faint shadow
        if world.has_player:
            won = world.result == "win"
            title, color = ("VICTORY", FACTION_COLORS[PLAYER]) if won else ("DEFEATED", FACTION_COLORS[world.winner or 2])
        else:
            title, color = f"{COLOR_NAMES[world.winner]} WINS", FACTION_COLORS[world.winner]
        fonts.draw(surf, fonts.title, title, color, (SCREEN_W // 2, 130), "center")
        fonts.draw(surf, fonts.hud, f"{format_time(world.seconds)}   |   map {MAP_NAMES[world.map_size]}   |   seed {world.seed}",
                   C_DIM, (SCREEN_W // 2, 215), "center")
        fonts.draw(surf, fonts.hud, "share of all ships over time", C_TEXT, (GRAPH.x, GRAPH.y - 30), "midleft")
        draw_share_graph(surf, GRAPH, world.stats.history, list(world.factions()), fonts)
        self._draw_table(surf, 690)
        self._draw_buttons(surf, 930)

    def _draw_table(self, surf, top):
        fonts, stats = self.game.fonts, self.world.stats
        columns = [("", 360), ("NODES CAPTURED", 700), ("SHIPS LAUNCHED", 910), ("SHIPS LOST", 1110), ("PEAK NODES", 1280)]
        for text, x in columns:
            fonts.draw(surf, fonts.small, text, C_DIM, (x, top), "midleft")
        for row, faction in enumerate(self.world.factions()):
            y = top + 36 + row * 36
            color = FACTION_COLORS[faction]
            name = (FACTION_NAMES if self.world.has_player else COLOR_NAMES)[faction]
            name += "  (eliminated)" if faction in self.world.eliminated else ""
            fonts.draw(surf, fonts.hud, name, color, (columns[0][1], y), "midleft")
            for value, (_, x) in zip((stats.captured[faction], stats.launched[faction], stats.lost[faction],
                                      stats.peak_nodes[faction]), columns[1:]):
                fonts.draw(surf, fonts.hud, str(value), C_TEXT, (x, y), "midleft")

    def _draw_buttons(self, surf, y):
        fonts = self.game.fonts
        self.rects = []
        x = SCREEN_W // 2 - 540
        mouse = pygame.mouse.get_pos()
        for key, label, _ in BUTTONS:
            rect = pygame.Rect(x, y - 28, 340, 56)
            hot = rect.collidepoint(mouse)
            pygame.draw.rect(surf, (20, 40, 56) if hot else (10, 16, 26), rect, border_radius=10)
            pygame.draw.rect(surf, FACTION_COLORS[PLAYER] if hot else (70, 80, 100), rect, 2, border_radius=10)
            fonts.draw(surf, fonts.hud, f"{key}  {label}", C_TEXT, rect.center, "center")
            self.rects.append(rect)
            x += 370

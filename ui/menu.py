"""ui/menu.py - a small reusable Menu: toggles, sliders, choices and action buttons.

What it is for : one class used by the title menu AND the Esc menu (and the game-over buttons).
                 It works with keyboard (arrows, Enter) and mouse (hover, click, drag sliders).
Uses            : config.py, graphics/fonts.py, pygame.
Used by         : ui/screens/title.py, ui/screens/pause.py, ui/screens/gameover.py.

The menu never stores the settings itself. You give it two little functions:
    get(key) -> current value        set_value(key, value) -> change it
so the same menu can edit the Game's settings dictionary (and the Game can react, e.g. change the music).
handle_event() returns None, ("changed", key) or ("action", id).
"""
from dataclasses import dataclass

import pygame

from config import C_TEXT, C_DIM, FACTION_COLORS

ACCENT = FACTION_COLORS[1]
DANGER = (255, 90, 110)
WARM = (255, 214, 0)


@dataclass
class Item:
    kind: str                  # "toggle", "slider", "choice" or "action"
    label: str
    key: str = ""              # settings key (toggle / slider / choice) or action id
    labels: object = ()        # choice: the text of each option (a tuple, or a function returning one, for options that change)
    first: int = 0             # choice: the setting value of the first option (opponents start at 1)
    danger: bool = False       # drawn in red (quit)
    swatch: object = None      # choice: optional function(index) -> RGB; the value is then drawn in that colour with a dot


def toggle(label, key):
    return Item("toggle", label, key)


def slider(label, key):
    return Item("slider", label, key)


def choice(label, key, labels, first=0, swatch=None):
    return Item("choice", label, key, labels if callable(labels) else tuple(labels), first, swatch=swatch)


def action(label, action_id, danger=False):
    return Item("action", label, action_id, danger=danger)


class Menu:
    ROW_H = 50

    def __init__(self, items, fonts, get, set_value, sound=None, title="", panel=True, width=860, center=(960, 540),
                 top=None):
        self.items, self.fonts, self.get, self.set_value = items, fonts, get, set_value
        self.sound = sound or (lambda name: None)
        self.title, self.panel = title, panel
        self.sel = 0
        self.drag = None                                       # index of the slider being dragged
        header = 90 if title else 20
        height = header + len(items) * self.ROW_H + 24
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = center
        if top is not None:
            self.rect.top = top
        self.rows = [pygame.Rect(self.rect.x + 24, self.rect.y + header + i * self.ROW_H, width - 48, self.ROW_H - 4)
                     for i in range(len(items))]

    # ------------------------------------------------------------------ values
    @staticmethod
    def labels_of(item):
        return tuple(item.labels()) if callable(item.labels) else item.labels

    def value_text(self, item):
        v = self.get(item.key)
        if item.kind == "choice":
            labels = self.labels_of(item)
            return labels[max(0, min(len(labels) - 1, int(v) - item.first))]
        if item.kind == "slider":
            return f"{int(round(float(v) * 100))}%"
        return ""

    def slider_track(self, row):
        return pygame.Rect(row.centerx - 20, row.centery - 4, row.w // 2 - 70, 8)

    def adjust(self, i, d):
        """Left/right (d = -1/+1) on item i."""
        item = self.items[i]
        if item.kind == "slider":
            v = min(1.0, max(0.0, round(float(self.get(item.key)) + 0.05 * d, 2)))
            self.set_value(item.key, v)
            self.sound("tick")
        elif item.kind == "choice":
            n = len(self.labels_of(item))
            index = (int(self.get(item.key)) - item.first + d) % n
            self.set_value(item.key, item.first + index)
            self.sound("tick")
        elif item.kind == "toggle":
            return self.activate(i)
        else:
            return None
        return ("changed", item.key)

    def activate(self, i):
        """Enter / click on item i."""
        item = self.items[i]
        if item.kind == "toggle":
            on = not self.get(item.key)
            self.set_value(item.key, on)
            self.sound("on" if on else "off")
            return ("changed", item.key)
        if item.kind == "choice":
            return self.adjust(i, 1)
        if item.kind == "action":
            self.sound("click")
            return ("action", item.key)
        return None

    # ------------------------------------------------------------------ events
    def _slider_to_mouse(self, i, x):
        track = self.slider_track(self.rows[i])
        self.set_value(self.items[i].key, round(min(1.0, max(0.0, (x - track.x) / track.w)), 2))

    def handle_event(self, e):
        n = len(self.items)
        if e.type == pygame.KEYDOWN:
            if e.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % n
                self.sound("hover")
            elif e.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % n
                self.sound("hover")
            elif e.key in (pygame.K_LEFT, pygame.K_a):
                return self.adjust(self.sel, -1)
            elif e.key in (pygame.K_RIGHT, pygame.K_d):
                return self.adjust(self.sel, 1)
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self.activate(self.sel)
        elif e.type == pygame.MOUSEMOTION:
            if self.drag is not None:
                self._slider_to_mouse(self.drag, e.pos[0])
                return ("changed", self.items[self.drag].key)
            for i, row in enumerate(self.rows):
                if row.collidepoint(e.pos) and i != self.sel:
                    self.sel = i
                    self.sound("hover")
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            for i, row in enumerate(self.rows):
                if row.collidepoint(e.pos):
                    self.sel = i
                    if self.items[i].kind == "slider":
                        self.drag = i
                        self._slider_to_mouse(i, e.pos[0])
                        return ("changed", self.items[i].key)
                    return self.activate(i)
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            if self.drag is not None:
                key = self.items[self.drag].key
                self.drag = None
                self.sound("tick")
                return ("changed", key)
        elif e.type == pygame.MOUSEWHEEL:
            mouse = pygame.mouse.get_pos()
            for i, row in enumerate(self.rows):
                if row.collidepoint(mouse) and self.items[i].kind in ("slider", "choice"):
                    return self.adjust(i, 1 if e.y > 0 else -1)
        return None

    # ------------------------------------------------------------------ drawing
    def draw(self, surf):
        fonts = self.fonts
        if self.panel:
            box = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            pygame.draw.rect(box, (6, 10, 18, 235), box.get_rect(), border_radius=14)
            pygame.draw.rect(box, (*ACCENT, 200), box.get_rect(), 2, border_radius=14)
            surf.blit(box, self.rect.topleft)
        if self.title:
            fonts.draw(surf, fonts.menu, self.title, ACCENT, (self.rect.centerx, self.rect.y + 44), "center")
        for i, (item, row) in enumerate(zip(self.items, self.rows)):
            selected = i == self.sel
            if selected:
                hl = pygame.Surface(row.size, pygame.SRCALPHA)
                pygame.draw.rect(hl, (*ACCENT, 34), hl.get_rect(), border_radius=8)
                pygame.draw.rect(hl, (*ACCENT, 170), hl.get_rect(), 1, border_radius=8)
                surf.blit(hl, row.topleft)
            color = DANGER if item.danger else (WARM if selected else C_TEXT)
            if item.kind == "action":
                fonts.draw(surf, fonts.menu, item.label, color, (row.x + 20, row.centery), "midleft")
                continue
            fonts.draw(surf, fonts.menu, item.label, color, (row.x + 20, row.centery), "midleft")
            self._draw_value(surf, item, row, selected)

    def _draw_value(self, surf, item, row, selected):
        fonts = self.fonts
        if item.kind == "toggle":
            on = bool(self.get(item.key))
            chip = pygame.Rect(row.right - 92, row.centery - 14, 72, 28)
            pygame.draw.rect(surf, (0, 90, 70) if on else (60, 30, 40), chip, border_radius=14)
            knob = chip.right - 15 if on else chip.x + 15
            pygame.draw.circle(surf, (0, 230, 118) if on else DANGER, (knob, chip.centery), 9)
        elif item.kind == "slider":
            track = self.slider_track(row)
            v = float(self.get(item.key))
            pygame.draw.rect(surf, (30, 50, 60), track, border_radius=4)
            pygame.draw.rect(surf, ACCENT, pygame.Rect(track.x, track.y, int(track.w * v), track.h), border_radius=4)
            pygame.draw.circle(surf, WARM if selected else C_TEXT, (track.x + int(track.w * v), track.centery), 11)
            fonts.draw(surf, fonts.menu, self.value_text(item), C_TEXT, (row.right - 20, row.centery), "midright")
        elif item.kind == "choice":
            color = ACCENT
            if item.swatch:                                          # e.g. YOUR COLOUR: the value is shown in that colour
                color = item.swatch(max(0, int(self.get(item.key)) - item.first))
            text = fonts.draw(surf, fonts.menu, self.value_text(item), color, (row.right - 60, row.centery), "midright")
            cy = row.centery
            if item.swatch:
                pygame.draw.circle(surf, color, (text.x - 52, cy), 10)
            pygame.draw.polygon(surf, C_DIM, [(text.x - 26, cy), (text.x - 12, cy - 10), (text.x - 12, cy + 10)])      # left arrow
            pygame.draw.polygon(surf, C_DIM, [(row.right - 26, cy), (row.right - 40, cy - 10), (row.right - 40, cy + 10)])  # right arrow

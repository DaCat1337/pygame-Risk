"""ui/input.py - turns mouse and keyboard events into simple "actions".

What it is for : InputState remembers what is selected / being dragged and returns a list of
                 action tuples. It never changes the game itself - game.py and play.py do that.
                 (The client only ASKS; the World decides.)
Uses            : config.py, pygame.
Used by         : ui/screens/play.py.

Actions it returns:
  ("select",) ("hover",) ("order", [source nodes], target) ("fraction", index) ("fraction_step", +1/-1)
  ("music_next",) ("pause",) ("menu",) ("help",) ("hints",)
(F11 fullscreen and F12 screenshot work on every screen, so game.py handles them.)

Mouse: press on your node = select, drag over more of your nodes to add them, release over
another node = send. A plain click on your node selects it; the next click on any node is the target.
"""
import math

import pygame

from config import PLAYER, SELECT_PAD

KEY_ACTIONS = {pygame.K_m: "music_next", pygame.K_p: "pause", pygame.K_ESCAPE: "menu", pygame.K_F1: "help",
               pygame.K_h: "hints", pygame.K_b: "bloom", pygame.K_c: "colorblind"}
FRACTION_KEYS = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3,
                 pygame.K_KP1: 0, pygame.K_KP2: 1, pygame.K_KP3: 2, pygame.K_KP4: 3}


def node_at(nodes, pos, pad=SELECT_PAD):
    """Index of the node under `pos` (clicking works up to `pad` pixels outside the edge), or None.
    If several qualify, the one whose edge is closest wins."""
    best, best_gap = None, None
    for i, n in enumerate(nodes):
        gap = math.hypot(pos[0] - n.x, pos[1] - n.y) - n.radius
        if gap <= pad and (best_gap is None or gap < best_gap):
            best, best_gap = i, gap
    return best


class InputState:
    def __init__(self):
        self.selection = []        # node indices the player has selected
        self.dragging = False      # mouse button is down after pressing on an own node
        self.sticky = False        # selection waits for the next click (after Space or a plain click)
        self.press_node = None     # the node the current drag started on
        self.hover = None          # node under the cursor
        self.cursor = (0, 0)

    def clear(self):
        self.selection, self.dragging, self.sticky, self.press_node = [], False, False, None

    def handle(self, e, world, can_command=True):
        """Process one pygame event; returns a list of action tuples (usually empty)."""
        actions = []
        if e.type == pygame.KEYDOWN:
            self._key(e, world, can_command, actions)
        elif e.type == pygame.MOUSEWHEEL and e.y:
            actions.append(("fraction_step", 1 if e.y > 0 else -1))
        elif e.type == pygame.MOUSEMOTION:
            self._motion(e, world, can_command, actions)
        elif e.type == pygame.MOUSEBUTTONDOWN and can_command:
            if e.button == 1:
                self._press(e, world, actions)
            elif e.button == 3:
                self.clear()
        elif e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self.dragging:
            self._release(e, world, actions)
        return actions

    # ------------------------------------------------------------------ pieces
    def _key(self, e, world, can_command, actions):
        if e.key in FRACTION_KEYS:
            actions.append(("fraction", FRACTION_KEYS[e.key]))
        elif e.key == pygame.K_SPACE and can_command:
            self.selection = world.owned(PLAYER)              # "all my nodes", then click a target
            self.sticky, self.dragging = bool(self.selection), False
            if self.selection:
                actions.append(("select",))
        elif e.key in KEY_ACTIONS:
            actions.append((KEY_ACTIONS[e.key],))

    def _motion(self, e, world, can_command, actions):
        self.cursor = e.pos
        hit = node_at(world.nodes, e.pos)
        if hit != self.hover:
            self.hover = hit
            if hit is not None:
                actions.append(("hover",))
        # dragging over more of your own nodes adds them to the selection
        if (can_command and self.dragging and hit is not None and world.nodes[hit].owner == PLAYER
                and hit not in self.selection):
            self.selection.append(hit)
            actions.append(("select",))

    def _press(self, e, world, actions):
        hit = node_at(world.nodes, e.pos)
        shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
        if self.sticky and not shift:
            if hit is not None:                               # the waiting selection now has its target
                actions.append(("order", [s for s in self.selection if s != hit], hit))
            self.clear()
        elif hit is not None and world.nodes[hit].owner == PLAYER:
            if shift and hit in self.selection:
                self.selection.remove(hit)
            elif shift:
                self.selection.append(hit)
            else:
                self.selection = [hit]
            self.dragging, self.sticky, self.press_node = True, False, hit
            actions.append(("select",))
        elif not shift:
            self.clear()

    def _release(self, e, world, actions):
        self.dragging = False
        hit = node_at(world.nodes, e.pos)
        if hit is None:
            self.clear()                                      # released over empty space = cancel
        elif hit == self.press_node:
            self.sticky = True                                # plain click: now click a target
        else:
            actions.append(("order", [s for s in self.selection if s != hit], hit))
            self.clear()

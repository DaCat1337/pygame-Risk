"""config.py - EVERY number you might want to tweak lives here.

What it is for : one place for screen size, colours, timing (the beat), balance and the AI table.
Uses            : nothing (it is the bottom of the import chain).
Used by         : every other file.

Tip for class: change a number here, restart the game, and see what happens.
"""

# --- screen -----------------------------------------------------------------
SCREEN_W, SCREEN_H = 1920, 1080          # logical resolution: all pixel numbers below are for this
FPS_TARGET = 60
WINDOW_SIZE = (1600, 900)                # size of the window after F11 (fits a 1080p desktop with a taskbar)
SCALINGS = ("AUTO", "SMOOTH", "PIXEL-EXACT")   # how the 1920x1080 picture is stretched to the monitor

# --- the beat clock (see core/beat.py) ----------------------------------------
BEAT = 0.5                               # seconds per beat = 120 BPM
STEP = BEAT / 2                          # an eighth note
DT = 1 / 60                              # fixed simulation step in seconds
TICKS_PER_BEAT = 30                      # BEAT / DT
TICKS_PER_STEP = 15                      # STEP / DT
BEATS_PER_CHORD = 16
CHORDS_PER_LOOP = 4
LOOP_BEATS = BEATS_PER_CHORD * CHORDS_PER_LOOP     # 64 beats = 32 seconds
MAX_TICKS_PER_FRAME = 8                  # catch-up limit after a slow frame
COUNTDOWN_BEATS = 3                      # "3-2-1" before a match starts producing

# --- factions and colours -----------------------------------------------------
NEUTRAL, PLAYER = 0, 1
FACTION_COLORS = {
    0: (110, 110, 125),                  # neutral grey
    1: (0, 230, 255),                    # player cyan
    2: (255, 60, 140),                   # magenta
    3: (255, 180, 0),                    # amber
    4: (150, 255, 80),                   # lime
}
FACTION_NAMES = {0: "NEUTRAL", 1: "YOU", 2: "MAGENTA", 3: "AMBER", 4: "LIME"}
COLOR_NAMES = {0: "NEUTRAL", 1: "CYAN", 2: "MAGENTA", 3: "AMBER", 4: "LIME"}   # used when nobody is "you" (watch mode)
C_BG = (0, 0, 0)
C_TEXT = (235, 240, 255)
C_DIM = (120, 130, 150)

# --- nodes ----------------------------------------------------------------------
NODE_RADIUS = {1: 24, 2: 39, 3: 57}
CAP_PER_SIZE = 40                        # a node holds at most 40 * size ships from production
START_SIZE = 3
START_GARRISON = 30
NEUTRAL_GARRISON_PER_SIZE = (4, 11)      # neutral garrison = size * randint(4, 10)

# --- map generation -------------------------------------------------------------
MAP_NAMES = ("SMALL", "MEDIUM", "LARGE")
MAP_NODES = (12, 18, 26)                 # nodes per map size, start nodes included
MARGIN = 90                              # keep nodes this far from the screen edges...
HUD_TOP = 100                            # ...plus this much extra at the top for the HUD bar
MIN_NODE_GAP = 42                        # smallest gap between two node edges
SIZE_MIX = (0.50, 0.35, 0.15)            # share of size 1 / 2 / 3 among the non-start nodes
MAPGEN_MAX_TRIES = 2000

# --- ships ------------------------------------------------------------------------
MAX_SHIPS = 3000                         # array capacity
MAX_FLIGHT_PER_FACTION = 1200            # ships one faction may have flying at once
SHIP_SPEED = 195.0                       # pixels per second
LANE_SPREAD = 0.6                        # lane offset = +-0.6 * target radius (makes streams, not lines)
SEND_FRACTIONS = (0.25, 0.5, 0.75, 1.0)
DEFAULT_SEND_INDEX = 1                   # 50%

# --- mid-air combat -----------------------------------------------------------------
CLASH_DIST = 10                          # ships of different owners this close annihilate
CLASH_CELL = 21                          # grid cell size used to find them quickly (2 * CLASH_DIST + 1)

# --- match rules ---------------------------------------------------------------------
MATCH_LIMIT_SECONDS = 12 * 60            # after this the faction with the most nodes wins
STATS_EVERY_BEATS = 2                    # share graph sample rate

# --- computer opponents (see core/ai.py): tweak live in class! -------------------------
DIFFICULTIES = ("EASY", "NORMAL", "HARD")
AI_TABLE = {
    # think_every: beats between decisions | max_orders: attack/defend missions per decision |
    # reserve: share of each garrison kept at home | start_delay: beats the AI waits before its first move |
    # defends: reacts to attacks | counter: counter-attacks the attacker's weakest node
    "EASY":   {"think_every": 10, "max_orders": 1, "reserve": 0.60, "start_delay": 24, "defends": False, "counter": False},
    "NORMAL": {"think_every": 4,  "max_orders": 1, "reserve": 0.40, "start_delay": 10, "defends": True,  "counter": False},
    "HARD":   {"think_every": 2,  "max_orders": 2, "reserve": 0.25, "start_delay": 0,  "defends": True,  "counter": True},
}
AI_PLAYER_BIAS_HARD = 1.15               # HARD likes to attack the player a bit more
AI_SURPLUS = 1.2                         # send needed * 1.2 + 3 ships to be safe
AI_SURPLUS_FLAT = 3

# --- look and feel ----------------------------------------------------------------------
GRID_SPACING = 60
GRID_BRIGHTNESS = 0.08
GRID_FLASH_BRIGHTNESS = 0.18
PULSE_PIXELS = 3                         # node outline pops this much on every beat (kept small: it happens every 0.5 s)
PULSE_DECAY = 0.15                       # seconds for the pop to fade
CAPTURE_FADE = 0.3                       # seconds the colour cross-fade takes
SELECT_PAD = 15                          # clicking a node works this many pixels outside its edge
FONT_HUD, FONT_MENU, FONT_TITLE = 22, 30, 96
FONT_NODE = {1: 22, 2: 26, 3: 32}
SHAKE_PIXELS = 3
FADE_SECONDS = 0.25                      # screen transitions

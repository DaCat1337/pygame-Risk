"""settings.py - load, validate and save settings.json (next to main.py).

What it is for : remember volume, track, opponents, ... between runs. A broken or hand-edited
                 file can never crash the game: every bad value just becomes the default.
Uses            : config.py, audio/tracks.py (how many tracks exist), json.
Used by         : main.py, game.py.
"""
import json

from audio.tracks import SHUFFLE
from config import SCALINGS

DEFAULT_SETTINGS = {
    "music_on": True, "music_vol": 0.5, "music_track": 0,     # 0 = first track ... SHUFFLE (= number of tracks) = random
    "sfx_on": True, "sfx_vol": 0.7,
    "hints": True, "bloom": True, "scaling": 0,                             # scaling: index into config.SCALINGS
    "opponents": 1,                                           # 1..3
    "difficulty": 1,                                          # 0 EASY, 1 NORMAL, 2 HARD
    "map_size": 1,                                            # 0 SMALL, 1 MEDIUM, 2 LARGE
    "send_fraction": 1,                                       # index: 0 = 25%, 1 = 50%, 2 = 75%, 3 = 100%
}

# allowed (lowest, highest) for the whole-number settings
INT_RANGES = {"music_track": (0, SHUFFLE), "scaling": (0, len(SCALINGS) - 1), "opponents": (1, 3),
              "difficulty": (0, 2), "map_size": (0, 2), "send_fraction": (0, 3)}


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)     # True/False are ints in Python: exclude


def load_settings(path):
    """Read saved settings. Anything missing, of the wrong type or out of range becomes the default
    (volumes outside 0..1 are clamped, like in game2)."""
    result = dict(DEFAULT_SETTINGS)
    if not path:
        return result
    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
        if not isinstance(raw, dict):
            return result
    except (OSError, ValueError):
        return result
    for key, default in DEFAULT_SETTINGS.items():
        value = raw.get(key, default)
        if isinstance(default, bool):
            if isinstance(value, bool):
                result[key] = value
        elif key in INT_RANGES:
            lo, hi = INT_RANGES[key]
            if isinstance(value, int) and not isinstance(value, bool) and lo <= value <= hi:
                result[key] = value
        elif _is_number(value):
            result[key] = min(1.0, max(0.0, float(value)))
    return result


def save_settings(path, settings):
    """Write settings.json. A read-only folder just means settings are not remembered."""
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(settings, fh, indent=2)
    except OSError:
        pass

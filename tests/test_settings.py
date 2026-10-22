"""tests/test_settings.py - a broken settings.json must never crash and must give sane values."""
import json
import os
import tempfile

import helpers
from helpers import check
from settings import load_settings, save_settings, DEFAULT_SETTINGS


def _load_text(text):
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "settings.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return load_settings(path)


def run():
    check(load_settings(None) == DEFAULT_SETTINGS, "no path = defaults")
    check(load_settings(os.path.join(tempfile.gettempdir(), "no_such_dir_xyz", "s.json")) == DEFAULT_SETTINGS, "missing file = defaults")
    check(_load_text("{ this is not json") == DEFAULT_SETTINGS, "garbage text = defaults")
    check(_load_text("[1, 2, 3]") == DEFAULT_SETTINGS, "JSON that is not an object = defaults")
    check(_load_text("") == DEFAULT_SETTINGS, "empty file = defaults")

    bad_types = {"music_on": "yes", "music_vol": "loud", "music_track": "2", "sfx_on": 1, "sfx_vol": None,
                 "hints": [], "bloom": 1, "scaling": 1.5, "opponents": True, "difficulty": {}, "map_size": "big", "send_fraction": None}
    check(_load_text(json.dumps(bad_types)) == DEFAULT_SETTINGS, "wrong types = defaults")

    out_of_range = {"music_track": 5, "scaling": 3, "opponents": 0, "difficulty": -1, "map_size": 3, "send_fraction": 4}
    check(_load_text(json.dumps(out_of_range)) == DEFAULT_SETTINGS, "out-of-range whole numbers = defaults")
    check(_load_text(json.dumps({"music_track": -1}))["music_track"] == 0, "music_track -1 = default")
    check(_load_text(json.dumps({"music_track": 4}))["music_track"] == 4, "music_track 4 (SHUFFLE) is valid")

    loud = _load_text(json.dumps({"music_vol": 7, "sfx_vol": -3}))
    check(loud["music_vol"] == 1.0 and loud["sfx_vol"] == 0.0, "volumes are clamped to 0..1")

    good = {"music_on": False, "music_vol": 0.2, "music_track": 3, "sfx_on": False, "sfx_vol": 0.9, "hints": False, "bloom": False,
            "scaling": 2, "opponents": 3, "difficulty": 2, "map_size": 0, "send_fraction": 3}
    check(_load_text(json.dumps(good)) == good, "valid settings are kept exactly")
    check(_load_text(json.dumps({"music_vol": 0.3, "extra": 1}))["music_vol"] == 0.3, "unknown keys are ignored")
    check(_load_text(json.dumps({"music_vol": 0.3}))["bloom"] is True, "a settings file from before the bloom option gets bloom on")

    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "s.json")
        save_settings(path, good)
        check(load_settings(path) == good, "save then load round-trips")
        save_settings(os.path.join(folder, "missing", "s.json"), good)
        check(True, "saving into a missing folder does not crash")


if __name__ == "__main__":
    run()
    raise SystemExit(0 if helpers.report("test_settings") else 1)

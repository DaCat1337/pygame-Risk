"""tests/run_all.py - runs every test file and prints ALL TESTS PASSED (N checks).

Start it from the game4 folder:   python -B tests\\run_all.py
Each test file is also runnable on its own, e.g.   python -B tests\\test_world.py

Every test file defines run() and uses tests/helpers.check().
"""
import importlib
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import helpers  # noqa: E402  (must come first: sets the dummy SDL drivers and sys.path)

# Test files, in the order they are run. Missing files are skipped, so early phases work too.
TEST_FILES = ["test_beat", "test_mapgen", "test_world", "test_combat", "test_ai", "test_audio",
              "test_settings", "test_game", "test_visuals", "test_perf"]


def main():
    start = time.time()
    for name in TEST_FILES:
        if not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), name + ".py")):
            print(f"{name}: (not written yet)")
            continue
        before = helpers.CHECKS
        module = importlib.import_module(name)
        module.run()
        print(f"{name}: {helpers.CHECKS - before} checks")
    seconds = time.time() - start
    if helpers.FAILS:
        print(f"\n{len(helpers.FAILS)} FAILED of {helpers.CHECKS} checks:")
        for message in helpers.FAILS:
            print("  -", message)
        sys.exit(1)
    print(f"\nALL TESTS PASSED ({helpers.CHECKS} checks, {seconds:.1f} s)")


if __name__ == "__main__":
    main()

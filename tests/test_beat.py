"""tests/test_beat.py - the metronome maths in core/beat.py (note_hz is tested in test_audio)."""
import helpers
from helpers import check
from core import beat


def run():
    check(beat.beat_of(0) == 0 and beat.beat_of(29) == 0 and beat.beat_of(30) == 1, "a beat is 30 ticks")
    check(beat.step_of(14) == 0 and beat.step_of(15) == 1 and beat.step_of(30) == 2, "a step is 15 ticks")
    check(beat.is_beat_tick(0) and beat.is_beat_tick(60) and not beat.is_beat_tick(15), "beat ticks")
    check(beat.is_step_tick(15) and not beat.is_step_tick(16), "step ticks")
    check(beat.beat_phase(0) == 0.0 and abs(beat.beat_phase(15) - 0.5) < 1e-9, "beat phase 0..1")
    check([beat.chord_of(b) for b in (0, 15, 16, 32, 48, 63, 64)] == [0, 0, 1, 2, 3, 3, 0], "chord changes every 16 beats and loops after 64")
    check(beat.chord_of_step(31) == 0 and beat.chord_of_step(32) == 1, "chord of a step")
    check(beat.is_chord_change(16) and not beat.is_chord_change(17), "chord change beats")
    check(beat.loop_beat(65) == 1, "music loop is 64 beats")

    # voice slots: alive factions take turns on the eighth notes
    two = [beat.voice_slot(s, [1, 2]) for s in range(4)]
    check([f for f, _ in two] == [1, 2, 1, 2], "2 factions: call and response")
    check([t for _, t in two] == [0, 0, 1, 1], "2 factions: the tone advances every second step")
    three = [beat.voice_slot(s, [1, 2, 3])[0] for s in range(6)]
    check(three == [1, 2, 3, 1, 2, 3], "3 factions take turns")
    four = [beat.voice_slot(s, [1, 2, 3, 4])[0] for s in range(8)]
    check(four == [1, 2, 3, 4, 1, 2, 3, 4], "4 factions take turns")
    check(all(f != 2 for f, _ in (beat.voice_slot(s, [1, 3, 4]) for s in range(60))), "an eliminated faction never gets a slot")
    check(all(f == 1 for f, _ in (beat.voice_slot(s, [1]) for s in range(20))), "the lone winner plays every step")
    check(beat.voice_slot(5, []) is None, "nobody alive = no voice")
    tones = {beat.voice_slot(s, [1])[1] for s in range(16)}
    check(tones == {0, 1, 2, 3}, "all four chord tones get played")


if __name__ == "__main__":
    run()
    raise SystemExit(0 if helpers.report("test_beat") else 1)

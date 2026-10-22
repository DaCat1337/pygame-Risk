"""core/beat.py - the metronome maths: which beat, step and chord is it?

What it is for : small pure functions that turn the simulation tick counter into musical time.
Uses            : config.py.
Used by         : core/world.py (production on the beat), game.py (music sync), audio/ (chords).

Analogy: a metronome that everybody in the room follows. The game never asks the wall clock
what the time is - it counts ticks (60 per second), and 30 ticks are exactly one beat.
That makes the game deterministic: the same seed always plays out the same way.
"""
from config import (TICKS_PER_BEAT, TICKS_PER_STEP, BEATS_PER_CHORD, CHORDS_PER_LOOP, LOOP_BEATS)

# Which chord tone each eighth-note slot plays (0 = lowest of the 4 tones, 3 = highest).
VOICE_ORDER = (0, 1, 2, 3, 2, 1, 3, 2)


def beat_of(ticks):
    """Beat number (0, 1, 2, ...) that this tick belongs to."""
    return ticks // TICKS_PER_BEAT


def step_of(ticks):
    """Eighth-note step number: two steps per beat."""
    return ticks // TICKS_PER_STEP


def is_beat_tick(ticks):
    """True on the very first tick of a beat."""
    return ticks % TICKS_PER_BEAT == 0


def is_step_tick(ticks):
    """True on the first tick of an eighth note (this includes every beat tick)."""
    return ticks % TICKS_PER_STEP == 0


def beat_phase(ticks):
    """0.0 right on the beat, creeping up to 1.0 just before the next one (for pulses)."""
    return (ticks % TICKS_PER_BEAT) / TICKS_PER_BEAT


def chord_of(beat):
    """Which of the 4 chords (0..3) is playing on this beat. Each chord lasts 16 beats."""
    return (beat // BEATS_PER_CHORD) % CHORDS_PER_LOOP


def chord_of_step(step):
    """Same as chord_of, but for a step number."""
    return chord_of(step // 2)


def loop_beat(beat):
    """Position inside the 64-beat music loop."""
    return beat % LOOP_BEATS


def is_chord_change(beat):
    """True on the first beat of every chord (the background grid flashes then)."""
    return beat % BEATS_PER_CHORD == 0


def voice_slot(step, alive):
    """Which faction plays on this step, and which chord tone (0..3).

    The alive factions take turns, one eighth note each: with 2 factions you hear call and
    response. A dead faction is not in `alive`, so it never gets a slot (its instrument is
    silent). Returns (faction, tone_index), or None if nobody is alive.
    """
    if not alive:
        return None
    n = len(alive)
    faction = alive[step % n]
    tone = VOICE_ORDER[(step // n) % len(VOICE_ORDER)]
    return faction, tone

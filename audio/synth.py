"""audio/synth.py - the sound building blocks: sine sweeps, noise, bells, plucks, mixing.

What it is for : tiny NumPy functions that every other audio file builds on.
Uses            : numpy only.
Used by         : audio/music.py, audio/voices.py, audio/sfx.py, tests.

A sound is just a list of numbers (the speaker position, 22050 times a second). We make those
lists from sine waves, noise and decay curves. (Copied from game2/main.py; the leading underscores
are dropped so other files may use them.)
"""
import re

import numpy as np

SR = 22050                       # samples per second

# Semitones above C inside one octave. A "note name" is a letter, an optional # or b, and an octave.
_NOTE_OFFSET = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def note_hz(name):
    """Frequency in Hz of a note name like "A4", "Bb2" or "F#4" (equal temperament).

    Every semitone is the previous one times 2^(1/12); twelve semitones double the frequency
    (one octave). A4 is the reference: 440 Hz, so A3 = 220 Hz.
    """
    m = re.fullmatch(r"([A-G])([#b]?)(-?\d)", name)
    if not m:
        raise ValueError(f"not a note name: {name!r}")
    letter, accidental, octave = m.groups()
    semitone = 12 * (int(octave) + 1) + _NOTE_OFFSET[letter] + {"#": 1, "b": -1, "": 0}[accidental]
    return 440.0 * 2.0 ** ((semitone - 69) / 12.0)       # MIDI note 69 is A4


def time_axis(seconds):
    """The time of every sample: 0, 1/22050, 2/22050, ... up to `seconds`."""
    return np.arange(int(SR * seconds)) / SR


def noise(seconds, seed):
    """White noise (random numbers between -1 and 1). The same seed gives the same noise."""
    return np.random.default_rng(seed).uniform(-1.0, 1.0, int(SR * seconds))


def lowpass(x, k):
    """Very simple low-pass filter: average every k neighbouring samples (smooths away the highs)."""
    if k <= 1:
        return x
    c = np.cumsum(np.insert(x, 0, 0.0))
    y = (c[k:] - c[:-k]) / k
    return np.pad(y, (k // 2, len(x) - len(y) - k // 2))


def sweep(f0, f1, seconds, curve=1.0):
    """Sine whose pitch glides from f0 to f1 Hz."""
    t = time_axis(seconds)
    f = f0 + (f1 - f0) * (t / seconds) ** curve
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def bell(freq, seconds=0.9, decay=5.0):
    """Bell-ish tone: a sine plus faint inharmonic overtones, ringing out."""
    t = time_axis(seconds)
    body = (np.sin(2 * np.pi * freq * t)
            + 0.45 * np.sin(2 * np.pi * freq * 2.76 * t) * np.exp(-t * decay)
            + 0.25 * np.sin(2 * np.pi * freq * 5.4 * t) * np.exp(-t * decay * 2))
    return body * np.exp(-t * decay)


def pluck(f, seconds=2.2):
    """Soft plucked-string tone: a sine plus two overtones that die away faster (game2's arpeggio note)."""
    tt = time_axis(seconds)
    x = (np.sin(2 * np.pi * f * tt) * np.exp(-tt * 2.6) + 0.35 * np.sin(4 * np.pi * f * tt) * np.exp(-tt * 5)
         + 0.12 * np.sin(6 * np.pi * f * tt) * np.exp(-tt * 9))
    x[:int(SR * 0.003)] *= np.linspace(0, 1, int(SR * 0.003))       # 3 ms fade-in: no click
    return x


def layer(items):
    """Mix [(start_seconds, signal), ...] into one signal."""
    n = max(int(s * SR) + len(x) for s, x in items)
    out = np.zeros(n)
    for s, x in items:
        i = int(s * SR)
        out[i:i + len(x)] += x
    return out


def finish(x, peak=0.8):
    """Normalise, soften the first/last few milliseconds (no clicks), make stereo int16."""
    x = np.asarray(x, dtype=np.float64)
    x = x / max(float(np.abs(x).max()), 1e-9) * peak
    n = min(int(SR * 0.004), len(x) // 2)
    if n:
        x[:n] *= np.linspace(0.0, 1.0, n)
        x[-n:] *= np.linspace(1.0, 0.0, n)
    return np.repeat((x * 32767).astype(np.int16)[:, None], 2, axis=1)


def add_wrap(buf, start, x):
    """Add x into the looping buffer, wrapping past the end (so tails flow into the start)."""
    idx = (start + np.arange(len(x))) % len(buf)
    buf[idx] += x

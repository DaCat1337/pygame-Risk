"""audio/sfx.py - all the short event sounds (clicks, whooshes, zaps, win/lose jingles).

What it is for : build_sfx() returns {name: (stereo int16 array, loudness 0..1)}.
Uses            : audio/synth.py, numpy.
Used by         : audio/player.py, tools/export_audio.py, tests.

Most of these are game2's sounds (same recipes). New for this game: send, whoosh, zap, lost, win.
"""
import numpy as np

from audio.synth import time_axis, noise, lowpass, sweep, bell, layer, finish


def build_sfx():
    """All sound effects: {name: (stereo int16 array, loudness 0..1)}."""
    out = {}

    def put(name, x, gain=1.0, peak=0.85):
        out[name] = (finish(x, peak), gain)

    # --- interface sounds (from game2)
    t = time_axis(0.05)
    put("click", np.sin(2 * np.pi * 1400 * t) * np.exp(-t * 70) + 0.3 * noise(0.05, 1) * np.exp(-t * 150), 0.5)
    t = time_axis(0.035)
    put("hover", np.sin(2 * np.pi * 900 * t) * np.exp(-t * 90), 0.25)
    t = time_axis(0.05)
    put("tick", np.sin(2 * np.pi * 700 * t) * np.exp(-t * 70), 0.35)
    put("on", layer([(0, bell(660, 0.18, 14)), (0.07, bell(990, 0.2, 14))]), 0.5)
    put("off", layer([(0, bell(990, 0.18, 14)), (0.07, bell(660, 0.2, 14))]), 0.5)
    t = time_axis(0.22)
    put("menu_open", sweep(260, 880, 0.22, 0.7) * np.exp(-t * 9), 0.5)
    put("menu_close", sweep(880, 260, 0.22, 0.7) * np.exp(-t * 9), 0.5)
    t = time_axis(0.05)
    put("camera", layer([(0.0, noise(0.05, 13) * np.exp(-t * 160)),
                         (0.07, lowpass(noise(0.05, 14), 3) * np.exp(-t * 70) * 0.7)]), 0.5)
    d = 0.2
    t = time_axis(d)
    put("newround", lowpass(noise(d, 11), 8) * np.sin(np.pi * t / d) * 0.8 + sweep(300, 600, d) * np.sin(np.pi * t / d) * 0.2, 0.4)
    d = 0.45
    t = time_axis(d)
    buzz = np.sign(np.sin(2 * np.pi * 110 * t)) * 0.5 + sweep(220, 110, d, 0.7) * 0.5
    put("wrong", lowpass(buzz, 3) * np.exp(-t * 5), 0.7)

    # --- game sounds
    d = 0.08
    t = time_axis(d)
    attack = np.minimum(t / 0.012, 1.0)                                        # 12 ms fade-in: no sharp "click" at the start
    put("send", sweep(380, 520, d) * np.exp(-t * 30) * attack, 0.4)            # soft, low blip when you give an order

    d = 0.55                                                                   # launch: a rising whoosh (game2)
    t = time_axis(d)
    env = np.sin(np.pi * np.minimum(t / d, 1.0) ** 0.7)
    put("launch", sweep(120, 1500, d, 2.0) * env * 0.6 + lowpass(noise(d, 5), 5) * env * 0.5, 0.7)
    d = 0.3                                                                    # whoosh: played on every launch beat, so it must be gentle
    t = time_axis(d)
    air = lowpass(lowpass(lowpass(noise(d, 6), 14), 14), 14)                   # three smoothings in a row: soft breath, no hiss
    air /= np.abs(air).max()
    tone = sweep(200, 340, d, 1.5)                                             # a low, slow rise (the old one whistled up to 1100 Hz)
    env = np.sin(np.pi * t / d) ** 2                                           # swells in and out smoothly
    put("whoosh", (0.6 * air + 0.35 * tone) * env, 0.35)

    t = time_axis(0.06)                                                        # zap: a tiny high noisy tick for a mid-air clash
    put("zap", noise(0.06, 17) * np.exp(-t * 120) * 0.7 + np.sin(2 * np.pi * 2600 * t) * np.exp(-t * 90) * 0.5, 0.4)

    d = 0.9                                                                    # impact (game2)
    t = time_axis(d)
    thump = sweep(130, 38, d, 0.4) * np.exp(-t * 4.5)
    crunch = lowpass(noise(d, 2), 14) * np.exp(-t * 14) * 2.0
    crack = noise(d, 3) * np.exp(-t * 60) * 0.5
    ring = (np.sin(2 * np.pi * 330 * t) + np.sin(2 * np.pi * 495 * t)) * np.exp(-t * 7) * 0.12
    put("impact", thump + crunch + crack + ring, 1.0, 0.95)

    d = 0.5                                                                    # lost: a falling sweep with a low thump (you lost a node)
    t = time_axis(d)
    thump = sweep(110, 40, d, 0.5) * np.exp(-t * 9) * 1.2
    put("lost", sweep(600, 150, d, 0.7) * np.exp(-t * 5) + thump, 0.8)

    # --- jingles
    run = [523.25, 659.25, 783.99, 1046.5]                                     # C5 E5 G5 C6
    put("survive", layer([(0.11 * i, bell(f, 1.1, 4.5)) for i, f in enumerate(run)]), 0.8)
    put("win", layer([(0.11 * i, bell(f, 1.1, 4.5)) for i, f in enumerate(run)]
                     + [(0.7 + 0.11 * i, bell(2 * f, 1.4, 4.0)) for i, f in enumerate(run)]), 0.8)   # the run again, an octave up
    t = time_axis(1.6)
    chord = sum(np.sin(2 * np.pi * f * t) for f in (261.63, 329.63, 392.0, 493.88)) \
        + 0.3 * sum(np.sin(2 * np.pi * 2 * f * t) for f in (261.63, 392.0))
    put("merge", chord * (1 - np.exp(-t * 6)) * np.exp(-t * 2.2), 0.8)
    d = 1.1
    t = time_axis(d)
    put("die", sweep(520, 80, d, 0.6) * np.exp(-t * 2.4) + lowpass(noise(d, 9), 40) * np.exp(-t * 3) * 1.6, 0.9)
    return out

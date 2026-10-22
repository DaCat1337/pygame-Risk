"""audio/music.py - builds one music track as a seamless 32-second stereo loop.

What it is for : build_track(track) turns a track dict (audio/tracks.py) into a NumPy int16 array:
                 slow pad chords + sub bass + high sparkles + echo (+ soft drums on PULSE).
                 There is NO arpeggio in it: the factions play that live on the beat (audio/voices.py).
                 build_energy(track) is a SECOND loop of the same length (a soft high shimmer and a few more
                 bells). The player mixes it in louder when a lot is happening in the match, so the
                 music gets fuller in big battles and thins out when things are quiet.
Uses            : audio/synth.py, numpy.
Used by         : audio/player.py, tools/export_audio.py, tests.

Seamless = the end flows into the start. Each chord is faded in and out with a cos^2 window
(neighbours overlap by half, so they always add up to 1) and is synthesised relative to its
own centre in time, so nothing jumps at the loop point. The echoes are circular too (np.roll).
(The pad, bass and sparkle code is game2's build_music, generalised to take any track.)
"""
import numpy as np

from audio.synth import SR, time_axis, noise, lowpass, sweep, bell, add_wrap, note_hz

LOOP_SECONDS = 32.0
PEAK = 0.6                      # every track ends at the same peak, so switching never jumps in loudness
ENERGY_PEAK = 0.30              # the energy layer at full intensity (on top of the 0.6 base: they rarely peak together)


def _unit(a):
    return a / max(float(np.abs(a).max()), 1e-9)


def _pad_and_bass(track, t, seconds):
    """Slow chords (two slightly detuned voices per note, panned apart) and a sub bass."""
    n = len(t)
    chord_len = seconds / 4
    overtone2, overtone3 = track["pad_tone"]
    pad = np.zeros((n, 2))
    bass = np.zeros((n, 2))
    for k, (names, root_name) in enumerate(track["chords"]):
        freqs = [note_hz(name) for name in names]
        root = note_hz(root_name)
        centre = (k + 0.5) * chord_len
        tau_all = ((t - centre + seconds / 2) % seconds) - seconds / 2     # time relative to the chord (wraps round the loop)
        mask = np.abs(tau_all) < chord_len
        tau = tau_all[mask]
        win = np.cos(np.pi * tau / (2 * chord_len)) ** 2                  # 1 at its centre, 0 at +-chord_len
        trem = 1.0 + 0.18 * np.sin(2 * np.pi * 4 * t[mask] / seconds + k)  # slow shimmer (loops cleanly)
        left = np.zeros(len(tau))
        right = np.zeros(len(tau))
        for f in freqs:
            for det, (gl, gr) in ((1.0, (1.0, 0.55)), (1.004, (0.55, 1.0))):
                e = np.exp(2j * np.pi * f * det * tau)
                e2 = e * e
                tone = e.imag + overtone2 * e2.imag + overtone3 * (e2 * e).imag     # fundamental + 2 overtones
                left += gl * tone
                right += gr * tone
        scale = win * trem / len(freqs)
        pad[mask, 0] += left * scale
        pad[mask, 1] += right * scale
        sub = (np.sin(2 * np.pi * root * tau) + 0.25 * np.sin(4 * np.pi * root * tau)) * win
        bass[mask, 0] += sub
        bass[mask, 1] += sub
    return pad, bass


def _sparkles(track, n, seconds, seed=21):
    """A few random high bells, then a ping-pong echo around the loop."""
    rng = np.random.default_rng(seed)
    bus = np.zeros((n, 2))
    scale = [note_hz(name) for name in track["sparkle_scale"]]
    for s in rng.choice(int(seconds / 0.5), track["sparkles"], replace=False):
        x = bell(float(rng.choice(scale)), 2.5, 2.2) * 0.14
        pan = float(rng.uniform(0.2, 0.8))
        add_wrap(bus, int(s * 0.5 * SR), np.stack([x * (1 - pan), x * pan], axis=1))
    wet = bus.copy()
    for delay, gain in track["echo"]:
        wet += gain * np.roll(bus[:, ::-1], int(delay * SR), axis=0)        # left/right swapped = ping-pong, circular
    return wet


def _drums(n, seconds):
    """Soft drums for PULSE: a kick on every beat, a filtered-noise hi-hat on every off-beat."""
    drums = np.zeros((n, 2))
    td = time_axis(0.25)
    kick = sweep(110, 45, 0.25) * np.exp(-td * 9)
    th = time_axis(0.08)
    raw = noise(0.08, 3)
    hat = (raw - lowpass(raw, 6)) * np.exp(-th * 60)                      # noise minus its lows = only the highs
    for beat in range(int(seconds / 0.5)):
        add_wrap(drums, int(beat * 0.5 * SR), np.stack([kick, kick], axis=1))
        add_wrap(drums, int((beat * 0.5 + 0.25) * SR), np.stack([hat * 0.5, hat * 0.5], axis=1))
    return drums


def _octave_up(name):
    """"Bb2" -> "Bb3" (the same note one octave higher)."""
    return name[:-1] + str(int(name[-1]) + 1)


def build_track(track, seconds=LOOP_SECONDS):
    """The finished loop: shape (seconds * 22050, 2), int16, peak 0.6 of full scale."""
    n = int(SR * seconds)
    t = np.arange(n) / SR
    pad, bass = _pad_and_bass(track, t, seconds)
    mix = 0.55 * _unit(pad) + 0.30 * _unit(bass) + 0.25 * _unit(_sparkles(track, n, seconds))
    if track["drums"]:
        mix += 0.35 * _unit(_drums(n, seconds))
    mix = mix / max(float(np.abs(mix).max()), 1e-9) * PEAK
    return (mix * 32767).astype(np.int16)


def build_energy(track, seconds=LOOP_SECONDS):
    """The "intensity" layer: same length and loop point as build_track, int16 stereo, peak 0.3.

    Purely tonal and soft: a shimmer (the two highest pad notes of each chord, an octave up) and a few extra bells.
    There are deliberately NO drums or hi-hats in it: an always-present rhythm got annoying. It is mixed in by volume
    only, so it has no effect on how the base loop sounds.
    """
    n = int(SR * seconds)
    t = np.arange(n) / SR
    shimmer_track = dict(track, pad_tone=(0.15, 0.04),
                         chords=[(tuple(_octave_up(name) for name in names[-2:]), root) for names, root in track["chords"]])
    shimmer, _ = _pad_and_bass(shimmer_track, t, seconds)
    sparks = _sparkles(dict(track, sparkles=max(4, track["sparkles"] * 3 // 2)), n, seconds, seed=22)
    mix = 0.60 * _unit(shimmer) + 0.40 * _unit(sparks)
    mix = mix / max(float(np.abs(mix).max()), 1e-9) * ENERGY_PEAK
    return (mix * 32767).astype(np.int16)

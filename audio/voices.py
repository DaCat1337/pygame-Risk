"""audio/voices.py - the faction instruments and the capture bells (the music IS the game).

What it is for : build_voices(track) makes 64 short notes (4 instruments x 4 chords x 4 chord
                 tones) plus, per chord, a 3-bell "you captured a node" run and a single soft bell.
Uses            : audio/synth.py, numpy.
Used by         : audio/player.py (plays them), tools/export_audio.py, tests.

Because every note is a tone of the CURRENT chord, anything the factions play or any capture
bell always sounds good together with the pad underneath.
Instruments (instrument number = faction number):
  1 player  pluck      2 magenta  bell      3 amber  glass      4 lime  soft reed
"""
import numpy as np

from audio.synth import SR, time_axis, lowpass, bell, pluck, note_hz

NOTE_SECONDS = 1.8
PAN = {1: 0.4, 2: 0.65, 3: 0.3, 4: 0.75}            # 0 = all left, 1 = all right
NOTE_PEAK = 0.30                                    # quiet enough that several notes can ring together
ECHO = ((0.375, 0.30), (0.75, 0.20), (1.125, 0.12))  # ping-pong echo baked into every note


def chord_tones(track, chord):
    """The 4 notes the factions play for this chord: the 4 highest pad notes, one octave up (Hz)."""
    names, _ = track["chords"][chord]
    return [2.0 * f for f in sorted(note_hz(n) for n in names)[-4:]]


def capture_notes(track, chord):
    """The 3 rising bell frequencies of a player capture: tones 0, 2 and 3 of the chord."""
    tones = chord_tones(track, chord)
    return [tones[0], tones[2], tones[3]]


def _glass(f):
    """Thin, glassy tone: fundamental + 3rd harmonic + a 5th harmonic that dies away quickly."""
    t = time_axis(NOTE_SECONDS)
    x = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 3 * f * t)
         + 0.2 * np.sin(2 * np.pi * 5 * f * t) * np.exp(-t * 14)) * np.exp(-t * 2.4)
    x[:int(SR * 0.003)] *= np.linspace(0, 1, int(SR * 0.003))
    return x


def _reed(f):
    """Soft reed: a square wave with the sharp highs filtered off, at half volume, slow attack."""
    t = time_axis(NOTE_SECONDS)
    square = np.sign(np.sin(2 * np.pi * f * t))
    x = lowpass(square, max(2, int(SR / f / 3))) * 0.5
    return x * np.minimum(t / 0.02, 1.0) * np.exp(-t * 2.0)


def instrument(number, f):
    """One dry note (mono, 1.8 s) of instrument 1..4 at frequency f."""
    if number == 1:
        x = pluck(f, 2.2)[:int(SR * NOTE_SECONDS)]
    elif number == 2:
        x = bell(f, NOTE_SECONDS, 3.0)
    elif number == 3:
        x = _glass(f)
    else:
        x = _reed(f)
    return x


def _to_stereo_with_echo(x, pan):
    """Pan the note, then add a ping-pong echo tail inside the same 1.8 s (shifted copies, sides swapped)."""
    n = len(x)
    dry = np.stack([x * (1 - pan), x * pan], axis=1)
    out = dry.copy()
    for delay, gain in ECHO:
        d = int(delay * SR)
        out[d:] += gain * dry[:n - d, ::-1]
    return out


def _to_int16(stereo, peak=NOTE_PEAK):
    stereo = stereo / max(float(np.abs(stereo).max()), 1e-9) * peak
    n = int(SR * 0.05)
    stereo[-n:] *= np.linspace(1.0, 0.0, n)[:, None]             # fade the tail out: no click at the end
    stereo[:int(SR * 0.002)] *= np.linspace(0, 1, int(SR * 0.002))[:, None]
    return (stereo * 32767).astype(np.int16)


def build_voices(track):
    """All instrument notes and capture bells of one track.

    Returns a dict: ("voice", instrument 1..4, chord 0..3, tone 0..3) -> int16 stereo array,
    "capture_<chord>" -> three rising bells, "bell_<chord>" -> one soft bell.
    """
    out = {}
    for chord in range(4):
        tones = chord_tones(track, chord)
        for inst in (1, 2, 3, 4):
            for tone, f in enumerate(tones):
                out[("voice", inst, chord, tone)] = _to_int16(_to_stereo_with_echo(instrument(inst, f), PAN[inst]))
        run = np.zeros(int(SR * 1.4))
        for k, f in enumerate(capture_notes(track, chord)):
            b = bell(f, 1.0, 4.5)
            run[int(0.09 * k * SR):int(0.09 * k * SR) + len(b)] += b
        out[f"capture_{chord}"] = _to_int16(np.stack([run * 0.5, run * 0.5], axis=1), 0.5)
        soft = bell(tones[1], 1.2, 5.0)
        out[f"bell_{chord}"] = _to_int16(np.stack([soft * 0.5, soft * 0.5], axis=1), 0.35)
    return out

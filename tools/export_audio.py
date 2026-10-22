"""tools/export_audio.py - OPTIONAL: save every sound of the game as a .wav file you can play in any media player.

What it is for : the whole soundtrack is made of maths (see audio/), so there are no sound files in the game.
                 This little tool writes them out once, so you can listen to them (or send them to a friend).
Uses            : audio/music.py, audio/voices.py, audio/sfx.py, audio/tracks.py, Python's built-in `wave`.
Used by         : you, by hand.

Run it from the game4 folder (Windows cmd):
    python tools\\export_audio.py              (everything: tracks, effects and every instrument note)
    python tools\\export_audio.py --quick      (tracks and effects only - about 15 seconds)
    python tools\\export_audio.py --out my_folder
The files land in  exports\\tracks,  exports\\sfx  and  exports\\voices\\<TRACK>.
"""
import argparse
import os
import sys
import wave

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)                          # so "from audio.music import ..." works from any folder

import numpy as np  # noqa: E402

from audio.music import build_track, build_energy  # noqa: E402
from audio.sfx import build_sfx  # noqa: E402
from audio.synth import SR  # noqa: E402
from audio.tracks import TRACKS  # noqa: E402
from audio.voices import build_voices  # noqa: E402


def write_wav(path, samples):
    """Save an int16 array (mono, or stereo as shape (n, 2)) as a standard 16-bit WAV file."""
    channels = 1 if samples.ndim == 1 else samples.shape[1]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as f:
        f.setnchannels(channels)
        f.setsampwidth(2)                              # 2 bytes = 16 bit
        f.setframerate(SR)
        f.writeframes(np.ascontiguousarray(samples, dtype="<i2").tobytes())


def voice_filename(key):
    """("voice", 2, 1, 3) -> voice_inst2_chord1_tone3.wav ;  "capture_1" -> capture_1.wav"""
    if isinstance(key, tuple):
        _, inst, chord, tone = key
        return f"voice_inst{inst}_chord{chord}_tone{tone}.wav"
    return f"{key}.wav"


def main():
    parser = argparse.ArgumentParser(description="Write the game's sounds to .wav files.")
    parser.add_argument("--out", default=os.path.join(HERE, "exports"), help="folder to write into (default: exports)")
    parser.add_argument("--quick", action="store_true", help="skip the (many) single instrument notes")
    args = parser.parse_args()

    count = 0
    for track in TRACKS:
        print(f"track {track['name']} ...")
        write_wav(os.path.join(args.out, "tracks", f"{track['name']}.wav"), build_track(track))
        write_wav(os.path.join(args.out, "tracks", f"{track['name']}_energy.wav"), build_energy(track))   # the busy-match layer
        count += 2
        if not args.quick:
            for key, arr in build_voices(track).items():
                write_wav(os.path.join(args.out, "voices", track["name"], voice_filename(key)), arr)
                count += 1
    print("sound effects ...")
    for name, (arr, _gain) in build_sfx().items():
        write_wav(os.path.join(args.out, "sfx", f"{name}.wav"), arr)
        count += 1
    print(f"done: {count} files in {args.out}")


if __name__ == "__main__":
    main()

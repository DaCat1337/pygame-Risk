"""tests/test_audio.py - the synthesised sound: tracks, voices, effects and the mixer wrapper.

I cannot LISTEN in a test. These checks prove the sound is well-formed: right length and format,
no clipping, seamless loops, notes that belong to their chords, and a player that never crashes.
"""
import os
import time

import numpy as np

import helpers
from helpers import check
import pygame

from config import BEAT
from audio.music import build_track, LOOP_SECONDS
from audio.player import Audio, rotated_music, BEAT_SAMPLES
from audio.sfx import build_sfx
from audio.synth import SR, note_hz
from audio.tracks import TRACKS, TRACK_NAMES
from audio.voices import build_voices, chord_tones, capture_notes

# game2's DRIFT chords in Hz (copied from game2/main.py build_music)
GAME2_CHORDS = [((146.83, 174.61, 220.00, 261.63, 329.63), 73.42), ((116.54, 146.83, 174.61, 220.00), 58.27),
                ((98.00, 146.83, 174.61, 233.08, 293.66), 49.00), ((110.00, 146.83, 164.81, 196.00, 261.63), 55.00)]


def run():
    # --- note names
    check(note_hz("A4") == 440.0 and abs(note_hz("A3") - 220.0) < 1e-9, "note_hz: A4 = 440 Hz, A3 = 220 Hz")
    check(abs(note_hz("C4") - 261.6256) < 0.001 and abs(note_hz("Bb2") - 116.5409) < 0.001 and abs(note_hz("F#4") - 369.9944) < 0.001,
          "note_hz: C4, Bb2 and F#4 are right")
    try:
        note_hz("H9")
        check(False, "a bad note name raises")
    except ValueError:
        check(True, "a bad note name raises")

    # --- DRIFT uses game2's chords (within 0.01 Hz)
    drift = TRACKS[0]
    ok = True
    for (names, bass), (hz, bass_hz) in zip(drift["chords"], GAME2_CHORDS):
        ok &= [round(note_hz(n), 2) for n in names] == [round(f, 2) for f in hz] or all(abs(note_hz(n) - f) < 0.01 for n, f in zip(names, hz))
        ok &= abs(note_hz(bass) - bass_hz) < 0.01
    check(ok, "DRIFT's pad and bass notes match game2's chords to 0.01 Hz")
    check(len(TRACKS) == 4 and TRACK_NAMES == ["DRIFT", "NEON", "PULSE", "DEEP"], "four tracks: DRIFT NEON PULSE DEEP")
    check(all(len(t["chords"]) == 4 for t in TRACKS), "every track has 4 chords")

    # --- the tracks
    peaks = []
    for track in TRACKS:
        t0 = time.time()
        loop = build_track(track)
        took = time.time() - t0
        m = loop.astype(np.float64)
        peak = int(np.abs(loop).max())
        peaks.append(peak)
        check(loop.shape == (int(SR * LOOP_SECONDS), 2) and loop.dtype == np.int16, f"{track['name']}: exactly 32 s of int16 stereo (built in {took:.1f} s)")
        check(peak < 32767 * 0.62, f"{track['name']}: no clipping (peak {peak})")
        typical = np.abs(np.diff(m, axis=0)).max()
        seam = np.abs(m[0] - m[-1]).max()
        check(seam <= typical, f"{track['name']}: the loop seam is smooth (jump {seam:.0f} <= largest normal step {typical:.0f})")
        left = m[:, 0]
        check(float(np.abs(left[:SR]).mean()) > 0.3 * float(np.abs(left).mean()), f"{track['name']}: no silent gap at the start")
    check(max(peaks) / min(peaks) < 1.10, f"all track peaks are within 10% of each other {peaks}")

    # --- the faction voices
    for track in TRACKS:
        voices = build_voices(track)
        notes = [k for k in voices if isinstance(k, tuple)]
        check(len(notes) == 64, f"{track['name']}: 64 instrument notes (4 instruments x 4 chords x 4 tones)")
        check(all(v.dtype == np.int16 and v.ndim == 2 and v.shape[1] == 2 and int(np.abs(v).max()) > 1000 for v in voices.values()),
              f"{track['name']}: every voice is audible int16 stereo")
        ok = True
        for chord in range(4):
            names, _ = track["chords"][chord]
            allowed = {round(2 * note_hz(n), 3) for n in names}
            ok &= all(round(f, 3) in allowed for f in capture_notes(track, chord))        # capture bells are chord tones
            ok &= all(round(f, 3) in allowed for f in chord_tones(track, chord))
            ok &= len(chord_tones(track, chord)) == 4 and f"capture_{chord}" in voices and f"bell_{chord}" in voices
        check(ok, f"{track['name']}: every capture bell is a tone of its chord")

    # --- the effects
    sfx = build_sfx()
    needed = {"click", "hover", "tick", "on", "off", "menu_open", "menu_close", "launch", "impact", "die", "survive", "merge",
              "camera", "newround", "wrong", "send", "whoosh", "zap", "lost", "win"}
    check(needed <= set(sfx), "every sound effect the game asks for exists")
    check(not ({"drop", "scatter", "wall", "erase", "nutrient", "rotate", "one", "split", "correct"} & set(sfx)), "the Lenia-only sounds are gone")
    ok = True
    for name, (arr, gain) in sfx.items():
        ok &= arr.dtype == np.int16 and arr.ndim == 2 and arr.shape[1] == 2 and 0.0 < gain <= 1.0
        ok &= 200 < len(arr) < SR * 3 and int(np.abs(arr).max()) > 3000
        ok &= int(np.abs(arr[0]).max()) < 400 and int(np.abs(arr[-1]).max()) < 400        # no clicks at the ends
    check(ok, "every effect is stereo int16, audible, short, and starts/ends softly")
    check(len(sfx["win"][0]) > len(sfx["survive"][0]), "win is the 4-bell run twice (longer than survive)")

    # --- the rotated-copy trick
    loop = build_track(TRACKS[0])
    for beat in (0, 1, 17, 63, 64, 70):
        rot = rotated_music(loop, beat)
        check(rot.shape == loop.shape and np.array_equal(rot[0], loop[(beat % 64) * BEAT_SAMPLES]),
              f"rotated copy for beat {beat}: sample 0 equals sample beat*BEAT*SR of the original")
    check(BEAT_SAMPLES == int(BEAT * SR) == 11025, "one beat is 11025 samples")
    rot = rotated_music(loop, 5)
    check(np.array_equal(rot[-1], loop[5 * BEAT_SAMPLES - 1]), "the rotated copy ends where it started (seamless)")

    # --- the launch sounds are gentle (the owner found them harsh): almost no energy above 1 kHz, no sharp start
    sfx = build_sfx()
    for name in ("whoosh", "send"):
        x = sfx[name][0][:, 0].astype(float)
        power = np.abs(np.fft.rfft(x)) ** 2
        freqs = np.fft.rfftfreq(len(x), 1 / SR)
        check(power[freqs > 1000].sum() / power.sum() < 0.02, f"{name} has almost no energy above 1 kHz (soft, not hissy)")
        check(np.abs(x[:int(0.004 * SR)]).max() < 0.35 * np.abs(x).max(), f"{name} starts softly (no click)")

    # --- tools/export_audio.py: a WAV file written by the tool reads back with the right format and content
    import tempfile
    import wave
    from tools.export_audio import write_wav, voice_filename
    loop = build_sfx()["die"][0]                            # (a short stereo int16 sound)
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "sub", "t.wav")
        write_wav(path, loop)
        with wave.open(path) as w:
            check((w.getnchannels(), w.getframerate(), w.getsampwidth(), w.getnframes()) == (2, SR, 2, len(loop)), "exported WAV: stereo, 22050 Hz, 16 bit, right length")
            check(np.array_equal(np.frombuffer(w.readframes(len(loop)), dtype="<i2").reshape(-1, 2), loop), "exported WAV holds exactly the samples")
    check(voice_filename(("voice", 2, 1, 3)) == "voice_inst2_chord1_tone3.wav" and voice_filename("capture_1") == "capture_1.wav", "voice file names")

    # --- the mixer wrapper (SDL's silent dummy device)
    pygame.init()                                           # opens the mixer in pygame's format; Audio must reopen it
    audio = Audio(enabled=True)
    check(audio.available, "the mixer starts (dummy device)")
    check(pygame.mixer.get_init()[0] == SR and pygame.mixer.get_init()[2] == 2, f"the mixer runs at 22050 Hz stereo: {pygame.mixer.get_init()}")
    if audio.available:
        check(pygame.mixer.get_num_channels() == 32, "32 mixer channels")
        audio.play("click")
        audio.play("does-not-exist")
        audio.set_sfx_volume(0.0)
        audio.set_sfx_on(False)
        audio.play("click")
        audio.set_sfx_on(True)
        audio.set_sfx_volume(0.5)
        check(not audio.play_music_from_beat(1, 0), "music for a track that is not built yet does not start")
        audio.request_track(1)
        audio.join()
        check(audio.track_ready(1), "a track builds in the background")
        check(audio.play_music_from_beat(1, 20, fade_ms=100) and pygame.mixer.Channel(0).get_busy(), "music starts from beat 20 on channel 0")
        check(audio.playing_track == 1 and audio.voice_track == 1, "the voices switch to the playing track")
        audio.play_voice(1, 0, 0, 0.5)
        audio.play_voice(2, 3, 3, 1.0)
        audio.play_capture(0)
        audio.play_capture(2, soft=True)
        audio.duck(0.35, 0.5)
        check(audio.duck_factor() < 1.0, "ducking lowers the music")
        audio.update()
        audio.set_music_volume(0.3)
        audio.pause()
        audio.resume()
        audio.set_music_on(False)
        check(not pygame.mixer.Channel(0).get_busy(), "turning music off stops it")
        check(not audio.play_music_from_beat(1, 0), "music does not start while switched off")
        audio.play_voice(1, 0, 0, 1.0)
        audio.set_music_on(True)
        # regression: a track started WITH a fade-in must end at the slider's volume, not at 100%
        # (pygame's own fade_ms jumps the channel to full volume when the fade ends)
        audio.music_vol = 0.5
        audio._duck = None
        check(audio.play_music_from_beat(1, 0, fade_ms=150), "music restarts with a fade-in")
        check(pygame.mixer.Channel(0).get_volume() < 0.1, "a fading-in track starts quiet")
        time.sleep(0.25)
        audio.update()
        want = audio._curve(0.5)
        check(abs(pygame.mixer.Channel(0).get_volume() - want) < 0.02, f"after the fade-in the music sits at the slider volume ({want:.2f})")
        time.sleep(0.2)
        audio.update()
        check(abs(pygame.mixer.Channel(0).get_volume() - want) < 0.02, "and it stays there")
        for _ in range(40):                                  # the 12-per-second limit must not crash
            audio.play("zap")
        pygame.mixer.quit()
    silent = Audio(enabled=False)
    silent.play("click")
    silent.play_voice(1, 0, 0, 1.0)
    silent.play_capture(0)
    silent.request_track(0)
    silent.set_music_on(True)
    silent.set_music_volume(0.2)
    silent.duck()
    silent.update()
    silent.pause()
    silent.resume()
    silent.stop_music()
    check(not silent.available and not silent.play_music_from_beat(0, 0) and not silent.music_playing(),
          "Audio(enabled=False) is silent and safe")


if __name__ == "__main__":
    run()
    raise SystemExit(0 if helpers.report("test_audio") else 1)

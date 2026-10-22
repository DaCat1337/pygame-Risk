"""audio/player.py - plays the sounds through pygame.mixer (the only audio file that imports pygame).

What it is for : the Audio class: music on a reserved channel, sound effects, the faction beat
                 voices, volumes, ducking, and starting the music AT ANY BEAT (the rotated-copy trick).
                 It is safe with no sound device: everything quietly does nothing (`available` False).
Uses            : config.py, audio/synth.py, audio/tracks.py, audio/music.py, audio/voices.py,
                 audio/sfx.py, pygame, numpy.
Used by         : game.py, main.py, tests.

The rotated-copy trick: a pygame Sound can only start at its FIRST sample. To start the music at
beat 20 we make a copy of the loop rotated with np.roll so that its first sample is where
beat 20 begins. Played on a loop, it carries on seamlessly because the loop is seamless.

Dynamic intensity: every track has a second loop, the "energy layer" (audio/music.py build_energy). It plays on
channel 1, started together with the base loop on channel 0, and only its VOLUME changes: the conductor says how
busy the match is (set_intensity 0..1) and the layer fades in and out smoothly.
"""
import math
import threading
import time
import traceback
from collections import deque

import numpy as np
import pygame

from config import BEAT, LOOP_BEATS
from audio.music import build_track, build_energy
from audio.sfx import build_sfx
from audio.synth import SR
from audio.tracks import TRACKS
from audio.voices import build_voices

BEAT_SAMPLES = int(BEAT * SR)          # 11025 samples per beat
ENERGY_RISE = 2.0                      # seconds the intensity takes to rise (a time constant: ~63% of the way)
ENERGY_FALL = 4.0                      # ...and to fall (slower, so the music does not flicker between beats)
BASE_DIP = 0.15                        # in a quiet moment the base loop is this much quieter (a thinner sound)


def rotated_music(loop, beat):
    """A copy of the music loop whose sample 0 is the start of `beat` (beats repeat every 64)."""
    return np.roll(loop, -(beat % LOOP_BEATS) * BEAT_SAMPLES, axis=0)


class Audio:
    MIN_GAP = {"tick": 0.04, "hover": 0.06, "zap": 0.05, "send": 0.05, "whoosh": 0.25, "click": 0.03}
    MAX_PER_SECOND = 12                                    # about this many effects per second in total...
    ALWAYS = {"win", "die", "lost", "merge", "survive", "menu_open", "menu_close", "camera", "on", "off"}   # ...except these

    def __init__(self, enabled=True, music=True):
        self.available = False
        self.music_on, self.sfx_on = True, True
        self.music_vol, self.sfx_vol = 0.5, 0.7
        self.sfx = {}
        self.loops = {}                    # track id -> int16 loop array (finished building)
        self.energy_loops = {}             # track id -> int16 energy-layer array (built together with the loop)
        self.dynamic_on = True             # the DYNAMIC MUSIC switch: off = the energy layer stays silent, the base loop stays at full volume
        self.energy, self.energy_target = 0.0, 0.0     # how much of the energy layer is mixed in now / should be (0..1)
        self._rotated_energy = None        # like _rotated, for the energy layer
        self._last_update = None
        self.voice_sets = {}               # track id -> {key: pygame Sound}
        self.voice_track = None            # which voice set is used right now
        self.playing_track = None
        self._rotated = None               # (key, Sound): the last rotated copy, kept so it is not rebuilt
        self._building = set()
        self._lock = threading.Lock()
        self._threads = []
        self._times = deque()
        self._last = {}
        self._duck = None                  # (start time, length, depth) while the music is dipped
        self._fade_in = None               # (start time, length) while a new track fades in
        if not enabled:
            return
        try:
            if pygame.mixer.get_init():              # pygame.init() already opened it with its own format;
                pygame.mixer.quit()                  # our buffers assume 22050 Hz stereo, so reopen it
            pygame.mixer.init(frequency=SR, size=-16, channels=2, buffer=512, allowedchanges=0)
            pygame.mixer.set_num_channels(32)
            pygame.mixer.set_reserved(2)             # channel 0 = music, channel 1 = its energy layer
        except (pygame.error, NotImplementedError):
            return
        self.available = True
        for name, (arr, gain) in build_sfx().items():
            self.sfx[name] = (pygame.mixer.Sound(buffer=arr.tobytes()), gain)

    @staticmethod
    def _curve(v):
        return max(0.0, min(1.0, v)) ** 1.6                # volume feels more even this way

    # ------------------------------------------------------------------ building tracks (background threads)
    def request_track(self, track_id):
        """Start building a track (loop + its voices) in the background, unless done or already started.
        The first track is built at start-up, the others lazily the first time they are needed."""
        if not self.available:
            return
        with self._lock:
            if track_id in self.loops or track_id in self._building:
                return
            self._building.add(track_id)
        thread = threading.Thread(target=self._build, args=(track_id,), daemon=True)
        self._threads.append(thread)
        thread.start()

    def _build(self, track_id):
        try:
            track = TRACKS[track_id]
            loop = build_track(track)
            energy = build_energy(track)
            sounds = {key: pygame.mixer.Sound(buffer=arr.tobytes()) for key, arr in build_voices(track).items()}
            with self._lock:
                self.voice_sets[track_id] = sounds
                self.energy_loops[track_id] = energy
                self.loops[track_id] = loop                # the loop is published last: "ready" means both are there
        except Exception:
            traceback.print_exc()                          # a failed build just means no music for this track (but say why)
        finally:
            with self._lock:
                self._building.discard(track_id)

    def track_ready(self, track_id):
        return track_id in self.loops

    def join(self):
        """Wait for all background builds (used by tests)."""
        for thread in self._threads:
            thread.join()

    # ------------------------------------------------------------------ music
    def play_music_from_beat(self, track_id, beat, fade_ms=0):
        """Start the track so that the music is at `beat` right now. Returns False if it cannot (not built yet,
        no sound device, music switched off). The voices switch to this track's notes too."""
        if not (self.available and self.music_on) or track_id not in self.loops:
            return False
        key = (track_id, beat % LOOP_BEATS)
        if self._rotated is None or self._rotated[0] != key:
            sound = pygame.mixer.Sound(buffer=rotated_music(self.loops[track_id], beat).tobytes())
            self._rotated = (key, sound)                   # cached: switching back to the same spot is free
        energy_key = (track_id, beat % LOOP_BEATS, "energy")
        if self._rotated_energy is None or self._rotated_energy[0] != energy_key:
            energy_sound = pygame.mixer.Sound(buffer=rotated_music(self.energy_loops[track_id], beat).tobytes())
            self._rotated_energy = (energy_key, energy_sound)
        pygame.mixer.Channel(1).play(self._rotated_energy[1], loops=-1)    # started right next to the base loop: they stay in step
        channel = pygame.mixer.Channel(0)
        channel.play(self._rotated[1], loops=-1)           # (NOT fade_ms=...: pygame's own fade-in resets the channel to
        self._fade_in = (time.monotonic(), fade_ms / 1000) if fade_ms else None     # full volume when it ends. We fade ourselves.)
        self._apply_music_volume()
        self.playing_track = track_id
        self.voice_track = track_id
        return True

    def stop_music(self, fade_ms=0):
        if self.available:
            if fade_ms:
                pygame.mixer.Channel(0).fadeout(fade_ms)
                pygame.mixer.Channel(1).fadeout(fade_ms)
            else:
                pygame.mixer.Channel(0).stop()
                pygame.mixer.Channel(1).stop()
        self.playing_track = None

    def music_playing(self):
        return self.available and pygame.mixer.Channel(0).get_busy()

    def duck(self, depth=0.6, seconds=1.4):
        """Dip the music for a moment (a lost node should be heard over it); update() eases it back."""
        self._duck = (time.monotonic(), seconds, depth)

    def duck_factor(self):
        """1.0 = normal; smaller while the music is ducked."""
        if self._duck is None:
            return 1.0
        t0, length, depth = self._duck
        k = (time.monotonic() - t0) / length
        return 1.0 if k >= 1.0 else 1.0 - depth * (1.0 - k) ** 2

    def fade_in_factor(self):
        """0 -> 1 while a freshly started track fades in, then 1.0."""
        if self._fade_in is None:
            return 1.0
        t0, length = self._fade_in
        return min(1.0, (time.monotonic() - t0) / length)

    def set_dynamic(self, on):
        """Switch the dynamic energy layer on / off. Off is immediate and the base loop is then at its full volume."""
        self.dynamic_on = bool(on)
        if not self.dynamic_on:
            self.energy = self.energy_target = 0.0
        if self.playing_track is not None:
            self._apply_music_volume()

    def set_intensity(self, level):
        """How busy the match is, 0 (quiet) .. 1 (a big battle). The energy layer eases towards it (see update).
        Ignored while DYNAMIC MUSIC is switched off."""
        self.energy_target = max(0.0, min(1.0, float(level))) if self.dynamic_on else 0.0

    def _apply_music_volume(self):
        """Volumes = slider curve x ducking x fade-in; the base loop dips a little when it is quiet, the energy layer
        follows the intensity. Every volume change goes through here."""
        if self.available:
            level = self._curve(self.music_vol) * self.duck_factor() * self.fade_in_factor()
            dip = BASE_DIP * (1.0 - self.energy) if self.dynamic_on else 0.0
            pygame.mixer.Channel(0).set_volume(level * (1.0 - dip))
            pygame.mixer.Channel(1).set_volume(level * self.energy)

    def update(self, dt=None):
        """Call once per frame: eases the intensity and applies ducking, fade-in and intensity to the music channels.
        (dt = seconds since the last call; measured by itself when left out.)"""
        if not self.available:
            return
        now = time.monotonic()
        if dt is None:
            dt = 0.0 if self._last_update is None else min(0.25, now - self._last_update)
        self._last_update = now
        before = self.energy
        if self.energy != self.energy_target:                     # ease: move a fraction of the way each frame
            tau = ENERGY_RISE if self.energy_target > self.energy else ENERGY_FALL
            self.energy += (self.energy_target - self.energy) * (1.0 - math.exp(-dt / tau))
            if abs(self.energy - self.energy_target) < 0.003:
                self.energy = self.energy_target
        busy = self._duck is not None or self._fade_in is not None or self.energy != before
        if busy and self.music_on and self.playing_track is not None:
            self._apply_music_volume()
        if self._duck is not None and self.duck_factor() >= 1.0:
            self._duck = None
        if self._fade_in is not None and self.fade_in_factor() >= 1.0:
            self._fade_in = None

    def set_music_on(self, on):
        self.music_on = bool(on)
        if not self.music_on:
            self.stop_music()

    def set_music_volume(self, v):
        self.music_vol = float(v)
        if self.playing_track is not None:
            self._apply_music_volume()

    def set_sfx_on(self, on):
        self.sfx_on = bool(on)

    def set_sfx_volume(self, v):
        self.sfx_vol = float(v)

    def pause(self):
        if self.available:
            pygame.mixer.pause()

    def resume(self):
        if self.available:
            pygame.mixer.unpause()

    # ------------------------------------------------------------------ the faction instruments
    def play_voice(self, instrument, chord, tone, volume):
        """One note of a faction's arpeggio. volume 0..1 follows the faction's share of the map.
        Beat voices are part of the music, so they obey the MUSIC switch and volume."""
        if not (self.available and self.music_on):
            return
        sounds = self.voice_sets.get(self.voice_track)
        snd = sounds.get(("voice", instrument, chord, tone)) if sounds else None
        if snd is not None:
            snd.set_volume(min(1.0, volume * self._curve(self.music_vol) * self.duck_factor() * 1.2))
            snd.play()

    def play_capture(self, chord, soft=False):
        """The bells for a capture, built from the current chord: 3 rising bells, or one soft bell."""
        if not (self.available and self.sfx_on):
            return
        sounds = self.voice_sets.get(self.voice_track)
        snd = sounds.get(f"{'bell' if soft else 'capture'}_{chord}") if sounds else None
        if snd is not None:
            snd.set_volume(min(1.0, self._curve(self.sfx_vol) * 1.4))
            snd.play()

    # ------------------------------------------------------------------ sound effects
    def play(self, name, vol=1.0):
        if not (self.available and self.sfx_on) or name not in self.sfx:
            return
        now = time.monotonic()
        if now - self._last.get(name, -1.0) < self.MIN_GAP.get(name, 0.02):
            return
        if name not in self.ALWAYS:                         # at most ~12 effects per second
            while self._times and now - self._times[0] > 1.0:
                self._times.popleft()
            if len(self._times) >= self.MAX_PER_SECOND:
                return
            self._times.append(now)
        self._last[name] = now
        snd, gain = self.sfx[name]
        snd.set_volume(min(1.0, gain * vol * self._curve(self.sfx_vol) * 1.4))
        snd.play()

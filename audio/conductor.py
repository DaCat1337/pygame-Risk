"""audio/conductor.py - decides WHAT plays WHEN: music start/switch/resync and world-event sounds.

What it is for : the Conductor turns World events into sound and keeps the music in time with the
                 simulation beat. (Split out of game.py so game.py stays short.)
Uses            : config.py, core/beat.py, audio/tracks.py, an Audio object (audio/player.py).
Used by         : game.py.

The music is started on a BEAT event (never "whenever"), so it always lines up with the world's
beat. On every beat it also tells the Audio how busy the match is (ships in the air, recent clashes), and the
music's energy layer fades in and out with that. If the music and the simulation drift apart by more than 0.12 s (a window drag, a slow
PC), it restarts from the next beat.
"""
import random
import time

from audio.tracks import TRACK_NAMES, SHUFFLE
from config import DT, PLAYER, TICKS_PER_BEAT
from core.beat import chord_of, chord_of_step, voice_slot

DRIFT_LIMIT = 0.12                 # seconds
INTENSITY_QUIET = 30               # up to this many ships in the air the match counts as quiet: the energy layer stays silent
INTENSITY_FULL = 170               # "a big battle": this many ships in the air (clashes count extra) = full intensity
CLASH_WEIGHT = 8                   # every ship destroyed in a recent clash counts like this many ships in the air


class Conductor:
    def __init__(self, audio, settings):
        self.audio = audio                          # may be None (silent) or an Audio that is not `available`
        self.settings = settings                    # the same dict the Game uses
        self.world = None                           # the world whose beat the music follows (events of other worlds are ignored)
        self.track = 0                              # the track that is (or will be) playing
        self.pending = None                         # a track id that will be started on the next beat
        self.fade_ms = 0
        self.ref = None                             # (wall clock, world tick) at the moment the music was started
        self.pause_started = None
        self.recent_clash = 0.0                     # ships destroyed in mid-air lately (halves every beat)
        self.apply_settings()

    @property
    def active(self):
        return self.audio is not None and self.audio.available

    # ------------------------------------------------------------------ settings
    def apply_settings(self):
        """Push the saved volumes and switches into the Audio object."""
        if self.audio is None:
            return
        s = self.settings
        self.audio.set_music_on(s["music_on"])
        self.audio.set_music_volume(s["music_vol"])
        self.audio.set_dynamic(s["dynamic_music"])
        self.audio.set_sfx_on(s["sfx_on"])
        self.audio.set_sfx_volume(s["sfx_vol"])

    def setting_changed(self, key):
        """A setting changed: apply it. Turning music back on rejoins on the next beat."""
        if key in ("music_on", "music_vol", "sfx_on", "sfx_vol", "dynamic_music"):
            self.apply_settings()
            if key == "music_on" and self.settings["music_on"] and self.world is not None:
                self.schedule(self.track, 250)
        elif key == "music_track":
            self.change_track(self.resolve_track())

    # ------------------------------------------------------------------ choosing and starting tracks
    def resolve_track(self):
        """The track to use now: the chosen one, or (SHUFFLE) a random one that is not the one just played."""
        choice = self.settings["music_track"]
        if choice == SHUFFLE:
            return random.choice([t for t in range(len(TRACK_NAMES)) if t != self.track])
        return choice

    def is_ready(self, track_id):
        """Is this track already built? (The first build of a track takes a few seconds in the background.)"""
        return self.active and self.audio.track_ready(track_id)

    def name(self):
        if not self.active:
            return ""
        return TRACK_NAMES[self.track] + (" (SHUFFLE)" if self.settings["music_track"] == SHUFFLE else "")

    def begin(self, world):
        """A new world starts: pick a track; it starts from beat 0 on the first beat, fading in."""
        self.world = world
        self.track = self.resolve_track()
        self.ref = None
        self.recent_clash = 0.0
        if self.active:
            self.audio.set_intensity(0.0)
        self.schedule(self.track, 250)

    def schedule(self, track_id, fade_ms=0):
        """Start `track_id` on the NEXT beat (so it stays in time). It is built first if necessary."""
        if not self.active:
            return
        self.audio.request_track(track_id)
        self.pending = track_id
        self.fade_ms = fade_ms

    def change_track(self, track_id):
        """Switch tracks in the middle of a match: the new one starts on the next beat."""
        self.track = track_id
        self.schedule(track_id)

    def next_track(self):
        """M key: the next track (0..3, then round to 0). Returns its name for the toast."""
        shown = self.settings["music_track"] if self.settings["music_track"] != SHUFFLE else self.track
        self.settings["music_track"] = (shown + 1) % len(TRACK_NAMES)
        self.change_track(self.settings["music_track"])
        return TRACK_NAMES[self.track]

    def stop(self):
        self.pending = None
        if self.active:
            self.audio.stop_music(200)

    # ------------------------------------------------------------------ pause
    def set_paused(self, paused):
        if not self.active:
            return
        if paused:
            self.pause_started = time.monotonic()
            self.audio.pause()
        else:
            if self.ref is not None and self.pause_started is not None:
                wall0, tick0 = self.ref             # the music stood still while paused: move its start time too
                self.ref = (wall0 + time.monotonic() - self.pause_started, tick0)
            self.audio.resume()

    # ------------------------------------------------------------------ the world's events
    def _start_pending(self, world, beat):
        """On every beat: if a track is waiting and ready, start it at exactly this beat."""
        if self.pending is None:
            return
        if not self.audio.music_on:
            self.pending = None
        elif self.audio.play_music_from_beat(self.pending, beat, self.fade_ms):
            self.ref = (time.monotonic(), world.ticks)
            self.pending = None

    def _check_drift(self, world):
        """expected = how long the SIMULATION says the music has been playing; actual = the wall clock."""
        if self.ref is None or self.pending is not None or not self.audio.music_playing():
            return
        wall0, tick0 = self.ref
        if abs((time.monotonic() - wall0) - (world.ticks - tick0) * DT) > DRIFT_LIMIT:
            self.schedule(self.track)

    def follow(self, world):
        """Follow another world's beat WITHOUT restarting the music (the title's attract mode goes on to its next
        battle with a continuing beat count, so the chords stay in step)."""
        self.world = world

    def on_events(self, world, events, quiet=False):
        """Turn what happened in the World into sound. quiet=True (the title's attract mode) plays only the
        music: beat voices and soft capture bells, no effects."""
        if not self.active or world is not self.world:
            return
        audio = self.audio
        launch, biggest_clash, beat_seen = 0.0, 0, False
        for e in events:
            kind = e[0]
            if quiet and kind not in ("beat", "step", "capture"):
                continue
            if kind == "beat":
                beat_seen = True
                self._start_pending(world, e[1])
                if quiet:
                    pass
                elif not world.live:
                    audio.play("tick")                                  # the 3-2-1
                elif e[1] * TICKS_PER_BEAT == world.countdown_ticks:
                    audio.play("newround")                              # "go"
            elif kind == "step":
                self._play_step_voice(world, e[1])
            elif kind == "launch":
                launch = max(launch, 1.0 if e[1] == PLAYER else 0.5)
            elif kind == "clash":
                biggest_clash = max(biggest_clash, e[3])
                self.recent_clash += e[3]
            elif kind == "capture":
                self._play_capture(world, e[2], e[3])
            elif kind == "eliminated":
                audio.play("merge")
            elif kind == "win":
                audio.play("win" if (e[1] == PLAYER or not world.has_player) else "survive")
            elif kind == "lose":
                audio.play("die")
        if launch:
            audio.play("whoosh", launch)                                # at most one per beat
        if biggest_clash:
            audio.play("zap", min(1.0, 0.25 + biggest_clash / 12))     # louder for bigger clashes
        if beat_seen:
            self._update_intensity(world)
        self._check_drift(world)

    def _update_intensity(self, world):
        """How busy is the match right now? 0 = nothing flying, 1 = a big battle. Worked out once per beat."""
        if not world.live or world.over:
            target = 0.0
        else:
            activity = int(world.ships.alive.sum()) + CLASH_WEIGHT * self.recent_clash
            target = max(0.0, min(1.0, (activity - INTENSITY_QUIET) / (INTENSITY_FULL - INTENSITY_QUIET)))
        self.recent_clash *= 0.5                                       # old clashes fade from the memory
        self.audio.set_intensity(target)

    def _play_step_voice(self, world, step):
        """Each alive faction plays its instrument on its own eighth-note slots, louder the more of the map it owns."""
        slot = voice_slot(step, world.alive_factions())
        if slot is None:
            return
        faction, tone = slot
        volume = 0.15 + 0.85 * float(world.shares()[faction - 1])
        self.audio.play_voice(faction, chord_of_step(step), tone, volume)

    def _play_capture(self, world, old, new):
        chord = chord_of(world.ticks // TICKS_PER_BEAT)
        if new == PLAYER and world.has_player:
            self.audio.play_capture(chord)                              # 3 rising bells in the current chord
        elif old == PLAYER and world.has_player:                        # (in watch / attract mode nobody "loses" a node)
            self.audio.play("lost")
            self.audio.duck(0.35, 1.2)
        elif old == 0 or not world.has_player:
            self.audio.play_capture(chord, soft=True)                   # a computer took a node: one soft bell

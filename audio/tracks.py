"""audio/tracks.py - the music tracks as DATA (note names only). No code here.

What it is for : each track is a plain dict. To make your own track: copy one dict, change the
                 note names, give it a new "name", add it to TRACKS, restart the game.
Uses            : nothing.
Used by         : audio/music.py, audio/voices.py, game.py, ui/screens/pause.py, ui/screens/title.py.

All tracks share the same frame so the beat clock works with every one of them:
32 seconds, 120 BPM, 4 chords x 16 beats.

A track dict has:
  name           shown in the menu and the HUD
  chords         4 x (pad notes, bass note). The 4 HIGHEST pad notes are the ones the factions play.
  sparkle_scale  notes for the random high bell sparkles
  pad_tone       loudness of the pad's 2nd and 3rd overtone (higher = brighter sound)
  drums          None, or "soft" (a kick on every beat and a hi-hat on the off-beats)
  sparkles       how many sparkles per loop
  echo           (delay in seconds, loudness) pairs of the ping-pong echo
"""
_ECHO = ((0.375, 0.42), (0.75, 0.3), (1.125, 0.2), (1.5, 0.12))

DRIFT = {
    "name": "DRIFT",                                                  # game2's track
    "chords": [
        (("D3", "F3", "A3", "C4", "E4"), "D2"),                       # Dm9
        (("Bb2", "D3", "F3", "A3"), "Bb1"),                           # Bbmaj7
        (("G2", "D3", "F3", "Bb3", "D4"), "G1"),                      # Gm
        (("A2", "D3", "E3", "G3", "C4"), "A1"),                       # A7sus4
    ],
    "sparkle_scale": ("D5", "F5", "G5", "A5", "C6", "D6"),
    "pad_tone": (0.35, 0.12), "drums": None, "sparkles": 11, "echo": _ECHO,
}

NEON = {
    "name": "NEON",                                                   # bright, hopeful
    "chords": [
        (("F3", "A3", "C4", "E4"), "F2"),                             # Fmaj7
        (("G3", "B3", "D4", "E4"), "G2"),                             # G6
        (("E3", "G3", "B3", "D4"), "E2"),                             # Em7
        (("A3", "C4", "E4", "G4", "B4"), "A2"),                       # Am9
    ],
    "sparkle_scale": ("C5", "D5", "E5", "G5", "A5", "C6"),            # C major pentatonic
    "pad_tone": (0.6, 0.18), "drums": None, "sparkles": 11, "echo": _ECHO,
}

PULSE = {
    "name": "PULSE",                                                  # dark and driving
    "chords": [
        (("C3", "Eb3", "G3", "Bb3", "D4"), "C2"),                     # Cm9
        (("Ab2", "C3", "Eb3", "G3"), "Ab1"),                          # Abmaj7
        (("F2", "Ab2", "C3", "Eb3", "G3"), "F1"),                     # Fm9
        (("G2", "C3", "D3", "F3"), "G1"),                             # G7sus4
    ],
    "sparkle_scale": ("C5", "Eb5", "G5", "Bb5", "C6", "D6"),
    "pad_tone": (0.3, 0.1), "drums": "soft", "sparkles": 9, "echo": _ECHO,
}

DEEP = {
    "name": "DEEP",                                                   # slow, spacious, minimal
    "chords": [
        (("E2", "B2", "F#3", "G3"), "E1"),                            # Em(add9)
        (("C3", "E3", "G3", "B3"), "C2"),                             # Cmaj7
        (("E2", "B2", "F#3", "G3"), "E1"),                            # Em(add9) again
        (("D3", "F#3", "A3", "B3"), "D2"),                            # D6
    ],
    "sparkle_scale": ("E5", "G5", "B5", "D6", "F#6"),
    "pad_tone": (0.15, 0.03), "drums": None, "sparkles": 5,
    "echo": ((0.5, 0.45), (1.0, 0.35), (1.5, 0.27), (2.0, 0.2), (2.5, 0.12)),   # longer echo
}

TRACKS = [DRIFT, NEON, PULSE, DEEP]
TRACK_NAMES = [t["name"] for t in TRACKS]
SHUFFLE = len(TRACKS)                 # the setting value 4 means "pick a random track each match"

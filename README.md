# SWARM CONQUEST

A real-time conquest game on a pure black screen.

You own glowing nodes that breed ships. Drag from your node onto another one and a swarm flies out.
Enemy swarms that meet in mid-air destroy each other, and what gets through lowers the node it reaches;
at zero the node changes colour. Every faction plays its own instrument, and it plays louder the more
of the map it owns. When a faction is wiped out its instrument falls silent, so you can *hear* who is winning.

Everything is made from code: **no image files, no sound files**. Only Python, NumPy and pygame.

---

## Install and run (Windows cmd)

```
pip install -r requirements.txt
python main.py
python -B tests\run_all.py
python tools\export_audio.py --quick
```

1. installs numpy and pygame, 2. starts the game, 3. runs all tests (about a minute),
4. optional: saves the music and sounds as `.wav` files into `exports\` so you can listen to them anywhere.

The first start takes about two seconds ("building the music...") because the soundtrack is calculated
on the spot. Other tracks are built the first time you pick them.

## Controls

| Input | What it does |
| ----- | ------------ |
| Press on your node, drag onto another node, release | send ships from there to there (the target may be your own node: reinforcement) |
| Drag across more of your nodes first | send from several nodes at once (Shift+click adds or removes nodes) |
| Space | select all your nodes, then click a target |
| Mouse wheel or keys 1-4 | how much to send: 25 / 50 / 75 / 100 % |
| M | next music track (it switches on the next beat) |
| P | pause |
| Esc | menu (pauses the match) |
| F1 | how to play |
| H | hints on / off |
| B | bloom (the soft glow around nodes, ships and flashes) on / off; also in the Esc menu |
| F11 / F12 | fullscreen / screenshot into `screenshots\` |
| R on the game-over screen | replay the same map |

---

## Where is what

```
game4/
  main.py            entry point: start pygame, open the window, build the first track, run the Game
  config.py          ALL the numbers: sizes, colours, beat timing, balance, the AI table (tweak live in class!)
  settings.py        load / save / validate settings.json
  game.py            the Game class: main loop, time accumulator, screens, overlays, fades

  core/              the RULES. Pure Python + NumPy, no pygame, so it can be tested without a window
    beat.py            beat / step / chord maths; which faction plays which note
    node.py            the Node dataclass
    ships.py           all ships as NumPy arrays: launch, move, arrive
    combat.py          mid-air clashes (grid-binned)
    mapgen.py          fair, seeded map generation
    world.py           World: tick(), order(), production, captures, events, win / lose
    stats.py           share history and counters (for the game-over graph)
    ai.py              the greedy computer opponent

  audio/             everything you hear
    synth.py           building blocks: sine, decay, bell, pluck, noise, lowpass ... (NumPy only)
    tracks.py          the 4 tracks as DATA (note names only)
    music.py           build_track(): a seamless 32-second loop
    voices.py          build_voices(): the faction instruments (64 notes) and capture bells
    sfx.py             build_sfx(): all event sounds
    player.py          Audio: pygame.mixer playback, volumes, ducking, start music at any beat
    conductor.py       decides WHAT plays WHEN: music sync, track switching, events -> sounds

  graphics/          everything you see in the world
    screen.py          window, scaling modes, fullscreen, screenshots
    fonts.py           font loading with a fallback
    glow.py            glow sprites, vignette, dot grid, fast screen dimming
    starfield.py       the night sky: nebula, twinkling stars, shooting stars
    territory.py       a faint colour wash over the area each faction controls
    draw_nodes.py      nodes, beat pulses and ripples, capacity rings, selection
    draw_ships.py      ships, trails, glow
    effects.py         sparks, rings, flashes, screen shake

  ui/                everything you click or read
    menu.py            one reusable Menu (toggle / slider / choice / action)
    hud.py             power bar, beat dots, timer, track name, hints
    input.py           mouse and keyboard -> selection, drag, actions
    screens/           title (with attract mode), play, pause menu, game over, help

  tests/             run_all.py runs every test_*.py (about 300 checks)
  tools/export_audio.py   optional: write all sounds to exports\*.wav
```

Who uses whom (an arrow means "imports"):

```
main.py --> game.py --> ui/screens/*  --> graphics/*, ui/menu, ui/hud, ui/input
               |
               +------> audio/conductor.py --> audio/player.py --> audio/music, voices, sfx --> audio/synth, tracks
               |
               +------> core/world.py --> core/ships, combat, mapgen, stats, ai, beat, node

config.py is imported by almost everyone.  core/ never imports pygame.
```

The **screen only asks** (`world.order(...)`), the **World decides**. It is like a game server: the client
may request a move, but the rules live in one place and can be tested alone.

---

## How it works

### 1. The beat clock: a metronome everyone follows (`core/beat.py`, `game.py`)
The game runs in tiny **fixed steps** of 1/60 second, called *ticks*. The World counts ticks, and the music
beat comes **only from that counter**: 30 ticks = 1 beat = 0.5 s (120 BPM), 15 ticks = one eighth note.
Ships are produced, orders start and notes play exactly on beats.

Why fixed steps? A real clock is bumpy (a slow frame, a window drag). `Game.run_world` keeps a "piggy bank" of real time
and spends it in 1/60 s coins. A slow frame just spends a few coins in a row, so the game is always the same.
That is also why a match with the same seed is exactly reproducible, and why the tests need no window.

### 2. Ships are NumPy arrays (`core/ships.py`)
Instead of 2000 Python objects, there is one array of x positions, one of y, one of owner and so on
("structure of arrays"). Moving every ship is then **one** line of NumPy instead of a loop. Think of a spreadsheet
column: you change the whole column at once.

### 3. Clashes only check people in the same room (`core/combat.py`)
Checking every ship against every other would be millions of pairs. Instead the screen is cut into small
square "rooms" of 21 px, each ship is put into its room, and only ships in the same room (and every second tick a
room shifted by half) are compared. Two enemy ships that meet destroy each other one for one.

### 4. The greedy AI (`core/ai.py`)
Every few beats, a computer faction looks at each possible target and gives it a score: *how valuable is it, how
close, how many ships would I need?* Then it sends ships to the best targets. "Greedy" means it only
looks at the best move **right now**, with no plan for later. The AI uses `world.order()` exactly like you do, so it can't cheat.
Difficulty (`AI_TABLE` in `config.py`) changes how often it thinks, how many ships it keeps at home, whether it defends,
counter-attacks, and how long it waits at the start.

### 5. Synthesised sound (`audio/`)
Every sound is a sum of sine waves, noise and envelopes calculated with NumPy. Nothing is recorded.
- **Tracks** (`tracks.py`, `music.py`): a track is just a dict of chords. `build_track` turns it into a 32-second
  loop (pad + bass + sparkles) that joins its own start without a click.
- **Beat voices** (`voices.py`, `core/beat.py`): each faction has an instrument (pluck, bell, glass, reed). On its own
  eighth-note slots it plays one **tone of the current chord**, so any mix always sounds harmonious.
  The more of the map it owns, the louder it is. A dead faction stops playing.
- **The rotated-copy trick** (`player.py`): a pygame Sound can only start at its first sample. To start the music at
  beat 20 we make a copy of the loop shifted with `np.roll` so beat 20 *is* sample 0. The music is always started
  **on a beat event** from the World (`conductor.py`), and if the real music and the simulation ever drift apart by more
  than 0.12 s, it is restarted on the next beat.

---

## Make your own track

1. Open `audio/tracks.py` and copy one of the dicts (for example `NEON`).
2. Give it a new `"name"` and change the note names in `"chords"` (four chords, each: pad notes + one bass note) and in
   `"sparkle_scale"`. The four highest pad notes of a chord are the notes the factions play.
3. Add your dict to the `TRACKS` list at the bottom of the file.
4. Start the game. Your track is in the title's MUSIC choice and in the pause menu.

Note names look like `C4`, `Bb2`, `F#3` (letter, optional `#` or `b`, octave number).

## Demo tips for the presentation

- Start on the title screen: the AI-vs-AI "attract mode" is already running and playing music behind the menu.
- Pick **WATCH AI BATTLE**, then press **M** to switch tracks live (the change happens on the beat).
- Point out the music **thinning out** when a faction dies, and the winner's instrument playing a final fanfare.
- Show the **share graph** on the game-over screen: it is the story of the match.
- Open `config.py` and change one number (for example `SHIP_SPEED`), restart, and show the difference.
- Test sound and fullscreen on the presentation machine **before** the class.

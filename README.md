# SWARM CONQUEST

A real-time conquest game on a pure black screen.

You own glowing nodes that breed ships. Drag from your node onto another one and a swarm flies out.
Enemy swarms that meet in mid-air destroy each other, and what gets through lowers the node it reaches;
at zero the node changes colour. Every faction plays its own instrument, and it plays louder the more
of the map it owns. When a faction is wiped out its instrument falls silent, so you can *hear* who is winning.

Some nodes are special (fortresses, factories, relays), there are four difficulty levels, you choose your own colour,
and there is a colour-blind mode. The music gets fuller in big battles.

Everything is made from code: **no image files, no sound files**. Only Python, NumPy and pygame.

---

## Install and run (Windows cmd)

```
pip install -r requirements.txt
python main.py
python -B tests\run_all.py
python tools\export_audio.py --quick
```

1. installs numpy and pygame, 2. starts the game, 3. runs all tests (about a minute, about 450 checks),
4. optional: saves the music and sounds as `.wav` files into `exports\` so you can listen to them anywhere.

The first start takes about two or three seconds ("building the music...") because the soundtrack is calculated
on the spot. Other tracks are built the first time you pick them (a message tells you). The game also creates
`settings.json` (your choices) and `screenshots\` next to `main.py`.

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
| B | bloom (the soft glow around nodes, ships and flashes) on / off |
| C | colour-blind mode on / off |
| F11 / F12 | fullscreen / screenshot into `screenshots\` |
| R on the game-over screen | replay the same map |

## The menus

**Title menu:** PLAY, OPPONENTS (1-3), DIFFICULTY (EASY / NORMAL / HARD / EXTREME), MAP (small / medium / large),
MUSIC (four tracks or shuffle; changing it previews the track on the next beat), **YOUR COLOUR** (cyan / magenta / amber / lime,
the computer opponents get the other colours), WATCH AI BATTLE, HOW TO PLAY, SETTINGS, QUIT.

**Esc menu / SETTINGS:** music on/off, music track, music volume, **DYNAMIC MUSIC** (the battle-intensity layer), sound effects
on/off and volume, hints, **BLOOM**, **COLOUR-BLIND MODE**, screen scaling, fullscreen, restart, quit.

---

## Where is what

```
game4/
  main.py            entry point: start pygame, open the window, build the first track, run the Game
  config.py          ALL the numbers: sizes, colours, beat timing, balance, node kinds, the AI table (tweak live in class!)
  settings.py        load / save / validate settings.json
  game.py            the Game class: main loop, time accumulator, screens, overlays, fades

  core/              the RULES. Pure Python + NumPy, no pygame, so it can be tested without a window
    beat.py            beat / step / chord maths; which faction plays which note
    node.py            the Node dataclass (with its special kind: fortress / factory / relay)
    ships.py           all ships as NumPy arrays: launch, move, arrive
    combat.py          mid-air clashes (grid-binned)
    mapgen.py          fair, seeded map generation (including the special nodes)
    world.py           World: tick(), order(), production, captures, events, win / lose
    stats.py           share history and counters (for the game-over graph)
    ai.py              the greedy computer opponent

  audio/             everything you hear
    synth.py           building blocks: sine, decay, bell, pluck, noise, lowpass ... (NumPy only)
    tracks.py          the 4 tracks as DATA (note names only)
    music.py           build_track(): a seamless 32-second loop; build_energy(): the battle-intensity layer
    voices.py          build_voices(): the faction instruments (64 notes) and capture bells
    sfx.py             build_sfx(): all event sounds
    player.py          Audio: pygame.mixer playback, volumes, ducking, start music at any beat, intensity
    conductor.py       decides WHAT plays WHEN: music sync, track switching, intensity, events -> sounds

  graphics/          everything you see in the world
    screen.py          window, scaling modes, fullscreen, screenshots
    fonts.py           font loading with a fallback
    glow.py            glow sprites, vignette, dot grid, fast screen dimming
    shapes.py          the four faction symbols for colour-blind mode
    starfield.py       the night sky: nebula, twinkling stars, shooting stars
    territory.py       a faint, smooth colour glow over the area each faction controls
    draw_nodes.py      nodes (and their special marks), beat pulses and ripples, capacity rings, selection
    draw_ships.py      ships, trails, glow
    effects.py         sparks, rings, flashes, screen shake

  ui/                everything you click or read
    menu.py            one reusable Menu (toggle / slider / choice / action)
    hud.py             power bar, beat dots, timer, track name, hints
    input.py           mouse and keyboard -> selection, drag, actions
    screens/           title (with attract mode), play, pause menu, game over, help

  tests/             run_all.py runs every test_*.py: beat, mapgen, world, combat, ai, audio, settings,
                     nodes (special nodes), colors (colour-blind palette), game, visuals, perf
  tools/export_audio.py   optional: write all sounds to exports\*.wav
  PLAN.md            the original specification;  PROGRESS.md  what was built, why, and what changed afterwards
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

There are four levels: EASY, NORMAL, HARD and EXTREME. The table `AI_TABLE` in `config.py` sets how often the AI thinks,
how many missions it plans at once, how many ships it keeps at home, whether it defends, whether it counter-attacks, and how
long it waits at the start. The tests play the levels against each other, so a higher level really beats a lower one.

### 5. Synthesised sound (`audio/`)
Every sound is a sum of sine waves, noise and envelopes calculated with NumPy. Nothing is recorded.
- **Tracks** (`tracks.py`, `music.py`): a track is just a dict of chords. `build_track` turns it into a 32-second
  loop (pad + bass + sparkles) that joins its own start without a click.
- **Beat voices** (`voices.py`, `core/beat.py`): each faction has an instrument (pluck, bell, glass, reed). On its own
  eighth-note slots it plays one **tone of the current chord**, so any mix always sounds harmonious.
  The more of the map it owns, the louder it is. A dead faction stops playing.
- **Dynamic intensity** (`music.py` `build_energy`, `conductor.py`, `player.py`): every track has a second loop of the same
  length (a soft high shimmer and a few extra bells, no drums) playing on its own channel, started together with the base loop.
  On every beat the conductor counts the ships in the air (and recent clashes) and tells the player how busy the match is; the
  player eases that layer's **volume** up and down. So big battles sound fuller and quiet moments thin out. Only volumes change,
  never the notes, so it can't go out of tune or out of time. DYNAMIC MUSIC in the Esc menu switches it off.
- **The rotated-copy trick** (`player.py`): a pygame Sound can only start at its first sample. To start the music at
  beat 20 we make a copy of the loop shifted with `np.roll` so beat 20 *is* sample 0. The music is always started
  **on a beat event** from the World (`conductor.py`), and if the real music and the simulation ever drift apart by more
  than 0.12 s, it is restarted on the next beat.

### 6. Special nodes (`core/node.py`, `core/mapgen.py`, `core/world.py`)
Some neutral nodes are special, and you can tell them apart by their outline (hover one to read what it does):
- **FORTRESS** (double ring with four towers): only every second attacking ship hurts a defender, so its defenders count double.
- **FACTORY** (turning gear): makes twice the ships per beat.
- **RELAY** (diamond): the ships launched from it fly 1.5x faster.

The map generator hands them out with its own dice, so a seed still gives the same positions as before; on a 2-player map a
node's mirrored twin gets the same kind, so the map stays fair. Start nodes are always plain. The AI counts a fortress as
twice as expensive and likes factories. The numbers are in `config.py` (`KIND_MIX`, `FORTRESS_SHIELD`, `FACTORY_BOOST`, `RELAY_SPEED`).

### 7. Your colour and colour-blind mode (`config.py` `apply_palette`, `graphics/shapes.py`)
**YOUR COLOUR** in the title menu chooses which of the four colours you play; the computer opponents get the rest.
Colour-blind mode (key **C**) swaps the four colours for cyan, red, pale yellow and magenta and puts a symbol
(circle, square, triangle, diamond) on every node and next to every name, so colour is never the only clue. That palette was
chosen by *simulating* the three common kinds of colour blindness and keeping the smallest difference between any two factions
as large as possible (`tests/test_colors.py` re-checks it). The colours live in dicts that are changed *in place*, so every
file that imported them sees the new palette at once.

### 8. Looking good and staying fast (`graphics/`)
Everything pretty is drawn **additively** (light adds up, like real light) and from pictures made once with NumPy: the glow
around nodes, the starfield, the soft territory glow. The territory glow is worked out on a coarse grid with one matrix product
and a little noise ("dithering") hides the brightness steps. Whole-screen darkening uses a ready-made picture instead of
`fill(..., BLEND_MULT)`, which is about 30 times slower. `tests/test_perf.py` prints the timings: with 2000 ships in the air a
whole frame takes under 10 ms of the 16.7 ms available at 60 FPS. BLOOM in the menu turns the glow off.

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
- Show the music getting **fuller in a big battle** (and switch DYNAMIC MUSIC off to hear the difference).
- Hover the **special nodes** and show a fortress taking twice the ships.
- Press **C** and **B** live: colour-blind mode and bloom change the whole picture at once.
- Show the **share graph** on the game-over screen: it is the story of the match.
- Open `config.py` and change one number (for example `SHIP_SPEED`), restart, and show the difference.
- Test sound and fullscreen on the presentation machine **before** the class.

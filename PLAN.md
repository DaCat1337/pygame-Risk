# PLAN: "Swarm Conquest" (working title) — a beat-synced neon territory game

You are implementing a new game from scratch in this folder (`game4\`). Read this whole plan
before writing code. Build it in the phases at the end, and run the tests after every phase.

The owner is a student returning to coding who will **present this game to a programming class**.
They must be able to understand the code afterwards, so it is split into many small, clearly named
files (§10). Clarity beats cleverness.

## 0. The pitch (what it must feel like)

A Galcon/Auralux-style real-time conquest game on a **pure black OLED screen**:

- About 20 glowing circles (**nodes**) float on black. The nodes you own slowly produce tiny dots
  (**ships**).
- Drag from your node to another node and half its ships stream over as a glowing swarm.
- When enemy swarms meet in mid-air they **annihilate in sparks**. Whatever gets through lowers the
  target's garrison, and at zero the node flips to your colour.
- Win by owning everything.

**The twist: the gameplay _is_ the music.**

- The game runs on the beat of a generated ambient track. There are several tracks to pick from in
  the settings, all at 120 BPM with 4 chords.
- Production happens on the beat, and launches snap to the next beat.
- Each faction (colour) owns an instrument that plays an arpeggio on its own beat slots. Its
  volume follows the faction's share of the map, so the winning side gets louder. When a faction
  is eliminated, its instrument goes silent, and you can _hear_ it.
- Every capture rings a bell **in the current chord**, so it always sounds good.

The priorities are **looks cool, sounds great, simple to play, fun for 3–5 minute matches**,
in that order. Keep the rules simple; spend the effort on juice: pulses, glows, sparks and sound.

## 1. Hard requirements

- Python 3.10+, **NumPy + Pygame only** (`requirements.txt`: `numpy>=1.24`, `pygame>=2.5`).
  - Use only pygame APIs that exist in both `pygame` and `pygame-ce`.
  - `pygame.gfxdraw` is fine for antialiased circles.
- **Multiple files** with the exact layout in §10. Run the game with `python main.py` from inside
  `game4\`.
- **No asset files.** All graphics are drawn in code, and all sounds are synthesised with NumPy.
- **Logical resolution 1920×1080**, opened with `pygame.SCALED | pygame.FULLSCREEN` and an F11
  toggle.
  - Everything is vector-drawn (circles, lines, text), so drawing at native 1080p gives perfectly
    sharp lines on a 1080p monitor and a clean 2× on 4K.
  - On a 1440p monitor (1.33×), or when shrinking to a small window, use the smooth stretch.
    Copy `screen_scaling_mode()` and the `PYGAME_FORCE_SCALE=photo` logic from
    `..\game2\main.py`, but compare against 1920×1080 instead of 1280×720.
  - **Every pixel number in this plan is already for 1920×1080.**
  - The windowed mode (F11) opens at 1600×900 via SCALED. That keeps the window on-screen on a
    1080p monitor with a taskbar, and the mouse coordinates stay correct.
- 60 FPS target with up to **2000 ships** on screen on an average laptop.
- No sound device, or a failed font load, must never crash the game. It just stays silent or uses
  the default font.
- **Do not modify anything outside `game4\`.**
  - The only exception is the backups (§14): you may create **new** folders inside
    `..\backups\`, but never change or overwrite existing ones.
  - `..\game2\` (the Lenia game) is the reference. Read it, copy from it, never edit it.
  - No git commands. Do not delete files.
- Code style:
  - Readable for a student. Every file starts with a short docstring: _what this file is for_,
    _which files it uses_, and _which files use it_.
  - Short docstrings on functions that explain _why_, and plain-English comments at the tricky
    spots (beat clock, collisions, AI, sound synthesis).
  - No over-engineering, no classes where a function will do, no metaclasses or decorators beyond
    `@dataclass`/`@staticmethod`.
  - Aim for **≤ 400 lines per file**. If a file grows past that, split it along an obvious line.

## 2. Reuse from `..\game2\main.py` (copy, do not import)

game4 must run on its own, so **copy** the code below into the game4 files named in the table. Do
not import it from game2.

| Copy                                                                                                                                   | To game4 file                             | Change                                                                                                                                                                                                                                                                                             |
| -------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SR`, `_time`, `_noise`, `_box_lowpass`, `_sweep`, `_bell`, `_layer`, `_finish`, `_add_wrap`, and the inner `pluck` from `build_music` | `audio/synth.py`                          | make them public: drop the leading underscore (`time_axis`, `noise`, `lowpass`, `sweep`, `bell`, `layer`, `finish`, `add_wrap`, `pluck`), and give each a one-line plain-English docstring                                                                                                         |
| `build_music()`                                                                                                                        | `audio/music.py`                          | turn it into `build_track(track)`, which takes a track definition (§7) instead of hard-coded chords. No baked arpeggio (the factions play it live) but **keep** the pad, sub-bass, sparkles and echo. Loop length stays 32.0 s. Track 1 "DRIFT" must reproduce game2's pad/bass/sparkles exactly.  |
| `build_sfx()`                                                                                                                          | `audio/sfx.py`                            | keep `click`, `hover`, `tick`, `on`, `off`, `menu_open`, `menu_close`, `launch`, `impact`, `die`, `survive`, `merge`, `camera`, `newround`, `wrong`. Remove the Lenia-only sounds (`drop`, `scatter`, `wall`, `erase`, `nutrient`, `rotate`, `one`, `split`, `correct`). Add the new ones from §7. |
| `Audio` class                                                                                                                          | `audio/player.py`                         | keep the mixer re-open at 22050 Hz, the reserved music channel 0, the `_curve`, ducking, `MIN_GAP` and background building in a thread. Use `set_num_channels(32)`. Add the track and beat-voice features from §7.                                                                                 |
| `build_glow`, `make_icon`, `Effects` (rings, bursts, shake)                                                                            | `graphics/glow.py`, `graphics/effects.py` | recolour to the faction colours, sizes ×1.5                                                                                                                                                                                                                                                        |
| `load_settings` / `save_settings` pattern                                                                                              | `settings.py`                             | new keys (§9)                                                                                                                                                                                                                                                                                      |
| Esc menu with sliders (`menu_layout`, `_menu_event`, `_draw_menu`)                                                                     | `ui/menu.py`                              | turn it into a small reusable `Menu` class (items = toggle / slider / choice / action) used by the title menu **and** the Esc menu                                                                                                                                                                 |
| `make_screen`, `screen_scaling_mode`, `main()` structure, F12 screenshot                                                               | `main.py`, `graphics/screen.py`           | 1920×1080, new caption                                                                                                                                                                                                                                                                             |

## 3. Timing: the beat clock (the most important design decision)

- **BEAT = 0.5 s** (120 BPM). **STEP = BEAT / 2 = 0.25 s**, an eighth note.
- Every music track loops in 32 s = 64 beats = 128 steps.
- The current chord is `(beat // 16) % 4`.
- The simulation runs at a **fixed timestep `DT = 1/60` s**, so one beat is exactly 30 sim ticks
  and one step is 15 ticks.
  - `World.tick()` advances one tick and increments `world.ticks`.
  - Beats and steps are derived from `world.ticks`, _never_ from the wall clock. That keeps the
    simulation **deterministic** and testable without audio. All of it lives in `core/beat.py` as
    small pure functions: `beat_of(ticks)`, `step_of(ticks)`, `chord_of(beat)`,
    `is_beat_tick(ticks)` and so on.
- In `game.py`, use the classic accumulator (a "piggy bank" of elapsed real time):
  - Add the real elapsed time to it.
  - Run `World.tick()` while it holds ≥ DT, at most 8 ticks per frame.
  - Clamp it to 0.25 s after a long stall (window drag).
- **Music alignment, the "rotated copy" trick.** A pygame `Sound` can only start at its first
  sample. To start the music _at any beat_, make a copy of the track array rotated with `np.roll`
  so that its sample 0 is that beat's position (`beat * BEAT * SR` samples into the loop), then
  play the copy on channel 0 with `loops=-1`.
  - Put this in `audio/player.py` as `Audio.play_music_from_beat(track_id, beat)`.
  - The copy is about 2.8 MB and is cheap to make. Cache the last rotated copy.
  - Use it to:
    1. start a match: play from beat 0 at tick 0 with `fade_ms=250`,
    2. start the music late if it was still building when the match began: play from the next
       beat,
    3. **switch tracks mid-match** from the Esc menu: play the new track from the next beat,
    4. resync after a pause or stall: `game.py` remembers the wall-clock time and beat at which
       the music was started, and if expected vs actual sim time drifts by more than 0.12 s, it
       restarts from the next beat.
  - The title screen just loops the selected track from beat 0.
- **Pause** (Esc menu or P):
  - Stop ticking and call `pygame.mixer.pause()`.
  - On resume, call `unpause()` and reset the last-frame timestamp; the paused time does not count.
- The `World` emits **events** as a list that `game.py` drains each frame, e.g. `("beat", b)`,
  `("step", s)`, `("capture", node, old, new)`, `("launch", owner, n)`, `("clash", x, y, n)`,
  `("eliminated", owner)`, `("win", owner)`.
  - `game.py` hands them to the sound and visual code.
  - Sound is triggered when the event is drained, at most 1 frame (16 ms) after the beat, which is
    inaudible.

## 4. The world (pure logic, **no pygame**, fully testable)

Everything in `core/` must not import pygame.

### Factions

- `0` = neutral (grey).
- `1` = player (cyan).
- `2`, `3`, `4` = computer opponents (magenta, amber, lime).
- Opponents: 1–3 (setting).

### Nodes (`core/node.py`, a small `@dataclass`)

- `x, y, radius, size` (size class 1/2/3), `owner`, `garrison` (float, shown as int), `cap`.
- Radius by size: 24 / 39 / 57 px.
- Production **per beat** = `size` ships (1/2/3), only if `owner != 0` and `garrison < cap`.
- `cap = 40 * size`.
- Neutral garrison at start = `size * rng.integers(4, 11)`. Neutrals never produce.
- Start nodes: one per faction, size 3, garrison 30.

### Map generation (`core/mapgen.py`, `generate_map(seed, n_factions, map_size)`)

- Node count: SMALL 12, MEDIUM 18, LARGE 26 (including the start nodes).
- Keep a play margin of 90 px from the screen edges, plus 100 px at the top for the HUD bar.
- **Fairness:**
  - With 2 factions, generate _half_ the map and mirror it through the screen centre (point
    symmetry). The two start nodes are mirror images.
  - With 3–4 factions, put the start nodes on an evenly spaced ellipse around the centre (random
    rotation) and fill the rest with rejection sampling. Minimum gap between node edges: 42 px.
    Give up and retry with `seed+1000` after 2000 failed attempts.
- Size mix: about 50% size 1, 35% size 2, 15% size 3.
- Same seed + same settings ⇒ identical map. Show the seed on the game-over screen and allow
  "replay this map".

### Ships (`core/ships.py`, NumPy arrays: structure of arrays, for speed)

- A `Ships` class holding `pos (N,2) float32`, `vel (N,2) float32`, `owner (N,) int8`,
  `target (N,) int16` and `alive (N,) bool`.
- Fixed capacity `MAX_SHIPS = 3000` with free-slot reuse via `np.flatnonzero(~alive)`.
- Total cap per faction: 1200 ships in flight. Production still goes into garrisons.
- Speed `SHIP_SPEED = 195` px/s. Steer toward the target node's centre.
  - Each ship keeps a small fixed **lane offset**: a perpendicular offset in `[-0.6, 0.6] × target
radius`, chosen at launch. Swarms then look like streams, not a single line.
  - Ships fly straight and do **not** avoid other nodes. That's simpler and reads fine visually.
- **Arrival:** when a ship is within the target's radius:
  - Same owner → `garrison += 1`.
  - Otherwise → `garrison -= 1`. If the garrison drops below 0, the node is **captured**: `owner =
ship.owner`, `garrison = 1` (or `abs`), and a `capture` event fires.
  - The ship is removed.

### Orders (`core/world.py`)

- `world.order(sources, target, fraction, owner)`:
  - Only from nodes the owner owns. `n = floor(garrison * fraction)`, at least 1 if garrison ≥ 1.
    Subtract `n` from the garrison **immediately**, so the UI is honest.
  - Queue the ships for the **next beat**.
  - On that beat, **emit them over the following beat**, i.e. spread across 30 ticks at
    `ceil(n/30)` per tick. Each ship spawns on the source's rim, facing the target.
  - Fractions: 25 / 50 / 75 / 100%, default 50%.

### Mid-air combat (`core/combat.py`, "smash them together")

Ships of **different owners** that come within `CLASH_DIST = 10` px annihilate one-for-one. Do it
vectorised:

1. Each tick, compute a grid cell per ship with cell size 21 px:
   `cell = (x//21) * W_CELLS + (y//21)`.
2. On odd ticks, shift the grid by half a cell (+10.5 px) before binning, so pairs on a cell
   border are caught on the next tick.
3. For each cell holding ships of 2+ owners, remove `k = smallest per-owner count in that cell`
   ships from **every** owner present in it. Use `np.unique` and `np.lexsort`; no Python loop over
   all ships.
4. Return **one** clash record per cell (centre position, number killed) for sparks and sound.
   Sound is throttled later.

This is not perfectly physical, but it is fast, deterministic and looks right: two equal swarms
cancel out in a shower of sparks. Explain it in the docstring with the analogy "only check people
in the same room for a fight".

### Elimination and win (`core/world.py`)

- A faction is **eliminated** when it owns no nodes and has no ships in flight or queued.
- The player **wins** when all opponents are eliminated and **loses** when eliminated.
- In WATCH mode (AI vs AI), the match ends when one faction remains.
- Safety: after 12 minutes of sim time, the faction with the most nodes, then the most ships, wins.

### Stats (`core/stats.py`)

- Every 2 beats, record each faction's share of all ships (garrisons + in flight). Keep a list of
  these snapshots for the graph.
- Also record per faction: nodes captured, ships launched, ships lost, peak node count, and the
  match time.

## 5. Computer opponents (`core/ai.py`, simple "greedy" AI)

`ai_think(world, faction, difficulty, rng) -> list of orders`, called on beats only:

|                      | EASY    | NORMAL  | HARD                                                  |
| -------------------- | ------- | ------- | ----------------------------------------------------- |
| thinks every         | 4 beats | 2 beats | 1 beat                                                |
| max orders per think | 1       | 2       | 3                                                     |
| reserve kept at home | 40%     | 25%     | 15%                                                   |
| reaction to attacks  | no      | yes     | yes, plus counter-attacks the attacker's weakest node |

Put the table in `config.py` as a dict, so it can be tweaked live in class.

Algorithm (greedy = always take the best-looking move right now):

1. For each candidate target node not owned by this faction:
   - `needed = garrison + incoming_enemy_ships_to_it + (size * beats_to_arrive if owned by an
enemy)`, where `beats_to_arrive = distance / (SHIP_SPEED * BEAT)` from the nearest own node.
   - `score = (size * 3 + (8 if owner == 0 else 4)) / (needed + 4 + distance / 90)`.
   - Prefer neutrals early, which happens naturally because their `needed` is low.
   - Slight bias toward attacking the player on HARD: × 1.15.
2. Pick the best-scoring target and gather sources from the nearest own nodes until the sendable
   ships exceed `needed * 1.2 + 3`. Sendable = garrison above the reserve. If it can't, skip this
   target and try the next.
3. **Defend** (NORMAL/HARD): if enemy ships incoming to one of its nodes exceed that node's
   garrison + production before arrival, send help from its nearest other node first.
4. Use only `world.order(...)`, the same function the player uses. The AI never cheats.

Determinism: give each AI its own `np.random.default_rng(seed + faction)` and use it only for
tie-breaking.

## 6. Visual style ("OLED neon", all sizes for 1920×1080)

- **Background:** pure black `(0,0,0)`.
  - A very faint dot grid every 60 px at about 8% brightness. It brightens briefly (to about 18%)
    on every **chord change**, every 16 beats.
  - A gentle vignette, pre-rendered once and applied with `BLEND_MULT`.
- **Colours:**
  - Player cyan `(0,230,255)`.
  - AI magenta `(255,60,140)`, amber `(255,180,0)`, lime `(150,255,80)`.
  - Neutral grey `(110,110,125)`.
  - Text white `(235,240,255)`, dim text `(120,130,150)`.
  - Define them all in `config.py`.
- **Fonts:**
  - `SysFont("consolas,menlo,dejavusansmono")` with a fallback.
  - Sizes: HUD 22, node numbers 22/26/32 by size, menu 30, titles 96.
  - Load them once in `graphics/fonts.py`.
- **Nodes** (`graphics/draw_nodes.py`):
  - A thin 3 px antialiased outline (`gfxdraw.aacircle` at r, r-1 and r-2).
  - A very faint inner fill (alpha about 25).
  - An additive glow sprite behind it (`build_glow`, cached per colour/radius, `BLEND_ADD`).
  - The garrison number centred.
  - **Beat pulse:** on every beat, each _owned_ node's outline radius pops +6 px and eases back
    (exp decay ~0.15 s), and its glow flares. The whole map breathes with the music.
  - Capacity ring: a thin arc around the node showing `garrison / cap`.
  - Orbiting dots: up to 10 tiny dots circling the node, as many as `garrison / 4`. Cosmetic only.
  - Capture: the colour **cross-fades** over 0.3 s instead of snapping.
- **Ships** (`graphics/draw_ships.py`):
  - A 3×3 px dot plus a short 9 px trail line (`pos - vel*0.05`) in the faction colour.
  - A Python loop over ≤ 2000 ships with `pygame.draw.line` is OK. If too slow, batch by owner and
    write pixels with `pygame.surfarray`.
- **Effects** (`graphics/effects.py`):
  - Clash: a spark burst of 6–10 short-lived particles in **both** colours, plus a tiny white
    flash.
  - Capture: an expanding ring in the new colour, a particle burst and a short light screen shake
    (3 px).
- **Territory tint (optional, last phase,** `graphics/territory.py`**):**
  - A soft Voronoi tint showing who controls which area.
  - Compute the nearest _owned_ node on a coarse 192×108 grid with NumPy, colour it at about 7%
    alpha and `smoothscale` it up.
  - Update it only on captures.
- **HUD, top** (`ui/hud.py`):
  - A thin stacked **power bar** across the screen: each faction's share of all ships.
  - Left: match time and the **track name**. Right: **four beat dots** that light up in turn, so
    the sync is visible.
  - Send-fraction indicator: `SEND 50%`.
- **Hints, bottom** (`ui/hud.py`, toggle H): `Drag from your node to send · Wheel/1-4 = send % ·
Space = all nodes · Esc = menu`.
- **Selection feedback** (`ui/input.py` state, drawn by `graphics/draw_nodes.py`):
  - Selected nodes get a dashed rotating ring.
  - While dragging, draw a glowing line from each selected node to the cursor.
  - A hovered target gets a bright ring, plus a small "needs ~N" label if it is enemy or neutral.
- Every screen transition fades (0.25 s).

## 7. Sound design

### Music tracks (`audio/tracks.py` holds the data, `audio/music.py` builds them)

All tracks share the same frame so the beat clock works with every one of them: **32 s, 120 BPM,
4 chords × 16 beats**.

- A track is a plain dict:
  ```
  {"name": ..., "chords": [(pad_notes, bass_note), ...4],
   "sparkle_scale": [...], "pad_tone": ..., "drums": ...}
  ```
- Write the notes as **names** (`"D3"`, `"Bb2"`, `"F#4"`). A helper `note_hz("A4") == 440.0`
  converts them with equal temperament (each semitone ×2^(1/12)). That's much less error-prone
  than typing Hz, and it teaches the idea.

| #   | Name      | Mood                                 | Chords (pad notes · bass)                                                                                         | Extras                                                                                                                              |
| --- | --------- | ------------------------------------ | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| 1   | **DRIFT** | game2's track, which the owner loves | Dm9 `D3 F3 A3 C4 E4 · D2`; Bbmaj7 `Bb2 D3 F3 A3 · Bb1`; Gm `G2 D3 F3 Bb3 D4 · G1`; A7sus4 `A2 D3 E3 G3 C4 · A1`   | as game2. Must match it.                                                                                                            |
| 2   | **NEON**  | bright, hopeful                      | Fmaj7 `F3 A3 C4 E4 · F2`; G6 `G3 B3 D4 E4 · G2`; Em7 `E3 G3 B3 D4 · E2`; Am9 `A3 C4 E4 G4 B4 · A2`                | brighter pad (stronger 2nd overtone), sparkles from C major pentatonic                                                              |
| 3   | **PULSE** | dark, driving, for HARD fights       | Cm9 `C3 Eb3 G3 Bb3 D4 · C2`; Abmaj7 `Ab2 C3 Eb3 G3 · Ab1`; Fm9 `F2 Ab2 C3 Eb3 G3 · F1`; G7sus4 `G2 C3 D3 F3 · G1` | **soft drums** baked in: a kick on every beat (sine sweep 110→45 Hz, decay 9), a filtered-noise hi-hat on every off-beat (decay 60) |
| 4   | **DEEP**  | slow, spacious, minimal              | Em(add9) `E2 B2 F#3 G3 · E1`; Cmaj7 `C3 E3 G3 B3 · C2`; Em(add9) again; D6 `D3 F#3 A3 B3 · D2`                    | darker pad (fewer overtones), only 5 sparkles, longer echo                                                                          |

Rules for the tracks:

- **Seamless loops** with the same cos² window and wrap-around technique as game2.
- The same peak level (0.6), so switching tracks never jumps in loudness.
- The setting `music_track`: 0–3 picks a track; **4 = SHUFFLE**, which picks a random track at the
  start of each match and never the same one twice in a row.
- Building: in a background thread, build the selected track first, then the others lazily on
  first use. About 1–2 s each.
- The faction beat voices and capture bells always use **the current track's chords**.

### Beat voices (the music _is_ the game, `audio/voices.py`)

- For the current track, pre-build **4 instruments × 4 chords × 4 chord tones** = 64 short
  `Sound`s:
  - Each note is about 1.8 s with its own ping-pong echo tail baked in.
  - Tone `i` of chord `c` = the 4 highest pad notes of the chord, times 2 (one octave up), like the
    plucks in game2.
  - Rebuild them in the background when the track changes. Until they're ready, keep playing the
    old set.
- Instruments, all built from `audio/synth.py`:
  - Player: **pluck** (game2's `pluck`).
  - Faction 2: **bell**, `bell(f, 1.8, 3.0)`.
  - Faction 3: **glass**: `sin(f) + 0.3*sin(3f)` with a fast-decaying 5× partial.
  - Faction 4: **soft reed**: a low-passed square at half volume.
- Pan: player 0.4, factions 2/3/4 at 0.65 / 0.3 / 0.75.
- **Slots:** step `s` (eighth notes) goes to faction `alive[s % len(alive)]`, counting alive
  factions only. With 2 factions this sounds like call and response.
  - Note index: `order = (0,1,2,3,2,1,3,2)`, tone = `order[(s // len(alive)) % 8]`.
  - Put the slot maths in `core/beat.py`, which is pure and testable.
- Volume = `0.15 + 0.85 * share_of_total_ships`. Beat voices follow the **music** volume setting,
  because they _are_ the music.
- An eliminated faction stops playing.
- If `alive` is only the winner, it plays every step for the final fanfare.

### Event sounds (add these to `audio/sfx.py`)

| Event                               | Sound                                                                                                                             |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| select own node                     | `click`                                                                                                                           |
| hover a node                        | `hover` (MIN_GAP 0.06)                                                                                                            |
| order given                         | a short soft `send` blip: `sweep(500, 900, 0.08)` with fast decay                                                                 |
| ships actually launch (on the beat) | a quieter shortened `launch` whoosh (0.3 s), at most 1 per beat                                                                   |
| clash                               | `zap`: a tiny high noisy tick, `noise*exp(-t*120)` plus a 2–3 kHz sine. Heavily rate-limited (MIN_GAP 0.05), volume by kill count |
| **capture by player**               | 3 rising bells from the **current chord** tones (build `capture_0..3` per track along with the voices)                            |
| capture by AI from neutral          | a single soft bell in the chord                                                                                                   |
| **player loses a node**             | `lost`: a falling sweep 600→150 Hz with a low thump (short `impact`), plus a music duck of depth 0.35                             |
| faction eliminated                  | `merge` (slow chord swell)                                                                                                        |
| win                                 | `survive` extended: the 4-bell run twice, the second time an octave up                                                            |
| lose                                | `die`                                                                                                                             |
| menu open/close, toggles            | `menu_open`, `menu_close`, `on`, `off`                                                                                            |
| screenshot                          | `camera`                                                                                                                          |

Throttling rules: never more than about 12 SFX per second total, except beat voices. `MIN_GAP`
per sound as in game2.

### Bonus (optional, last)

`tools/export_audio.py` writes every track, SFX and voice to `exports\*.wav`, like the
game2 backup's `export_audio.py`. The owner enjoys listening to them.

## 8. Controls (`ui/input.py` turns mouse/keys into actions; `game.py` performs them)

| Input                                  | Action                                                                         |
| -------------------------------------- | ------------------------------------------------------------------------------ |
| Left-press on your node                | select it (Shift+click adds or removes nodes)                                  |
| Drag over more of your nodes           | add them to the selection while dragging                                       |
| Release over another node              | send `SEND%` from all selected nodes to it (it can be your own: reinforcement) |
| Release over empty space / right-click | cancel                                                                         |
| Space                                  | select all your nodes (then click a target)                                    |
| Mouse wheel or 1–4                     | send fraction 25 / 50 / 75 / 100%                                              |
| M                                      | next music track (switches on the next beat, shows a toast with the name)      |
| P                                      | pause                                                                          |
| Esc                                    | menu (pauses single-player)                                                    |
| F1                                     | how-to-play overlay                                                            |
| H                                      | hints on/off                                                                   |
| F11                                    | fullscreen on/off                                                              |
| F12                                    | screenshot to `screenshots\`                                                   |
| R (on the game-over screen)            | replay the same map                                                            |

Also make the click-target to _select_ a node generous (radius + 15 px).

## 9. Screens and menus (`ui/screens/*.py`, using the `Menu` class from `ui/menu.py`)

1. **Title** (`ui/screens/title.py`):
   - An AI-vs-AI match runs in the background at 40% brightness. It's "attract mode", and it is
     great for the class presentation.
   - The big title with a slow glow pulse on the beat.
   - Menu: `PLAY`, `OPPONENTS 1/2/3`, `DIFFICULTY EASY/NORMAL/HARD`, `MAP SMALL/MEDIUM/LARGE`,
     `MUSIC ◀ DRIFT ▶`, `WATCH AI BATTLE`, `HOW TO PLAY`, `SETTINGS`, `QUIT`.
   - Changing the track on the title switches the music immediately, so you can preview it.
   - Keyboard (arrows/Enter) and mouse both work.
2. **Playing** (`ui/screens/play.py`): as above. A 3-2-1 countdown, one per beat, before ticking
   starts producing.
3. **Esc menu** (`ui/screens/pause.py`):
   - `RESUME`, `MUSIC on/off`, `MUSIC TRACK` (DRIFT/NEON/PULSE/DEEP/SHUFFLE), `MUSIC VOLUME`
     slider, `SFX on/off`, `SFX VOLUME` slider, `HINTS`, `SCREEN SCALING (restart)`
     AUTO/SMOOTH/PIXEL-EXACT, `FULLSCREEN`, `RESTART MATCH`, `QUIT TO TITLE`, `QUIT GAME`.
   - Copy the slider behaviour from game2.
4. **Game over** (`ui/screens/gameover.py`):
   - `VICTORY` or `DEFEATED` in the faction colour.
   - A **share graph**: stacked area or lines of each faction's share over time, drawn with thin
     glowing lines. It's the "story of the match".
   - The stats table, the seed, and `R replay map · Enter new map · Esc title`.
5. **How to play** (`ui/screens/help.py`): 5 short lines and a tiny animated diagram (optional).

**Settings** (`settings.py`, saved as `settings.json` next to `main.py`; validated and clamped like
game2; an invalid file gives the defaults and never crashes):

`music_on, music_vol (0.5), music_track (0 = DRIFT), sfx_on, sfx_vol (0.7), hints (True),
scaling (0), opponents (1), difficulty (1 = NORMAL), map_size (1 = MEDIUM), send_fraction
(1 = 50%)`

## 10. File layout (create exactly this; each file has one clear job)

```
game4/
  main.py                 entry point only (~40 lines): start pygame, choose scaling, open the
                          window, create Audio + Game, run
  config.py               ALL constants: screen size, colours, timing (BEAT, STEP, DT), balance
                          numbers, AI table, font sizes. The file to tweak live in class.
  settings.py             load/save/validate settings.json
  game.py                 the Game class: owns the World, Audio, screens; main loop, accumulator,
                          event routing, music sync. It should read like a table of contents.

  core/                   the game rules: pure Python + NumPy, NO pygame (testable)
    __init__.py
    beat.py               beat/step/chord maths, voice slot maths
    node.py               Node dataclass
    ships.py              Ships (NumPy arrays): spawn, move, arrive
    combat.py             grid-binned mid-air clashes
    mapgen.py             generate_map (fair, seeded)
    world.py              World: tick(), order(), production, captures, events, win/lose
    stats.py              share history + per-faction counters
    ai.py                 ai_think (greedy AI)

  audio/                  everything you hear
    __init__.py
    synth.py              building blocks: sine, decay, sweep, noise, lowpass, bell, pluck,
                          layer, finish, note_hz (NumPy only)
    tracks.py             the 4 track definitions (note names, data only)
    music.py              build_track(track) -> seamless 32 s loop (NumPy only)
    voices.py             build_voices(track) -> the 64 faction notes + capture bells (NumPy only)
    sfx.py                build_sfx() -> all event sounds (NumPy only)
    player.py             Audio class: pygame.mixer playback, volumes, ducking,
                          play_music_from_beat, background building

  graphics/               everything you see in the world
    __init__.py
    screen.py             make_screen, screen_scaling_mode, screenshot
    fonts.py              font loading with fallback
    glow.py               glow sprites (cached), vignette, background dot grid
    draw_nodes.py         nodes, pulses, capacity rings, selection rings
    draw_ships.py         ships and trails
    effects.py            particles, rings, sparks, screen shake
    territory.py          optional Voronoi tint

  ui/                     everything you click or read
    __init__.py
    menu.py               reusable Menu class (toggle / slider / choice / action items)
    hud.py                power bar, beat dots, timer, track name, send %, hints, toasts
    input.py              mouse/keyboard -> selection, drag, actions
    screens/
      __init__.py
      title.py            title + attract mode
      play.py             the playing screen (draws world + HUD, handles input)
      pause.py            Esc menu
      gameover.py         result, share graph, stats
      help.py             how to play

  tests/
    run_all.py            runs every test file, prints ALL TESTS PASSED (N checks)
    helpers.py            tiny check() counter, dummy SDL drivers
    test_beat.py  test_mapgen.py  test_world.py  test_combat.py  test_ai.py
    test_audio.py  test_settings.py  test_game.py  test_perf.py

  tools/
    export_audio.py       optional: write all sounds to exports\*.wav

  README.md
  requirements.txt
```

**Dependency direction (no circular imports):**

- `config` ← `core/*` ← `audio/*` ← `graphics/*`, `ui/*` ← `game` ← `main`.
- `core` and the NumPy-only audio files never import pygame. Only `audio/player.py` does.
- Imports are absolute from the `game4` folder, e.g. `from core.world import World`.
- `main.py` and `tests/run_all.py` make sure the folder is on `sys.path`.

## 11. Tests (`tests/`, headless)

Use `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy`, set in `tests/helpers.py`. Use plain
asserts with a check counter, like `..\game2\test_lenia.py`; no pytest needed. Run everything from
the `game4` folder with `python -B tests\run_all.py`. Each test file can also run on its own.

- **test_beat:**
  - Beat/step/chord of a tick.
  - Voice slots for 2/3/4 alive factions; an eliminated faction never gets a slot.
  - `note_hz("A4") == 440`, `note_hz("A3") == 220`.
- **test_mapgen:**
  - Deterministic per seed.
  - No overlapping nodes (edge gap ≥ 42).
  - All nodes inside the margins.
  - The 2-player map is point-symmetric.
  - Correct node counts for all sizes and faction counts.
  - Generation succeeds for 200 different seeds.
- **test_world:**
  - Production: an owned node gains `size` per beat and nothing between beats; neutrals never
    grow; it stops at the cap.
  - Orders: the garrison drops immediately; ships appear only from the next beat and are all out
    within one more beat; you can't order from a node you don't own; 100% leaves 0.
  - Arrival: reinforcing your own node adds ships, attacking subtracts, and overflow captures
    with the correct leftover and fires a `capture` event.
  - Elimination and win events.
- **test_combat:**
  - Two equal swarms sent at each other along the same line cancel to 0 ships.
  - 30 vs 20 leaves about 10. Allow ± a few, because of the lanes.
  - Ships of the same owner never clash.
- **test_ai:**
  - Only returns orders from nodes it owns.
  - Never sends below its reserve.
  - EASY/NORMAL/HARD are all valid.
  - **AI vs AI** (seed 1, 2 factions, NORMAL) finishes with a winner within 12 sim-minutes,
    deterministically: the same seed gives the same winner and the same tick count twice.
- **test_audio:**
  - Every track is exactly 32 s, int16 stereo, has no clipping and a smooth loop seam (copy
    game2's seam test).
  - The track peaks are within 10% of each other.
  - DRIFT matches game2's chord frequencies to 0.01 Hz.
  - Voices: 64 built per track; every capture bell frequency is a tone of its chord.
  - `play_music_from_beat`'s rotation: sample 0 of the rotated array equals sample
    `beat*BEAT*SR` of the original.
  - `Audio(enabled=False)` is silent and safe.
- **test_settings:** garbage JSON, wrong types and out-of-range values (including `music_track`)
  all give the defaults.
- **test_game (smoke test):**
  - Create `Game` with the dummy drivers.
  - Inject events: start a match, drag-send from the player start node to a neutral, press M
    (track change), open and close the Esc menu, change a slider, run 600 frames of update+draw.
  - Win and lose screens render (force them with a helper).
- **test_perf:** with 2000 ships in flight, `World.tick()` averages < 3 ms and one full `draw()`
  at 1920×1080 < 14 ms on the dummy driver. Print the numbers and only warn, not fail, if slower.

## 12. README.md (for presenting in class)

Include these sections:

- What the game is.
- Install and run (Windows cmd one-liners: `pip install -r requirements.txt`, `python main.py`,
  `python -B tests\run_all.py`).
- Controls.
- **"Where is what" — a file map:** the tree from §10 with one line per file, plus the
  dependency arrow from §10 drawn as a simple text diagram.
- **"How it works"** in plain English, each with a pointer to the file:
  - The beat clock and fixed timestep, with an analogy: a metronome everyone follows
    (`core/beat.py`, `game.py`).
  - Ships as NumPy arrays (`core/ships.py`).
  - Grid-binned clash detection, with an analogy: only checking people in the same room
    (`core/combat.py`).
  - The greedy AI (`core/ai.py`).
  - Synthesised sound, the tracks, the beat voices and the rotated-copy trick (`audio/`).
- **"Make your own track"**: copy a dict in `audio/tracks.py`, change the note names, restart.
- **"Demo tips for the presentation"**: start WATCH AI BATTLE, press M to switch tracks live,
  point out the music thinning when a faction dies, and show the share graph.

## 13. Build phases (run the tests after each one; do not move on with failing tests)

The 6 phases are grouped into **3 checkpoints** (§14). Within a checkpoint, go straight from one
phase to the next without waiting: run the tests, fix them, make the backup, update PROGRESS.md,
and continue. Only stop at the end of a checkpoint.

1. **Rules:**
   - `config.py`, everything in `core/` except `ai.py`.
   - `tests/helpers.py`, `run_all.py`, `test_beat`, `test_mapgen`, `test_world`, `test_combat`.
   - There is no pygame in this phase.
2. **Seeing and playing:**
   - `graphics/*` (without territory), `ui/input.py`, `ui/hud.py`, `ui/screens/play.py`,
     `game.py`, `main.py`.
   - Playable vs an opponent that does nothing.
   - `test_game` (first version).
3. **AI:** `core/ai.py` and `test_ai`, including the deterministic AI-vs-AI match.
4. **Audio:**
   - `audio/*`: synth, tracks, music, voices, sfx, player.
   - Music alignment via `play_music_from_beat`, pause and track switching.
   - `test_audio`.
5. **Screens:** `ui/menu.py`, title with attract mode, pause menu, `settings.py` +
   `test_settings`, game over with the share graph, help, fullscreen and screenshot.
6. **Polish:**
   - Capture colour cross-fade, chord-change grid flash, the optional territory tint.
   - `test_perf`, README, the optional `tools/export_audio.py`.

At the end, report:

- what you built,
- the test output (the check count),
- the measured tick and draw times,
- anything you could not verify. You cannot hear the audio; say so, and describe how you checked
  it instead.

## 14. Workflow: speed, checkpoints, backups, progress

The owner has **one day** and wants everything done fast. Work efficiently: write whole files in
one go, don't ask questions the plan already answers, and don't add features that aren't in the
plan.

### Checkpoints (the only places where you stop and wait for the owner's "go")

| Checkpoint               | Phases                                | The owner checks                                                                                                                 |
| ------------------------ | ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **A: Playable game**     | 1 Rules + 2 Seeing and playing + 3 AI | runs `python main.py`, plays a match vs the AI, says whether dragging swarms feels fun, and tweaks `config.py` numbers if needed |
| **B: Sound and screens** | 4 Audio + 5 Screens                   | listens to all tracks and sounds (you cannot hear them), clicks through the title, Esc menu and game over                        |
| **C: Finished**          | 6 Polish + README                     | final run-through                                                                                                                |

At each checkpoint, give a short plain-English summary of:

- what was built and which files it is in,
- the test output,
- **the 2–3 key ideas the owner should understand** (with a file pointer each),
- exactly what to try by hand.

The owner's "go" at a checkpoint approves creating and editing the files of the next checkpoint's
phases.

### Backups (after every phase whose tests pass)

There is no git, so copy the folder. Run this from `game4\`'s parent folder, in Windows cmd
(e.g. `cmd /c` from your shell):

```
robocopy game4 "backups\game4 phase1" /E /XD __pycache__ /XF settings.json
```

- Replace `phase1` with the phase number: `phase2`, ...; after a fix at a checkpoint use
  `phase3 fix1` etc.
- **Never reuse an existing backup folder name.** Check first; if it exists, append ` b`.
- robocopy exit codes 0–7 mean success. Only 8 and above are errors.
- Mention the backup folder name in your summary.

### PROGRESS.md (your memory between sessions)

Keep `game4\PROGRESS.md` up to date after every phase:

- phases done, with their backup folder,
- the current test count,
- deviations from the plan and why,
- known issues and the owner's tweaks (for example config values they changed).

If a session runs out of context, a new session continues with "Read PLAN.md and PROGRESS.md,
continue". So PROGRESS.md must be enough to pick up where you left off.

### If time runs short: the cut list (cut from the top, never from the bottom)

1. Territory tint (§6, already optional).
2. `tools/export_audio.py`.
3. The help-screen animation.
4. Tracks PULSE and DEEP (keep DRIFT + NEON and SHUFFLE between them).
5. The share graph on the game-over screen (keep the stats text).
6. Attract mode behind the title (plain black title instead).

**Never cut:** tests, the AI, the beat sync, the faction beat voices, or DRIFT. Those are the game
and what the owner explains in class.

### Owner's side (for reference; not your task)

- After checkpoint C: **code freeze.** Only fixes, no new features.
- Prepare the presentation:
  - read the README's "How it works" and explain each part out loud once,
  - test on the presentation machine (projector resolution, fullscreen, **sound through the room's
    speakers**),
  - demo plan: WATCH AI BATTLE → explain the beat sync → press M to switch tracks → play a quick
    match → show the share graph.
- Fallback: the Lenia game in `..\game2\` still works if anything breaks.

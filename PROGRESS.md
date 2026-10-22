# PROGRESS (read PLAN.md first, then this file)

Continue with: "Read PLAN.md and PROGRESS.md, continue".

## Phases
| Phase | Status | Backup folder (in ..\backups) | Tests |
| ----- | ------ | ----------------------------- | ----- |
| 1 Rules | done | `game4 phase1` | 111 checks |
| 2 Seeing and playing | done | `game4 phase2` | 152 checks |
| 3 AI | done | `game4 phase3`, fix: `game4 phase3 fix1` | 171 checks |
| 4 Audio | done | `game4 phase4` | 242 checks |
| 5 Screens | done | `game4 phase5`, VFX pass: `game4 phase5 fix1`, bug fixes: `game4 phase5 fix2` | 293 checks |
| 6 Polish + README | done | `game4 phase6`; owner's copy of the finished game: `game4 finished v1` (everything incl. settings.json) | 303 checks |
| after v1: bloom fix + option | done | `game4 phase6 fix1` | 315 checks |
| after v1: smooth territory glow | done | `game4 phase6 fix2` | 319 checks |
| after v1: softer launch sounds | done | `game4 phase6 fix3` | 323 checks |
| finished v2 (slogan removed from title, README and help) | done | `game4 finished v2` (everything incl. settings.json) | 323 checks |
| v3 idea 1: node types | done | `game4 phase6 fix4` | 345 checks |
| v3 idea 2: dynamic music intensity | done | `game4 phase6 fix5` | 379 checks |
| v3 idea 3: colour-blind mode | done | `game4 phase6 fix6` | 403 checks |
| v3 feedback: calmer dynamic music + DYNAMIC MUSIC toggle, new TOUGH difficulty | done | `game4 phase6 fix7` | 414 checks |
| v3 feedback: difficulties renamed, YOUR COLOUR choice | done | `game4 phase6 fix8` | 449 checks |
| v3 feedback: MATCH LENGTH (matches were too short) | done | `game4 phase6 fix9` | 460 checks |
| finished v4 (owner: "it works great now") | done | `game4 finished v4` (everything incl. settings.json) | 460 checks |
| finished v3 (README rewritten; node types, dynamic music, colour-blind mode, 4 difficulties, colour choice) | done | `game4 finished v3` (everything incl. settings.json) | 449 checks |

**Checkpoint C reached (everything in the plan is built). Next: the owner's final run-through; after that code freeze (fixes only).**

After finished v2, the owner chose 3 ideas: node types, dynamic music intensity, colour-blind mode.
- **Node types** (config.NODE_*, KIND_*; core/node.py `kind`, `absorbed`, `shield`): FORTRESS (every 2nd attacking ship bounces off, so
  defenders count double), FACTORY (production x2), RELAY (ships launched from it fly 1.5x faster). Only neutral nodes get a kind
  (`KIND_MIX` 14 / 12 / 10 %, `mapgen._assign_kinds`, own dice so positions/sizes/garrisons of a seed are unchanged); on a 2-faction
  map the mirrored twin gets the same kind; start nodes are always plain. Drawn as: double ring with 4 towers / turning gear / diamond;
  hover shows a tooltip (KIND_HELP). AI: `needed` is multiplied by `node.shield`, factories score +4. `world.needed_to_capture` ("needs ~N")
  counts the shield. tests/test_nodes.py (19 checks) is new.

- **Dynamic music intensity**: `audio/music.build_energy(track)` = a second loop (high shimmer, doubled sparkles, quiet 16th hats, soft kick
  unless the track has drums), same length, peak 0.35. `Audio` plays it on channel 1 (now 2 reserved channels), started together with
  the base loop; only its volume changes (`set_intensity`, eased in `update`: rise 1.2 s, fall 3 s time constants; the base loop is
  15% quieter in quiet moments, `BASE_DIP`). `Conductor._update_intensity` runs on every beat: activity = ships in the air + 8 x
  recent clash casualties; target = min(1, activity/150) ** 0.6 (`INTENSITY_FULL`, `INTENSITY_CURVE`); 0 during the countdown and after
  the match is decided. Track build time is ~1 s longer (energy layer built in the same background thread; startup wait ~2.5 s).
  Cannot be judged by ear here: checked by numbers (peaks, loop edges, channel volumes over a simulated match).

- **Colour-blind mode** (setting `colorblind`, key C, Esc menu toggle): `config.apply_palette()` updates FACTION_COLORS / FACTION_NAMES /
  COLOR_NAMES IN PLACE (so `from config import FACTION_COLORS` everywhere sees it). Palette cyan (89,255,255), red (255,50,0),
  pale yellow (237,255,165), magenta (255,0,255), found by a random search + hill climb maximising the smallest CIELAB difference under
  protan / deutan / tritan simulation (worst pair dE 43; the default palette: protan 7). Shapes (config.FACTION_SHAPES, graphics/shapes.py)
  on owned nodes, in the HUD names and the game-over table. `Game.apply_palette()` repaints (NodeView.refresh_colors, territory glow,
  title text). Not changed in colour-blind mode: menu accent colour (still cyan) and the window icon. tests/test_colors.py.

- Owner: "the always-playing new sound is annoying" -> `build_energy` is now purely tonal (soft shimmer + a few extra bells; the drums, kick and
  16th hats are gone), peak 0.30, the intensity has a silent zone (`INTENSITY_QUIET` 30 ships in the air -> 0, `INTENSITY_FULL` 170 -> 1,
  linear in between) and eases more slowly (rise 2 s, fall 4 s). New setting `dynamic_music` (Esc menu "DYNAMIC MUSIC"): off = energy layer
  silent at once and the base loop never dips (`Audio.set_dynamic`). The menu rows are 50 px high now so the longer Esc menu fits.
- Owner: "HARD is too hard, I want a level between HARD and NORMAL" -> new difficulty TOUGH (config.DIFFICULTIES is now EASY, NORMAL, TOUGH, HARD):
  think every 3 beats, 1 mission, keeps 32% home, waits 4 beats, defends, no counter-attack (HARD: every 2 beats, 2 missions, 25%, no wait,
  counter-attacks). AI-vs-AI over 48 matches (12 maps x 2 sizes x sides swapped): TOUGH beats NORMAL 46/48, HARD beats TOUGH 47/48; median match
  length NORMAL-vs-TOUGH 75 s, HARD matches ~30 s. NOTE: a saved `difficulty` of 2 (the old HARD) is now TOUGH; HARD is index 3.
  The title's attract battles use HARD by name. Settings accept 0..3.

- Owner: rename tough -> HARD and hard -> EXTREME: `DIFFICULTIES = (EASY, NORMAL, HARD, EXTREME)`; the old TOUGH numbers are now `AI_TABLE["HARD"]`,
  the old HARD numbers `AI_TABLE["EXTREME"]` (`AI_PLAYER_BIAS_EXTREME`). Saved indices keep their meaning (2 = the middle-hard level, now called HARD;
  3 = EXTREME). Attract battles on the title use EXTREME. (Earlier PROGRESS notes below still say TOUGH / HARD in the OLD naming.)
- Owner: "choose your colour in the menu instead of always being blue": new setting `player_color` (0..3, default 0) and a title-menu choice
  "YOUR COLOUR" (value drawn in that colour with a dot; labels follow colour-blind mode via a function-valued `labels` in ui/menu.py).
  `config.apply_palette(colorblind, player_color)`: you (faction 1) get the picked colour of the set, the opponents the remaining colours in menu
  order; colour names follow (FACTION_NAMES[1] stays "YOU"). `config.color_choices(colorblind)` lists the four (rgb, name). Applies at once
  (Game.apply_palette repaints nodes, territory glow and the title text). Instruments are still tied to the faction number, not the colour.
  Only in the title menu (not in the in-match Esc menu).

- Owner: "AI matches only last a minute or two, can we change that?" -> measured AI-vs-AI (tools: scratch scripts, 16 maps x both sides): two EQUAL AIs
  mostly stall to the 12-minute limit; the short matches are the lopsided ones (EXTREME v HARD 30 s, EXTREME v NORMAL 28 s, HARD v NORMAL 92 s) because
  captured nodes add production and the stronger side snowballs. Three brakes, chosen together by the new title-menu choice MATCH LENGTH
  (setting `pace`, default 2 = LONG; `config.PACE_NAMES`, `_PACES`, live dict `PACE`, `apply_pace(index)`):
  SHORT = old rules; MEDIUM = 1.5 attackers per defender, 8 beats of unrest after a capture, ships at 77% speed; LONG = 2.0 / 8 / 77%.
  Measured median match: MEDIUM 62 / 55 / 131 s, LONG 91 / 90 / 196 s for the same three pairs (stalls to 12 min: 0-3 of 32 on MEDIUM, 2-7 of 32 on LONG).
  Code: `Node.shield = PACE["defence"] + FORTRESS_BONUS (fortress only; was x2 -> now +1 so a fortress is not absurd on LONG)`, `Node.unrest`
  (counted down in `World._on_beat`, set in `_land` on capture), `PACE["speed"]` in ships.launch / world.needed_to_capture / ai (`_per_beat()`),
  fractional defence handled in `World._land` (`floor(absorbed / shield)`). `SHIP_SPEED` stays the base for all presets. The "needs ~N" label and
  the AI count the defence. The rule tests run at SHORT (`apply_pace(0)` at the start of test_world / combat / ai / nodes), Game tests at the
  default LONG. NOTE: the earlier notes about the fortress ("defenders count double") describe SHORT.

After finished v1 (owner: "every ~12 beats the circles stop giving light"):
- Cause found by measuring the light around a node frame by frame: a dip every 16 beats (the chord changes, ~8 s). The dot grid was
  a whole-screen picture blitted with an alpha, which dimmed the sky and territory wash underneath it, and the chord-change
  "flash" (alpha 255) blacked them out for a moment. Introduced when the starfield/territory were added. Fix: `glow.draw_grid()`
  draws the dots with BLEND_ADD (light is only ever added). Regression tests in test_visuals.
- New setting `bloom` (default on): key **B**, the Esc/Settings menu ("BLOOM (GLOW)"). Off = no soft glow around nodes, no ship halos,
  no additive flashes (rings, sparks, stars, territory stay). Saved in settings.json; old files get bloom on.

- Owner: "the dim light zone after a capture is blocky". Cause: `territory.py` used hard Voronoi borders (nearest node wins) at
  192x108 plus only ~18 brightness levels (banding). Now: each owned node is a soft Gaussian lamp (`REACH` 210 px), lamps ADD (colours
  mix where pools meet), a fixed dither noise hides the banding, and a capture cross-fades the glow over 0.8 s instead of popping.
  Speed: the Gaussian is separable, so one matrix product per faction: compute 41 -> 6 ms, fade redraw (20x/s) ~6 ms.
  Tweak in graphics/territory.py: `STRENGTH` (0.08), `REACH`, `FADE_SECONDS`.

- Owner: "the sound when the little things go out of the circle is too harsh". Changed in audio/sfx.py: `whoosh` (every launch beat)
  was a rising sine whistle (150 -> 1100 Hz) over thinly filtered white noise; now a low slow rise (200 -> 340 Hz) under triple-smoothed
  noise with a smooth swell (spectral centroid 465 -> 260 Hz, energy above 1 kHz 4.6% -> 0.1%). `send` (when you give an order) is
  lower (380 -> 520 Hz, was 500 -> 900) with a 12 ms fade-in. NOT changed: `zap` (mid-air clash tick, centroid 3.7 kHz, 28% above
  3 kHz) is the sharpest remaining sound - the next candidate if it is still too harsh. Unverified by ear (numbers + tests only).

Checkpoint B feedback from the owner and what was done (phase5 fix2 + phase 6):
- *"music didn't start until I moved the volume slider"*: real bug in `audio/player.py`. pygame's own `fade_ms` on `Channel.play`
  resets the channel to FULL volume when the fade ends (measured: 0.33 -> 1.0), so the slider was ignored until touched.
  Now the Audio class fades in itself (`_fade_in`, `_apply_music_volume`); regression test in test_audio.
  Also: the first track was built in a background thread WHILE the game drew frames (GIL contention: 1.8 s of work took ~9 s,
  silent title meanwhile). `Game.wait_for_music()` (called by main.py) now builds it first behind "building the music..." (~1.5 s).
  Other tracks are still built lazily when first chosen; a toast says "building it first, starts when ready".
- *"overlapping music in the menu"*: probable causes fixed: (1) a computer losing a node in attract/watch mode played the
  "lost" sound and DUCKED the music (faction 1 was treated as "the player"); (2) every new attract battle jumped the tick
  counter forward by up to half a beat, so the music looked "out of sync" and restarted (a hard cut with a fade-in).
  Battles now continue the tick counter exactly. Cannot be verified by ear here.
- *"circles light up too much on the beat"*: node glow flare 0.45 -> 0.2, outline pop 6 -> 3 px (`PULSE_PIXELS`), ripple alpha 120 -> 55.
- *"background could be cooler, stars"*: `graphics/starfield.py` (dim nebula, 340 twinkling stars on 3 parallax depth layers,
  a shooting star every 10-25 s) and the plan's optional `graphics/territory.py` (7% Voronoi wash, 192x108 grid, only on captures).
- Speed lesson 2: `surf.fill(colour, special_flags=BLEND_MULT)` over the whole screen costs ~15 ms. Everything that dims the
  screen now goes through `graphics/glow.dim()` (cached flat picture blitted with BLEND_MULT, ~0.5 ms). Title draw 25 ms -> 7 ms.
- `tests/test_visuals.py` is new (split from test_game.py to stay under 400 lines). `tests/test_perf.py` prints the timings.
- `tools/export_audio.py` (stdlib `wave`): `python tools\export_audio.py --quick` (tracks + effects) or without `--quick`
  (also all 256 instrument notes). `settings.py` now takes the highest `music_track` value from `audio/tracks.SHUFFLE`, so adding a
  5th track needs no other change.
- Measured (dummy driver, ~2000 ships in the air): `World.tick()` ~0.4-0.7 ms, full play-screen `draw()` ~9 ms, title `draw()` ~7 ms.

(Checkpoint A was approved by the owner: "feels very good already". Owner feedback: the AI is too hard -> needs real difficulty levels (phase 5 title menu + retuning `AI_TABLE`), better sounds (phase 4), better VFX (phase 6 polish).)

## Deviations from the plan (and why)
- **Mirror centre of the 2-faction map** is the centre of the *play area* (960, 590), not the screen centre
  (960, 540). The HUD takes 100 px at the top, so mirroring through the screen centre would push nodes into
  the HUD margin. (core/mapgen.py: `CENTER`)
- `clash` events carry the two owners: `("clash", x, y, n, owner_a, owner_b)` (plan: `x, y, n`) so sparks can
  use both colours.
- `combat.py` uses `np.unique` + a stable `np.argsort` instead of `np.lexsort`; same result, simpler.
- `World(..., nodes=None)` accepts a hand-made node list (for tests) and `countdown_beats` for the 3-2-1.
- `note_hz` test (plan puts it in test_beat) moves to `test_audio` in phase 4, because `note_hz` lives in audio/synth.py.

- `settings.py` + `tests/test_settings.py` were written in phase 2 (not phase 5) because `Game` needs the settings
  (send fraction, hints, opponents ...). Out-of-range *volumes* are clamped like game2; out-of-range *whole
  numbers* (track, opponents ...) fall back to the default.
- `graphics/glow.py` also holds `build_grid` (dot grid); `ui/screens/play.py` also holds `WorldView` (draws a
  world; the title's attract mode will reuse it). The chord-change grid flash and the colour cross-fade
  (phase 6 in the plan) are already in, because they were a few lines each.
- Phase-2 placeholders that later phases replace: Esc quits the game (menu = phase 5), M shows a toast
  (music = phase 4), F1 shows a toast (help = phase 5), end-of-match is a simple banner (game over screen = phase 5),
  `Game.on_world_events` is empty (sound = phase 4).
- Speed lesson: every Surface that is blitted each frame must be 32 bit like the screen (`convert()`), otherwise
  the blit is 5-10x slower. Measured: full draw with 2000 ships ~8 ms.

- AI details: `ai_think` returns `(source, target, fraction)` tuples; `max_orders` counts *missions* (one target,
  possibly several source nodes). `needed` = garrison - ships we already sent + (for enemy nodes) the defender's own
  reinforcements on the way + its production while we fly. The AI only sees ships that are flying (not the enemy's
  queued orders), and it subtracts its own ships already on the way, so it does not spam one target.
- `World.add_opponents(difficulty)` creates the AI players (`core/ai.py: Opponent`); `Game.start_match` calls it.
- A stray file `prof.out` (my profiling output) is in game4\ - harmless, delete it by hand if you like (I may not delete files).

- Phase 4 additions: `audio/conductor.py` (not in the plan's file list) holds the music start/switch/resync logic and
  the event -> sound routing, so game.py stays short (plan §10: "split along an obvious line"). `Game.music` is the Conductor.
- `World.tick()` keeps the metronome (step/beat events, `ticks`) running after the match is decided, so the winner's
  instrument can play the final fanfare; nothing else moves after `over`.
- Voice notes: pluck / bell / glass / reed, 1.8 s with a baked echo, peak 0.3 so several can ring together. Music tracks
  peak at 0.6 (all four within 10%). Loop pad/bass are game2's; DRIFT uses exact-equal-temperament Hz (differs from
  game2's 2-decimal Hz by < 0.005 Hz); the sparkle level is a bit higher than game2 because the arpeggio is gone.
- Checked numerically instead of by ear: dominant pitch of each instrument = requested note; music + 4 voices at full
  volume peaks at ~1.0 only in the unrealistic worst case (all voices at volume 1.0 and music volume 1.0).
- test_game uses a fake wall clock (test frames run faster than real time) for the music-sync checks.

- Phase 5: all five screens exist (title with attract mode, play, Esc menu, game over with share graph, help with a small
  animation). `Game` shows the title first; screens fade (0.25 s); the Esc menu / game over / help are *overlays*
  (`Game.overlay`) on top of the current screen. F11 / F12 work on every screen (handled in `Game.handle_event`).
- The Conductor ignores events from worlds it is not following (`Conductor.begin(world)` / `follow(world)`), so the
  title's attract battles and a new match never confuse each other. Attract battles carry the beat count over, so the
  music never restarts between battles. Attract mode is quiet (no zaps/whooshes), only voices and soft bells.
- Menu arrows are drawn as triangles (not the characters in the plan) so they never depend on the font.
- Game over appears 1.6 s after the match ends; the metronome keeps ticking, so the winner's instrument plays the fanfare.
- Watch mode names the factions CYAN / MAGENTA / AMBER / LIME (`config.COLOR_NAMES`) instead of "YOU".
- **AI difficulty retuned after the owner said "the AI is too hard"** (config.AI_TABLE, new column `start_delay`):
  EASY thinks every 10 beats, waits 24 beats (12 s) before its first move, keeps 60% home, never defends;
  NORMAL every 4 beats, 1 mission, waits 10 beats, keeps 40%; HARD every 2 beats, 2 missions, keeps 25%, counter-attacks.
  Measured AI-vs-AI (10 maps, sides swapped): NORMAL beats EASY, HARD beats NORMAL, in every match (tests lock this in).
  NORMAL vs NORMAL mostly ends in the 12-minute time limit (two careful AIs stalemate); a human breaks that.
  The title's attract battles use HARD so they stay lively.

- **VFX pass (owner asked for better VFX; done early at checkpoint B, polish phase 6 continues):** glow ring around every
  ship (additive, `draw_ships.HALO_STRENGTH`), additive light flashes on clashes (bigger clash = bigger flash/more sparks/a ring)
  and a node-sized flash + 3 shockwave rings on captures, and a sonar ripple that leaves every owned node on each beat
  (`draw_nodes.WAVE_*`). Measured: full draw with 2000 ships ~7 ms.

## Balance finding (for the owner at checkpoint A)
AI vs AI is much faster than the 3-5 minutes the plan wants: median 30-60 s on MEDIUM (see test_ai output). Reason:
production is `size` ships per beat (3 per half second on a big node) and the AI snowballs. Levers in config.py
(nothing was changed): `AI_TABLE` (reserve, think_every), `SHIP_SPEED`, `START_GARRISON`, `NEUTRAL_GARRISON_PER_SIZE`,
and production per beat (currently `Node.production = size`, in core/node.py).
Experiment (8 seeds, medians): SHIP_SPEED 110 -> little change; slower AI (reserve 0.5/0.4, think_every 4/2,
speed 120) -> NORMAL 90 s. A human vs AI match may be longer or shorter - judge by playing first.

## Known issues / owner tweaks
- Not verifiable here: real window, fullscreen/F11 window size, mouse feel, and ALL sound (no ears) - see test_audio for what was checked.
- phase3 fix1: `python main.py` crashed ("No video mode has been set") because `build_glow` called `.convert()` while `main.py` builds the window icon before the window exists. Fixed, and test_game now builds the icon with no display.

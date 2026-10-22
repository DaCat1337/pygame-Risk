"""tests/test_game.py - smoke test: a whole Game with fake events, run with no window and no sound card.

It walks through the title menu, plays frames of a match, drags an order, uses the keys, opens the
Esc menu / help / game-over screens, and runs a long AI battle with real (dummy-device) audio.
It cannot judge how things LOOK - it only proves nothing crashes and the controls do what they say.
"""
import os
import tempfile
import types

import helpers
from helpers import check
import pygame

from config import PLAYER, SEND_FRACTIONS
from game import Game
from ui.input import node_at
from ui.screens.difficulty import DifficultyScreen
from ui.screens.gameover import GameOverScreen
from ui.screens.help import HelpScreen
from ui.screens.pause import PauseScreen

DT_FRAME = 1 / 60


def mouse(kind, pos, button=1):
    if kind == pygame.MOUSEMOTION:
        return pygame.event.Event(kind, pos=pos, rel=(0, 0), buttons=(1, 0, 0))
    return pygame.event.Event(kind, pos=pos, button=button)


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="")


def frames(game, n):
    for _ in range(n):
        game.update(DT_FRAME)
        game.draw()


def start_match(game, seed=11, has_player=True):
    """Start a match and wait for the 0.25 s screen fade to finish."""
    game.start_match(seed, has_player)
    frames(game, 18)


def run():
    pygame.init()
    pygame.display.quit()                                   # main.py makes the icon BEFORE any window exists: test that order
    from graphics.glow import make_icon
    check(make_icon().get_width() == 64, "the window icon can be built before the window exists")
    screen = pygame.display.set_mode((1920, 1080))
    shots = tempfile.mkdtemp()
    game = Game(screen, audio=None, settings_path=None, shots_dir=shots)
    check(game.current is game.title and game.title.world is not None, "the game starts on the title screen with an attract battle")

    # --- the title menu (keyboard)
    menu = game.title.menu
    frames(game, 130)
    check(game.title.world.ticks > 100 and game.running, "the attract battle runs behind the title")
    game.handle_event(key(pygame.K_DOWN))
    game.handle_event(key(pygame.K_RIGHT))
    check(game.settings["opponents"] == 2, "title menu: Down then Right = OPPONENTS 2")
    game.handle_event(key(pygame.K_LEFT))
    game.handle_event(key(pygame.K_LEFT))
    check(game.settings["opponents"] == 3, "choices wrap round (1 -> 3)")
    game.handle_event(key(pygame.K_RIGHT))
    game.handle_event(key(pygame.K_DOWN))
    game.handle_event(key(pygame.K_RETURN))
    check(isinstance(game.overlay, DifficultyScreen), "DIFFICULTY in the title menu opens the difficulty page")
    frames(game, 2)
    game.handle_event(key(pygame.K_LEFT))
    check(game.settings["difficulty"] == 0, "AI LEVEL can be set to EASY on that page")
    game.handle_event(key(pygame.K_ESCAPE))
    check(game.overlay is None, "Esc closes the difficulty page")
    game.handle_event(key(pygame.K_DOWN))
    game.handle_event(key(pygame.K_RIGHT))
    check(game.settings["map_size"] == 2, "MAP can be set to LARGE")
    game.settings.update(opponents=1, difficulty=1, map_size=1)
    # --- title menu (mouse): hover and click HOW TO PLAY, close it, open SETTINGS and drag a slider
    row = menu.rows[menu.items.index(next(i for i in menu.items if i.key == "help"))]
    game.handle_event(mouse(pygame.MOUSEMOTION, row.center))
    game.handle_event(mouse(pygame.MOUSEBUTTONDOWN, row.center))
    check(isinstance(game.overlay, HelpScreen), "clicking HOW TO PLAY opens the help overlay")
    frames(game, 3)
    game.handle_event(key(pygame.K_ESCAPE))
    check(game.overlay is None, "Esc closes the help")
    game.handle_event(key(pygame.K_F1))
    check(isinstance(game.overlay, HelpScreen), "F1 opens the help")
    game.handle_event(mouse(pygame.MOUSEBUTTONDOWN, (100, 100)))
    check(game.overlay is None, "a click closes the help")
    row = menu.rows[[i.key for i in menu.items].index("settings")]
    game.handle_event(mouse(pygame.MOUSEBUTTONDOWN, row.center))
    check(isinstance(game.overlay, PauseScreen) and not game.overlay.pauses, "SETTINGS opens the settings page")
    frames(game, 2)
    sm = game.overlay.menu
    i_vol = [it.key for it in sm.items].index("music_vol")
    track = sm.slider_track(sm.rows[i_vol])
    game.handle_event(mouse(pygame.MOUSEBUTTONDOWN, (track.x + track.w // 4, track.centery)))
    game.handle_event(mouse(pygame.MOUSEBUTTONUP, (track.x + track.w // 4, track.centery)))
    check(abs(game.settings["music_vol"] - 0.25) < 0.02, "dragging the volume slider sets the volume")
    sm.sel = [it.key for it in sm.items].index("hints")
    hints = game.settings["hints"]
    game.handle_event(key(pygame.K_RETURN))
    check(game.settings["hints"] != hints, "Enter toggles HINTS in the settings page")
    game.handle_event(key(pygame.K_ESCAPE))
    check(game.overlay is None, "Esc closes the settings page")

    # --- PLAY starts a match (with a fade)
    game.handle_event(key(pygame.K_UP))
    menu.sel = 0
    game.handle_event(key(pygame.K_RETURN))
    check(game.fade is not None and game.fade[0] == "out", "PLAY starts a fade out")
    game.handle_event(key(pygame.K_DOWN))
    check(menu.sel == 0, "input is ignored while the screen fades out")
    frames(game, 18)
    check(game.current is game.play and game.fade is None, "after the fade the match is on screen")
    game.start_match(11)
    frames(game, 12)
    play = game.play
    world = play.world
    check(game.current is play and not world.live, "a match starts with the 3-2-1 countdown running")
    frames(game, 100)                                       # 90 countdown ticks
    check(world.live and world.ticks >= 90, "the countdown ends and the match goes live")

    # --- drag from the player's start node to the farthest neutral node
    start = world.owned(PLAYER)[0]
    sn = world.nodes[start]
    neutral = max((i for i, n in enumerate(world.nodes) if n.owner == 0),
                  key=lambda i: (world.nodes[i].x - sn.x) ** 2 + (world.nodes[i].y - sn.y) ** 2)
    nn = world.nodes[neutral]
    before = sn.garrison
    game.handle_event(mouse(pygame.MOUSEBUTTONDOWN, (sn.x, sn.y)))
    check(play.input.selection == [start] and play.input.dragging, "pressing on your node selects it")
    game.handle_event(mouse(pygame.MOUSEMOTION, (nn.x, nn.y)))
    frames(game, 2)                                         # draw with a selection and a hover target
    game.handle_event(mouse(pygame.MOUSEBUTTONUP, (nn.x, nn.y)))
    check(len(world.pending) == 1 and sn.garrison < before, "releasing over a neutral node sends an order (garrison drops)")
    check(play.input.selection == [], "the selection is cleared after sending")
    frames(game, 60)
    check(world.ships.count() > 0, "ships fly after the next beat")

    # --- selection rules
    game.handle_event(mouse(pygame.MOUSEBUTTONDOWN, (nn.x, nn.y)))
    check(play.input.selection == [], "you cannot select a node you do not own")
    game.handle_event(mouse(pygame.MOUSEBUTTONDOWN, (sn.x, sn.y)))
    game.handle_event(mouse(pygame.MOUSEBUTTONUP, (5, 5)))
    check(play.input.selection == [] and not play.input.dragging, "release over empty space cancels")
    game.handle_event(mouse(pygame.MOUSEBUTTONDOWN, (sn.x, sn.y)))
    game.handle_event(mouse(pygame.MOUSEBUTTONUP, (sn.x, sn.y)))
    check(play.input.selection == [start] and play.input.sticky, "a plain click keeps the node selected")
    game.handle_event(mouse(pygame.MOUSEBUTTONDOWN, (5, 5), button=3))
    check(play.input.selection == [], "right-click cancels")
    game.handle_event(key(pygame.K_SPACE))
    check(play.input.selection == world.owned(PLAYER), "Space selects all your nodes")
    game.handle_event(mouse(pygame.MOUSEBUTTONDOWN, (nn.x, nn.y)))
    check(play.input.selection == [], "...and the next click on a node is the target")

    # --- send fraction: keys and wheel
    game.handle_event(key(pygame.K_4))
    check(SEND_FRACTIONS[game.settings["send_fraction"]] == 1.0, "key 4 = send 100%")
    game.handle_event(key(pygame.K_1))
    check(SEND_FRACTIONS[game.settings["send_fraction"]] == 0.25, "key 1 = send 25%")
    game.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=1))
    check(SEND_FRACTIONS[game.settings["send_fraction"]] == 0.5, "wheel up = next fraction")
    game.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-5))
    game.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-5))
    check(game.settings["send_fraction"] == 0, "the fraction stops at the lowest value")

    # --- pause, hints, node_at, stall
    t0 = world.ticks
    game.handle_event(key(pygame.K_p))
    frames(game, 30)
    check(play.paused and world.ticks == t0, "P pauses: the world does not tick")
    game.handle_event(key(pygame.K_p))
    frames(game, 10)
    check(not play.paused and world.ticks > t0, "P again resumes")
    hints = game.settings["hints"]
    game.handle_event(key(pygame.K_h))
    check(game.settings["hints"] != hints, "H toggles the hints")
    check(node_at(world.nodes, (sn.x + sn.radius + 10, sn.y)) == start, "clicking 10 px outside a node still hits it")
    check(node_at(world.nodes, (5, 5)) is None, "node_at finds nothing in an empty corner")
    t1 = world.ticks
    game.update(5.0)
    check(world.ticks - t1 <= 8, "after a long stall at most 8 ticks run in one frame")

    # --- the Esc menu in a match
    t2 = world.ticks
    game.handle_event(key(pygame.K_ESCAPE))
    check(isinstance(game.overlay, PauseScreen) and play.paused, "Esc opens the menu and pauses")
    frames(game, 20)
    check(world.ticks == t2, "the world stands still behind the menu")
    pm = game.overlay.menu
    pm.sel = [it.key for it in pm.items].index("music_track")
    game.handle_event(key(pygame.K_RIGHT))
    check(game.settings["music_track"] == 1, "MUSIC TRACK changes in the menu")
    game.handle_event(key(pygame.K_ESCAPE))
    check(game.overlay is None and not play.paused, "Esc closes the menu and resumes")
    game.handle_event(key(pygame.K_ESCAPE))
    pm = game.overlay.menu
    pm.sel = [it.key for it in pm.items].index("restart")
    seed = game.seed
    game.handle_event(key(pygame.K_RETURN))
    frames(game, 18)
    check(game.overlay is None and game.seed == seed and game.play.world is not world and not game.play.paused,
          "RESTART MATCH replays the same map, unpaused")
    world = game.play.world
    game.handle_event(key(pygame.K_ESCAPE))
    pm = game.overlay.menu
    pm.sel = [it.key for it in pm.items].index("title")
    game.handle_event(key(pygame.K_RETURN))
    frames(game, 18)
    check(game.current is game.title and game.overlay is None, "QUIT TO TITLE goes back to the title")
    start_match(game, 11)
    world = game.play.world

    # --- 600 frames of a running match, then screenshot
    frames(game, 600)
    check(game.running, "600 frames update + draw without a crash")
    check(world.stats.launched[2] > 0, "the computer opponent sends ships during the match")
    game.handle_event(key(pygame.K_F12))
    check(len(os.listdir(shots)) == 1, "F12 saves a screenshot")

    # --- game over: the overlay opens after a moment, R replays, Esc goes to the title
    world.over, world.result, world.winner = True, "win", PLAYER
    frames(game, 40)
    check(game.overlay is None, "the final moment stays visible for a little while")
    frames(game, 70)
    check(isinstance(game.overlay, GameOverScreen), "then the game-over screen opens")
    world.stats.snapshot(world.ticks, world.ship_totals())
    frames(game, 3)
    game.handle_event(key(pygame.K_r))
    frames(game, 18)
    check(game.seed == 11 and game.play.world is not world and not game.play.world.over, "R on the game-over screen replays the same map")
    world = game.play.world
    world.over, world.result, world.winner = True, "lose", 2
    frames(game, 120)
    check(isinstance(game.overlay, GameOverScreen), "DEFEATED screen opens too")
    game.handle_event(key(pygame.K_RETURN))
    frames(game, 18)
    check(game.seed != 11 or game.play.world is not world, "Enter starts a new map")
    world = game.play.world
    world.over, world.result, world.winner = True, "win", PLAYER
    frames(game, 120)
    game.handle_event(key(pygame.K_ESCAPE))
    frames(game, 18)
    check(game.current is game.title, "Esc on the game-over screen goes to the title")
    game.handle_event(key(pygame.K_F11))
    game.handle_event(key(pygame.K_F11))
    check(game.running, "F11 twice does not break anything")

    # --- watch mode (no human player): renders, ignores commands, game-over shows the winner
    start_match(game, 3, has_player=False)
    frames(game, 130)
    game.handle_event(mouse(pygame.MOUSEBUTTONDOWN, (100, 100)))
    check(game.play.world.has_player is False and game.running, "watch mode runs and ignores commands")
    game.play.world.over, game.play.world.winner = True, 2
    frames(game, 120)
    check(isinstance(game.overlay, GameOverScreen), "watch mode ends with a game-over screen")
    game.handle_event(key(pygame.K_ESCAPE))
    frames(game, 18)

    # --- the title's attract battles continue the beat count exactly (so the music is never thrown out of step)
    game.enter_title()
    frames(game, 20)
    before = game.title.world
    before_ticks = before.ticks
    game.title.new_attract()
    check(game.title.world is not before and game.title.world.ticks == before_ticks,
          "a new attract battle starts exactly where the last one stopped")

    # --- Quit actions
    menu = game.title.menu
    menu.sel = [it.key for it in menu.items].index("quit")
    game.handle_event(key(pygame.K_RETURN))
    check(not game.running, "QUIT in the title menu stops the game")

    audio_section(screen)


def audio_section(screen):
    """With real (dummy-device) audio: music starts on a beat, M switches tracks, pause, resync, all event sounds."""
    from audio.player import Audio
    import audio.conductor as conductor_module
    # The test frames run much faster than real time, so give the conductor a fake wall clock that moves 1/60 s per frame.
    fake = types.SimpleNamespace(now=1000.0)
    fake.monotonic = lambda: fake.now
    real_time = conductor_module.time
    conductor_module.time = fake

    def timed_frames(game, n):
        for _ in range(n):
            fake.now += DT_FRAME
            game.update(DT_FRAME)
            game.draw()

    audio = Audio(enabled=True)
    g3 = Game(screen, audio=audio, settings_path=None, shots_dir=None)
    audio.join()                                            # let the first track finish building
    timed_frames(g3, 40)
    check(audio.playing_track == 0 and audio.music_playing(), "the title plays the selected track from a beat")
    g3.start_match(11)
    timed_frames(g3, 12)
    check(g3.music.world is g3.play.world, "starting a match makes the music follow the new world")
    timed_frames(g3, 40)
    check(audio.playing_track == 0 and audio.music_playing(), "music (re)starts from beat 0 on the match's first beat")
    check(g3.track_name() == "DRIFT", "the HUD knows the track name")
    g3.handle_event(key(pygame.K_m))
    audio.join()
    check(g3.music.pending == 1 and "NEON" in g3.toast_text(), "M schedules the next track and shows a toast")
    timed_frames(g3, 35)                                    # more than one beat
    check(audio.playing_track == 1 and g3.music.pending is None, "the new track starts on the next beat")
    # a node "lost" in watch / attract mode (nobody is the player) must not duck the music or play the lost sound
    from types import SimpleNamespace
    audio._duck = None
    g3.music._play_capture(SimpleNamespace(ticks=0, has_player=False), 1, 2)
    check(audio._duck is None, "no music ducking when a computer loses a node in watch mode")
    g3.music._play_capture(SimpleNamespace(ticks=0, has_player=True), 1, 2)
    check(audio._duck is not None, "the player losing a node ducks the music")
    audio._duck = None

    # dynamic intensity: the conductor turns "how busy is the match" into 0..1 for the music's energy layer
    import numpy as np
    from audio.conductor import INTENSITY_QUIET, INTENSITY_FULL, CLASH_WEIGHT

    def intensity(ships, clashes=0.0, live=True, over=False):
        busy_world = SimpleNamespace(live=live, over=over, ships=SimpleNamespace(alive=np.ones(ships, dtype=bool)))
        g3.music.recent_clash = clashes
        g3.music._update_intensity(busy_world)
        return audio.energy_target

    check(intensity(INTENSITY_QUIET) == 0.0, "a quiet match (few ships in the air) leaves the energy layer silent")
    half = intensity((INTENSITY_QUIET + INTENSITY_FULL) // 2)
    check(0.4 < half < 0.6, f"half way between quiet and a big battle = about half intensity ({half:.2f})")
    check(intensity(INTENSITY_FULL * 6) == 1.0, "a big battle = full intensity (capped at 1)")
    check(intensity(0, clashes=10) == (CLASH_WEIGHT * 10 - INTENSITY_QUIET) / (INTENSITY_FULL - INTENSITY_QUIET) and g3.music.recent_clash == 5,
          "recent clashes count, and are half forgotten each beat")
    check(intensity(INTENSITY_FULL, live=False) == 0.0, "during the 3-2-1 countdown the music stays calm")
    check(intensity(INTENSITY_FULL, over=True) == 0.0, "after the match is decided the energy layer fades out")
    g3.handle_event(key(pygame.K_p))
    check(g3.play.paused, "P pauses (the mixer is paused too)")
    ref = g3.music.ref
    fake.now += 0.05                                        # 50 ms pass while paused
    g3.handle_event(key(pygame.K_p))
    check(g3.music.ref[0] > ref[0], "after a pause the music's start time moves by the paused time")
    g3.music.ref = (fake.now - 5.0, g3.music.ref[1])        # pretend the music has drifted by 5 seconds
    timed_frames(g3, 2)
    check(g3.music.pending == 1, "a drift of more than 0.12 s schedules a restart from the next beat")
    timed_frames(g3, 35)
    check(g3.music.pending is None and audio.music_playing(), "...and the restart happens on the next beat")
    g3.settings["music_track"] = 4                          # SHUFFLE never repeats the track that is playing
    check(all(g3.music.resolve_track() != g3.music.track for _ in range(30)), "SHUFFLE never picks the same track twice in a row")
    g3.settings["music_track"] = 1
    g3.set_setting("music_on", False)
    check(not audio.music_playing(), "turning the music off stops it")
    g3.set_setting("music_on", True)
    timed_frames(g3, 35)
    check(audio.music_playing(), "turning it on again rejoins on the next beat")
    # a whole AI battle with sound: voices, whooshes, zaps, capture bells, elimination and win jingles
    g3.start_match(5, has_player=False)
    timed_frames(g3, 2500)
    world = g3.play.world
    check(g3.running and (world.over or world.ticks > 2000), "2500 frames of an AI battle with all sounds, no crash")
    check(g3.music.ref is None or abs((fake.now - g3.music.ref[0]) - (world.ticks - g3.music.ref[1]) / 60) < 0.2,
          "at the end the music clock and the world clock agree")
    g3.enter_title()
    timed_frames(g3, 600)
    check(g3.running and audio.music_playing(), "back on the title the music plays on (attract battles continue the beat)")
    conductor_module.time = real_time
    pygame.mixer.quit()


if __name__ == "__main__":
    run()
    raise SystemExit(0 if helpers.report("test_game") else 1)

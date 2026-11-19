"""The playable simulator's back end (experimental/simui/game.py, ADR 0024) agrees with the simulator: the same play
driven through the page's order path gives the same ending and key moments as sim.simulate(); a run of clicks replays
to the same run; a stage jump hands over at its flag; the page's state serialises."""
import importlib.util
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location('simui_game', os.path.join(ROOT, 'experimental', 'simui', 'game.py'))
game = importlib.util.module_from_spec(_spec)      # loaded by file: no sys.path edit here (G4 ratchet)
sys.modules['simui_game'] = game
_spec.loader.exec_module(game)
import sim  # noqa: E402  (game puts experimental/cnv on the path)

A4 = os.path.join(ROOT, 'experimental', 'cnv', 'plays', 'a4.txt')


def lines(path):
    out = []
    for raw in open(path, encoding='utf-8'):
        line = raw.split('#')[0].strip()
        if line:
            out.append(line)
    return out


def drive(session, script_lines, until=sim.UNTIL):
    """Plays the lines through Session.command as the page would send them: a flag-anchored line at the start, a timed
    one at the tick before it is due."""
    timed = []
    for line in script_lines:
        e = sim.parse_script(line)[0]
        if isinstance(e[0], tuple):
            assert session.command({'verb': 'line', 'text': line}) == (True, '')
        else:
            timed.append((e[0], line))
    timed.sort(key=lambda x: x[0])
    s = session.s
    while s.ending is None and s.t <= until:
        while timed and timed[0][0] < s.t + sim.DT - 1e-9:
            assert session.command({'verb': 'line', 'text': timed.pop(0)[1]}) == (True, '')
        session.tick()
    return session


@pytest.fixture(scope='module')
def a4_ui():
    return drive(game.Session('a4'), lines(A4))


def test_a4_play_through_the_page_matches_simulate(a4_ui):
    ref = sim.simulate('a4', '', A4)
    assert ref.ending is not None
    assert game.key_times(a4_ui.obs) == game.key_times(game.Observe(ref))
    assert a4_ui.s.ending == ref.ending
    assert {f: v for f, v in a4_ui.s.flags.items() if 'Phase' in f} == {f: v for f, v in ref.flags.items() if 'Phase' in f}


def test_the_replay_record_makes_the_same_run(a4_ui):
    again = game.replay('a4', list(a4_ui.rec.happened))
    assert game.key_times(game.Observe(again)) == game.key_times(a4_ui.obs)


def clicks_session():
    """A4 played by clicks: the scene skipped to the hand-back, then a move to a clicked point, an ice wall on a clicked
    point, an attack on a named enemy, at the ticks the page would put them."""
    se = game.Session('a4')
    s = se.s
    assert se.command({'verb': '派', 'units': [], 'to': [1500, 2500]})[0] is False      # locked in the opening scene

    def wait(secs):
        se.run_to(s.t + secs)
        while not s.input:                      # a scene came up meanwhile: the page waits for the hand-back too
            se.tick()
    wait(0)
    mine = [b.name for b in s.living() if b.owner == s.human and b.speed > 0]
    eng = next(b.name for b in s.living() if b.owner == s.human and b.template == 'CNV_IceEngineer')
    assert se.command({'verb': '走', 'units': mine[:5], 'to': [1500, 2500]}) == (True, '')
    assert se.command({'verb': '派', 'units': mine[5:], 'to': [1500, 2500]}) == (True, '')
    wait(20)
    assert se.command({'verb': '放', 'units': [eng], 'ability': 'freeze', 'to': [1600, 2450]}) == (True, '')
    wait(15)
    foe = min((b for b in s.living() if s.enemy(s.human, b.owner) and not b.scenery and b.speed > 0),
              key=lambda b: abs(b.x - 1500) + abs(b.y - 2500))
    assert se.command({'verb': '攻击', 'units': mine[:3], 'target': foe.name}) == (True, '')
    se.run_to(s.t + 30)
    return se


def snapshot(s):
    return sorted((b.name, round(b.x, 3), round(b.y, 3), round(b.hp, 3), b.alive) for b in s.bodies.values()), \
        [x for x in s.log if x[1] != '剧本']


def test_clicks_replay_to_the_same_run():
    se = clicks_session()
    s = se.s
    assert any(e[1] == '放' and e[4].startswith('@') for e in se.rec.happened)
    assert any(b.template == 'CNV_A4IceWall' or b.template == 'CNV_A4IceSeed' for b in s.bodies.values()
               if b.made_at > 0)                            # the clicked cast made its wall
    again = game.replay('a4', list(se.rec.happened), until=s.t - sim.DT)
    assert round(again.t, 3) == round(s.t, 3)
    assert snapshot(again) == snapshot(s)
    import build                                            # the plain simulator, no UI class at all, the same
    m, t, _ = build.resolve('a4', '')
    plain = sim.Sim(m, t, 'normal', '')
    plain.events = sorted(se.rec.happened, key=lambda e: e[0])
    plain.run(s.t - sim.DT)
    assert snapshot(plain) == snapshot(s)


@pytest.mark.xfail(strict=True, reason=(
    "plays/a4.txt no longer reaches stage 2: it was hill-climbed (2026-11-08) on a simulator whose infantry turned "
    "before walking. After 54a14eb0 (A231, bench airevit: infantry walk off at once), A256 recorded truck 1 at "
    "211.5 s and truck 2 at 217.0 s, both lost to CNV A4 HV2 V1 JapanAntiVehicleInfantry-1 -> Lose 1 at 226.4 s. "
    "Now truck 1 (213.4 s) and truck 2 (217.8 s) fall to CNV A4 HV3 V2 JapanAntiVehicleInfantry-1 -> Lose 1 at 230.47 s, "
    "with CNV_A4_Phase_2 still unset at handover. "
    "The engine change is benched; the play script wants re-climbing (work/re/scripts/a4climb.py), see A256 handoff"))
def test_a_stage_jump_hands_over_at_its_flag():
    se = game.Session('a4')
    assert se.stages[:2] == ['CNV_A4_Phase_1', 'CNV_A4_Phase_2']
    assert se.jump(1) == (True, '')
    while se.busy:
        se.work(budget=5.0)
    s = se.s
    assert s.flags.get('CNV_A4_Phase_2') == 1 and s.ending is None
    assert not s.events and not s.anchored                  # the play script's orders still to come are dropped
    assert se.rec.happened                                  # what it did on the way is in the record


def test_the_state_serialises():
    se = game.Session('a4')
    se.run_to(10)
    st = se.state()
    json.dumps(st)
    json.dumps(se.static())
    assert st['units'] and st['letterbox'] in (True, False) and 'unmodeled' in st
    me = [u for u in st['units'] if u['rel'] == 'me']
    assert me and all('x' in u and 'hp' in u for u in me)


# ---- the voice channel: one line heard at a time, queued in game time as the engine queues dialogue ----------------

def test_two_lines_at_one_moment_are_heard_one_after_another():
    se = game.Session('a4')
    s = se.s
    s.act('PLAY_SOUND_EFFECT', ['CNV_A4_001'], None)
    s.act('PLAY_SOUND_EFFECT', ['CNV_A4_002'], None)
    a, b = se.rec.voices[-2:]
    assert a.t == a.asked == b.asked
    assert b.t == pytest.approx(a.t + a.secs)                   # the second waits for the first to play out
    if game.find_voice('CNV_A4_001'):
        assert a.secs == pytest.approx(game.recording_seconds(game.find_voice('CNV_A4_001')))
    assert game.voice_waits(se.rec.voices[-2:]) == [(b.asked, b.t, 'CNV_A4_002', 'CNV_A4_001')]


def test_a4_voice_channel_never_holds_two_lines(a4_ui):
    v = a4_ui.rec.voices
    assert len(v) > 20
    for a, b in zip(v, v[1:]):
        assert b.t >= a.t + a.secs - 1e-6, (a.key, b.key)       # at any moment at most one line is heard


def test_a4_full_play_holds_no_line_back(a4_ui):
    """The level itself: the A4 full play's lines, at their recordings' real lengths, never wait for one another. A
    line held back here is heard late in the game as well (the engine queues dialogue): the level line's to fix."""
    assert game.voice_waits(a4_ui.rec.voices) == []


def test_the_page_gets_a_line_when_the_run_reaches_its_start():
    se = game.Session('a4')
    se.run_to(1.0)
    run = se.state()['run']
    assert se.state()['voices'] == []
    s = se.s
    s.act('PLAY_SOUND_EFFECT', ['CNV_A4_001'], None)
    s.act('PLAY_SOUND_EFFECT', ['CNV_A4_002'], None)
    first = se.state()['voices']
    assert [x['key'] for x in first] == ['CNV_A4_001']          # the second is not handed over before its start
    se.run_to(se.rec.voices[-1].t + 0.1)
    assert 'CNV_A4_002' in [x['key'] for x in se.state(first[-1]['i'] + 1)['voices']]
    se.restart()
    assert se.state()['run'] == run + 1                         # the page drops what it is playing


# ---- the map's orientation: north up, as the map pictures (maprender) and the game's minimap ----------------------

def test_the_page_draws_north_up_by_the_map_pictures_own_definition():
    import maprender
    se = game.Session('a4')
    st = se.static()
    assert st['screen_y'] == maprender.SCREEN_Y == -1           # world y grows north, the screen's y down
    assert maprender.north_up(0, 100, 1000) == (0, 900)        # the picture's own projection uses it
    sites = {x['name']: x for x in st['sites']}
    north, south = sites['north refinery'], sites['south refinery']
    assert north['y'] > south['y']                              # so on screen the north camp is above the south
    page = open(os.path.join(ROOT, 'experimental', 'simui', 'index.html'), encoding='utf-8').read()
    assert 'SY = ST.screen_y' in page                           # the page takes it from there, no copy of its own
    assert 'SY * (y - view.cy)' in page and 'SY * (y - cv.height / 2)' in page    # both ways (W2S, S2W)

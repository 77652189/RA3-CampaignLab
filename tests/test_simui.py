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
    return s


@pytest.fixture(scope='module')
def a4_ui():
    return drive(game.Session('a4'), lines(A4))


def test_a4_play_through_the_page_matches_simulate(a4_ui):
    ref = sim.simulate('a4', '', A4)
    assert ref.ending is not None
    assert game.key_times(a4_ui) == game.key_times(ref)
    assert a4_ui.ending == ref.ending
    assert {f: v for f, v in a4_ui.flags.items() if 'Phase' in f} == {f: v for f, v in ref.flags.items() if 'Phase' in f}


def test_the_replay_record_makes_the_same_run(a4_ui):
    again = game.replay('a4', list(a4_ui.happened))
    assert game.key_times(again) == game.key_times(a4_ui)


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
    assert any(e[1] == '放' and e[4].startswith('@') for e in s.happened)
    assert any(b.template == 'CNV_A4IceWall' or b.template == 'CNV_A4IceSeed' for b in s.bodies.values()
               if b.made_at > 0)                            # the clicked cast made its wall
    again = game.replay('a4', list(s.happened), until=s.t - sim.DT)
    assert round(again.t, 3) == round(s.t, 3)
    assert snapshot(again) == snapshot(s)
    import build                                            # the plain simulator, no UI class at all, the same
    m, t, _ = build.resolve('a4', '')
    plain = sim.Sim(m, t, 'normal', '')
    plain.events = sorted(s.happened, key=lambda e: e[0])
    plain.run(s.t - sim.DT)
    assert snapshot(plain) == snapshot(s)


def test_a_stage_jump_hands_over_at_its_flag():
    se = game.Session('a4')
    assert se.stages[:2] == ['CNV_A4_Phase_1', 'CNV_A4_Phase_2']
    assert se.jump(1) == (True, '')
    while se.busy:
        se.work(budget=5.0)
    s = se.s
    assert s.flags.get('CNV_A4_Phase_2') == 1 and s.ending is None
    assert not s.events and not s.anchored                  # the play script's orders still to come are dropped
    assert s.happened                                       # what it did on the way is in the record


def test_the_state_serialises():
    se = game.Session('a4')
    se.run_to(10)
    st = se.state()
    json.dumps(st)
    json.dumps(se.static())
    assert st['units'] and st['letterbox'] in (True, False) and 'unmodeled' in st
    me = [u for u in st['units'] if u['rel'] == 'me']
    assert me and all('x' in u and 'hp' in u for u in me)

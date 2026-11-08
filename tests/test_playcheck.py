"""The comparison games (experimental/cnv/playcheck.py, ADR 0023): a level's player script compiled into mission script
actions so the simulator and the bench play the same thing. Here: it compiles for every play, the simulator reads on it
what the check's table says (so the bench's expectations cannot drift from the simulator), and the compiled play ends
the way the simulator's own script does (the translation is not the difference). The bench's side is
`cnv_check <level> play`; its readings are in docs/story/sim-vs-bench-plays.md."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('playcheck', ROOT / 'experimental' / 'cnv' / 'playcheck.py')
playcheck = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(playcheck)       # it puts the cnv folders on the path itself (guard G4's ceiling)

PLAYS = sorted(p.stem for p in (ROOT / 'experimental' / 'cnv' / 'plays').glob('*.txt'))


@pytest.mark.parametrize('level', PLAYS)
def test_every_play_compiles_into_script_actions(level):
    import build
    m, _, _ = build.resolve(level, '')
    t = playcheck.build(m, level)
    assert any(s.name.startswith('Test - play ') for s in t.scripts)
    assert [label for _, label in t.counters][0] == '玩家局阶段' and len(t.counters) <= 4


@pytest.mark.parametrize('level', sorted(playcheck.EXPECT))
def test_the_table_is_what_the_simulator_reads(level):
    result, end, phases = playcheck.EXPECT[level]
    t, s = playcheck.read(level)
    got_result, got_end, got_phases = playcheck.readings(t, s)
    assert got_result == result, s.ending_line()
    lo, hi = playcheck.window(end)      # ADR 0023: 15 % off the bench-agreed reading is a stop-and-find-out
    assert lo <= got_end <= hi, f'{level}: the simulator now ends at {got_end:.1f}, agreed {end} (window {lo:.0f}-{hi:.0f})'
    seen = {k: sec for k, sec in got_phases}
    for k, sec in phases:
        lo, hi = playcheck.window(sec)
        assert lo <= seen.get(k, -99) <= hi, f'{level}: phase {k} at {seen.get(k)}, agreed {sec} (window {lo:.0f}-{hi:.0f})'


@pytest.mark.parametrize('level', ['j7', 'a3'])
def test_compiled_play_ends_as_the_simulators_own_script_does(level):
    t, s = playcheck.read(level)
    tn, sn = playcheck.read(level, native=True)
    assert playcheck.readings(t, s)[:2] == playcheck.readings(tn, sn)[:2]


def test_a_window_is_15_percent_and_never_narrower_than_the_slack():
    assert playcheck.window(100.0) == (85.0, 115.0)
    lo, hi = playcheck.window(10.0)
    assert (lo, hi) == (6.0, 14.0)


def test_an_attack_line_compiles_to_an_attack_order_on_the_target():
    import build
    m, _, _ = build.resolve('j7', '')
    c = playcheck.Compiler(m, playcheck.Test())
    acts = c.actions((5.0, '攻击', 'tengu', 'launch tower'), 5.0)
    goal = c.who('launch tower', 5.0)[0]
    assert acts and acts == [('NAMED_ATTACK_NAMED', n, goal) for n in c.who('tengu', 5.0)]


def test_a_capture_line_is_the_engineers_capture_order_on_both_sides():
    # `占领 <who> 进 <building>`: the player's capture order -- the bench's script action, the simulator's order_capture
    import build
    import sim
    m, t, _ = build.resolve('a7', '')
    c = playcheck.Compiler(m, playcheck.Test())
    acts = c.actions((5.0, '占领', 'engineer', 'station'), 5.0)
    goal = c.who('station', 5.0)[0]
    assert acts and acts == [('NAMED_USE_COMMANDBUTTON_ABILITY_ON_NAMED', n, 'Command_CaptureBuilding', goal)
                             for n in c.who('engineer', 5.0)]
    assert sim.parse_script('5 占领 engineer 进 station; 6 占领 station') == [(5.0, '占领', 'engineer', 'station'),
                                                                     (6.0, '占领', 'station')]
    s = sim.Sim(m, t, 'normal', '')
    eng = s.pick('engineer')[0]
    s.happen((5.0, '占领', 'engineer', 'station'))
    assert eng.mode == 'capture' and eng.goal is s.pick('station')[0]


def test_a_line_the_bench_cannot_be_told_stops_the_compile():
    import build
    m, _, _ = build.resolve('j7', '')
    c = playcheck.Compiler(m, playcheck.Test())
    with pytest.raises(ValueError):
        c.actions((5.0, '打', 'tengu 1'), 5.0)

"""The auto player (experimental/autoplay, ADR 0026 item 4): what it sees, that every run is a script that plays back
the same game, that the card player with a steady hand reproduces the plan's own play, that a seed is a run, and the
batch's statistics."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
# loaded by file (guard G4: no new sys.path edits); autoplay.py loads the simulator, the players and the briefs itself
_spec = importlib.util.spec_from_file_location('autoplay', ROOT / 'experimental' / 'autoplay' / 'autoplay.py')
autoplay = importlib.util.module_from_spec(_spec)
sys.modules['autoplay'] = autoplay
_spec.loader.exec_module(autoplay)
sim, players = autoplay.sim, autoplay.players
_bspec = importlib.util.spec_from_file_location('autoplay_batch', ROOT / 'experimental' / 'autoplay' / 'batch.py')
batch = importlib.util.module_from_spec(_bspec)
_bspec.loader.exec_module(batch)

STEADY = players.Style(shift=0.0, slip=0.0, off=0.0)       # a card player with no slip at all


@pytest.fixture(scope='module')
def a3_rush():
    return autoplay.play('a3', 'rush', 1)


def test_the_view_holds_only_what_the_player_sees():
    import build
    m, t, _ = build.resolve('a4', '')
    s = sim.Sim(m, t, 'normal', '')
    s.advance(15 * 100)
    view = autoplay.View(s, autoplay.levels.brief('a4'))
    hidden = [b for b in s.living() if b.owner != s.human and not b.scenery and s.enemy(s.human, b.owner)
              and autoplay.attackable(b) and not s.side_sees(s.human, b)]
    assert hidden, 'A4 at 1:40 has enemies the player has not found: the check would pass vacuously'
    assert all(s.side_sees(s.human, f.body) for f in view.foes)
    assert not {f.name for f in view.foes} & {b.name for b in hidden}
    assert not any(not autoplay.attackable(f.body) for f in view.foes)      # a marker (zone, smoke) is not a target


def test_a_run_is_a_script_that_plays_back_the_same_game(a3_rush):
    run, _ = a3_rush
    assert run.outcome in ('win', 'lose') and run.lines
    for line in run.lines:
        sim.parse_script(line)                                  # every order is a line the simulator reads
    assert autoplay.replay('a3', run.lines) == (run.outcome, pytest.approx(run.t, abs=1e-6))


def test_a_card_player_with_a_steady_hand_plays_the_plan_itself():
    run, _ = autoplay.play('a3', 'card', 1, style=STEADY)
    plan = sim.simulate('a3', script=autoplay.levels.brief('a3').plan)       # the same lines through the simulator
    assert (run.outcome, run.t) == ('win', plan.ending[1])
    assert len(run.lines) == 16


def test_the_card_player_on_a4_wins_with_a_steady_hand():
    run, _ = autoplay.play('a4', 'card', 1, style=STEADY)
    # plays/a4.txt: 14:48 (handoff-phase4); 888.x -> 889.0 at A round 174's benched ore-point heading (1a745b63)
    assert run.outcome == 'win' and 889 <= run.t < 890


def test_a_seed_is_a_run():
    a = autoplay.play('a3', 'card', 3)[0]
    b = autoplay.play('a3', 'card', 3)[0]
    c = autoplay.play('a3', 'card', 4)[0]
    assert a.lines == b.lines and (a.outcome, a.t) == (b.outcome, b.t)
    assert a.lines != c.lines


def test_idle_does_not_win_a3():
    run, _ = autoplay.play('a3', 'idle', 1)
    assert run.outcome == 'lose' and not run.lines


def test_a_unit_no_line_can_name_is_skipped_not_misaddressed():
    import build
    m, t, _ = build.resolve('a3', '')
    s = sim.Sim(m, t, 'normal', '')
    view = autoplay.View(s, autoplay.levels.brief('a3'))
    out = autoplay.Orders(s, view)
    odd = s.add('#9 odd', 'AlliedAntiInfantryInfantry', s.human, 100, 100)
    out.go([odd], (200, 200))
    assert not out.lines and out.skipped == 1
    peace = s.bodies[m.cast['peace 1'].name]
    assert view.address(peace) == 'peace 1'


def test_the_batch_statistics():
    lo, hi = batch.wilson(0, 10)
    assert lo == 0.0 and 0.2 < hi < 0.35
    lo, hi = batch.wilson(10, 10)
    assert hi == 1.0 and 0.65 < lo < 0.8
    runs = [{'outcome': 'win', 't': 600.0, 'lost': 2, 'escort_lost': 0, 'ending': '', 'seed': 1},
            {'outcome': 'win', 't': 100.0, 'lost': 0, 'escort_lost': 0, 'ending': '', 'seed': 2},
            {'outcome': 'lose', 't': 200.0, 'lost': 5, 'escort_lost': 1, 'ending': 'Lose 1', 'seed': 3}]
    s = batch.summarize(runs)
    assert s['wins'] == 2 and s['in_band'] == 1 and s['lost_by'] == {'Lose 1': 1} and s['fastest_win'] == (100.0, 2)
    assert s['time_win']['median'] == 350.0

"""engine_aipullback airevk2 / airevk2o (D round 133): ReverseMove's effect on the bench.

airevk1's start (two Hammers join the attack team f213, state 2 f242 with aim = a far player Guardian 166+ off),
then at 16.7 s the check deletes the two Guardians and spawns one of the player's Guardians on each Hammer: every
member's only foe a few tens off, far inside the reverse gate 0 < d < R - 10 (cannon AttackRange 150: R - 10 = 135;
work/re/d131_triggers.md section 1). The host's samples (fixtures: selected frames, pointers redacted):

  airevk2 (ReverseMove on)  f272 both aim spawned foe 3262; f302 3171 gets the stop + a move to a point 135 from its
          target, along target -> member, and leaves the target; it drives there with its hull still on the target
          (hull -84 .. -127, displacement dotted with hull forward < 0): it backs up. 23 such move orders in the run.
  airevk2o (off)            the same frames, no such move order in the whole run; the members keep their targets.

Counters (坦克数, 近敌, 敌坦): on  s1-12 4 4 2 | s13 4 4 1 | s14 4 3 1 | s15-30 4 3 4 | s31-48 4 4 4 | s49-85 4 3 4
                              off s1-12 4 4 2 | s13 4 4 1 | s14-15 4 3 1 | s16-85 4 3 4
D round 134: the simulator's ReverseMove (ra3model tactics._reverse) now gets each member's own attack target
(simai ordered_aim) and reach AttackRange - 5: it backs up on airevk2 after the swap, never on airevk2o (asserted
below). The counter replay stays a strict xfail for another reason (team recruitment, see its reason).
Evidence: work/re/d133_airevk2.md.
"""
import importlib.util
import math
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    'teamlog', Path(__file__).resolve().parent.parent / 'experimental' / 'cnv' / 'teamlog.py')
teamlog = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(teamlog)

OBSERVED = Path(__file__).resolve().parent / 'fixtures' / 'e_reverse'
R10 = 135.0                                     # AttackRange 150 - 5 - 10


def _rows(build):
    return {r['frame']: r for r in teamlog.states(OBSERVED / (build + '.txt'))['T']}


def _pos(build, frame):
    team, = teamlog.at(OBSERVED / (build + '.txt'), frame)
    return {i: (x, y) for i, x, y in team['ids']}


def _moves(build):
    """The move orders (type 236) in the fixture: [(frame, (x, y))]."""
    out = []
    for line in (OBSERVED / (build + '.txt')).read_text(encoding='utf-8').splitlines():
        if line.startswith('cmd:') and ' type=236 ' in line:
            f = int(line.split('frame=')[1].split()[0])
            x, y, _ = line.split('args=7:')[1].split(':')
            out.append((f, (float(x), float(y))))
    return out


@pytest.mark.parametrize('build', ['airevk2', 'airevk2o'])
def test_both_builds_reach_the_reverse_gate(build):
    """State 2, both members aiming at a spawned foe well inside R - 10 before the first micro pass that could back."""
    rows = _rows(build)
    assert rows[242]['mstate'] == 2
    pos = _pos(build, 300)
    aim = rows[300]['aim']
    for m in (3170, 3171):
        tid, at = aim[m]
        assert tid not in (0, 3175, 3176) and at is not None      # a spawned foe, not the deleted far ones
        assert 0 < math.dist(pos[m], at) < R10, (m, pos[m], at)


def test_on_the_member_backs_up_to_r_minus_10():
    rows = _rows('airevk2')
    (f, dest), *_ = _moves('airevk2')
    assert f == 302
    tid, target = rows[300]['aim'][3171]
    assert rows[302]['aim'][3171][0] == 0                         # left its target
    assert rows[302]['dest'][3171] == pytest.approx(dest, abs=0.1)
    assert math.dist(dest, target) == pytest.approx(R10, abs=1.0)
    # away from the target along target -> member
    p = _pos('airevk2', 300)[3171]
    away = (p[0] - target[0], p[1] - target[1])
    step = (dest[0] - p[0], dest[1] - p[1])
    assert away[0] * step[0] + away[1] * step[1] > 0
    # driven in reverse: displacement against the hull's forward
    for a, b in ((302, 313), (316, 329)):
        pa, pb = _pos('airevk2', a)[3171], _pos('airevk2', b)[3171]
        h = math.radians(rows[a]['hd'][3171])
        dx, dy = pb[0] - pa[0], pb[1] - pa[1]
        assert math.hypot(dx, dy) > 10
        assert dx * math.cos(h) + dy * math.sin(h) < 0, (a, b, rows[a]['hd'][3171], dx, dy)


def test_off_no_back_up_order():
    assert _moves('airevk2o') == []
    rows = _rows('airevk2o')
    assert all(rows[f]['dest'].get(m, (0.0, 0.0)) == (0.0, 0.0) for f in rows if f >= 298 for m in (3170, 3171))


LATE_FRAME = round(16.7 * 15)                   # checks/engine_aipullback LATE_AT


def _model_reverses(build):
    """The simulator's back-up orders in `build` (D round 134): [(game frame, member, point)]."""
    from test_simai_bench_b import simai
    w = simai.run(build, 'a', 40.0, lib=simai.model()['xmldata'].Library(), record=True)
    b, = w.brains.values()
    return [(o['frame'] + b.started, o['member'], o['point']) for o in b.rec['orders'] if o['kind'] == 'reverse']


def test_model_backs_up_after_the_swap_only_with_the_switch_on():
    """The bench's host effect on the simulator (Fighter.aim = the member's own attack target, reach = AttackRange
    - 5): on, members aiming a spawned foe inside R - 10 get back-up orders after the swap (bench first f302); off,
    none in the whole run."""
    on = _model_reverses('airevk2')
    assert any(f > LATE_FRAME for f, _, _ in on), on
    assert _model_reverses('airevk2o') == []


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason='近敌 counts all four Hammers, so it rests on who joins the team: bench 2 of 4 join at '
                          'f213 after the near foe died s13 (the other 2 stay out and never back up); the simulator '
                          'recruits all 4 and they back off the near foes from s14 on (近敌 s31-47 on 1, off 4; '
                          'bench on 4, off 3). Not ReverseMove: work/re/d132_whenidle.md, d134 in handoff-d')
def test_model_replays_the_k2_counters():
    from test_simai_bench_b import _probe_run, simai
    lib = simai.model()['xmldata'].Library()
    got = {}
    for build in ('airevk2', 'airevk2o'):
        _, rows = _probe_run(build, lib, 50.0)
        got[build] = [tuple(r.values()) for r in rows]
    assert got['airevk2'][30:47] == [(4, 4, 4)] * 17
    assert got['airevk2o'][30:47] == [(4, 3, 4)] * 17

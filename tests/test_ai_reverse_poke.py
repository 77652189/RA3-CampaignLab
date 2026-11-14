"""engine_aipullback airevkp1 / airevkp0 (D round 135b, "注入摆"): d133's ReverseMove result again, from a placed start.

PREMISE: THE START IS PLACED (前提是摆出来的). airevk1 as it is (no script deletes or spawns anything), plus the map's
CNVCmd host carrying out the build's plan: at logic frame 250 each of the player's two Guardians is moved 50 west of
one of the attack team's two members (where those stood f242-248 in the 11-13 airevk1 run). Foe 1 is already dead by
then (as in airevk1, s13): its poke logs 'not found'. Foe 2 lands beside member 3171, ~119 from member 3170 -- both
inside the reverse gate 0 < d < R - 10 = 135 (work/re/d131_triggers.md section 1).

Bench 11-14 (fixtures: the poke lines and the AI player's select / back-up orders; pointers and program places
replaced by tokens, P4 = the back-up order's place, named ReverseMove in the private table):
  airevkp1 (on)  f272 both members get a back-up move (message 0x236) to a point 135 from the foe; 19 in the run
  airevkp0 (off) the same poke, no back-up order in the whole run
  counters (坦克数, 近敌, 敌坦): on  s1-12 4 4 2 | s13 4 4 1 | s14-17 4 3 1 | s18-85 4 2 1
                                 off s1-12 4 4 2 | s13 4 4 1 | s14-85 4 3 1
The same conclusion as airevk2 / airevk2o (tests/test_ai_reverse_k2.py), there reached by a script swap.
"""
import importlib.util
import math
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    'inject', Path(__file__).resolve().parent.parent / 'experimental' / 'cnv' / 'inject.py')
inject = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inject)

OBSERVED = Path(__file__).resolve().parent / 'fixtures' / 'e_reverse'
NAMES = {'P4': 'ReverseMove'}
FOE2 = (3553.0, 3304.0)
R_MINUS_10 = 135.0


def _look(build, kinds):
    return inject.look(str(OBSERVED / f'{build}.txt'), kinds=kinds)


@pytest.mark.parametrize('build', ['airevkp1', 'airevkp0'])
def test_the_plan_ran_at_frame_250(build):
    pokes = _look(build, ('poke',))
    assert [(e.frame, e.unit) for e in pokes] == [(250, '-1'), (250, '3176')]
    assert pokes[1].what.endswith('-> 3553.0,3304.0')


def test_on_both_members_back_up_to_r_minus_10_from_the_placed_foe():
    backs = [e for e in _look('airevkp1', ('command',)) if e.source == 'P4']
    assert len(backs) == 19 and all('倒车' in e.what for e in backs)
    first = [e for e in backs if e.frame == 272]
    assert sorted(e.unit for e in first) == ['3170', '3171']
    for e in first:
        x, y = (float(v) for v in e.what.rsplit('(', 1)[1].rstrip(')').split(','))
        assert math.hypot(x - FOE2[0], y - FOE2[1]) == pytest.approx(R_MINUS_10, abs=1.0)
    assert inject.source_name(backs[0], NAMES).startswith('ReverseMove')


def test_off_no_back_up_order():
    assert not [e for e in _look('airevkp0', ('command',)) if '倒车' in e.what]

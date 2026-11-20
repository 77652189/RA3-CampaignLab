"""A270: SKIRMISH_AI_START and PLAYER_TOGGLE_SKIRMISH_AI, benched by name (checks/engine_aistart.py).

B's aiskirm map, s1 AlliedBalanced, 50000 at the 10 s wake script (bench 11-16, all NOEXPECT):
  aistart   no library, SKIRMISH_AI_START alone: 50000 / 1 structure through f1154 -- the yard left on teamSoviet_1
  ainowake  no library, MAKE_BASE + money only: 50000 / 1 through f746
  aixfer    no library, SKIRMISH_AI_TRANSFER_ALL (team step, no wake): 50000 / 1 through f1104
  aistartx  no library, UNIT_AI_TRANSFER(yard) + SKIRMISH_AI_START (retail a07's way): paying at f169, 2 at f312
  aipause   library, toggled off at 25 s and on at 85 s: paying to 48300 at f457 (what was under way), flat to f1262,
            the third structure (done while paused) placed at f1280, paying again from f1300
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('aistart_simai_run', ROOT / 'experimental/cnv/simai_run.py')
simai_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai_run)
simai = simai_run.simai    # one copy of simai, the run's (R3 13f-2d)

pytestmark = pytest.mark.skipif(not simai.available(), reason='ra3model.ai not on this computer')


def _read(build, key, frames):
    w = simai_run.run(build, 'a', until=0.)
    got = {}
    for f in frames:
        w.advance(f - w.sim.frame_now())
        got[f] = [w.sim.counters.get(f'CNV_{key}_{k}', 0) for k in ('Money', 'Built')]
    return got


@pytest.mark.parametrize('build', ['aistart', 'ainowake', 'aixfer'])
def test_an_ai_neither_woken_nor_handed_its_yard_never_opens(build):
    """aistart / ainowake / aixfer: 50000 and one structure all run -- START without the yard handed, MAKE_BASE, and
    the team step without a wake each leave the AI idle."""
    got = _read(build, 'AIStart', (400, 900))
    assert got[400] == got[900] == [50000, 1], got


def test_skirmish_ai_start_opens_an_ai_whose_yard_was_handed():
    """aistartx: paying by f169, the second structure between f290 and f312 (as aiskirm's own wake)."""
    got = _read('aistartx', 'AIStart', (175, 330))
    assert 0 < got[175][0] < 50000 and got[175][1] == 1, got
    assert got[330][1] == 2, got


def test_toggle_skirmish_ai_off_freezes_the_ai_and_on_resumes_it():
    """aipause: flat money and two structures from f500 to f1262; the third placed at f1280 just after the 85 s
    resume, and paying again by f1350."""
    got = _read('aipause', 'AIPause', (500, 1260, 1300, 1350))
    assert got[500] == got[1260] and got[500][1] == 2, got
    assert got[1300][1] == 3, got
    assert got[1350][0] < got[1260][0], got

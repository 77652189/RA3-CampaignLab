"""simai HOOKS 9: the read-only trail (SimAI(record=True) -> Brain.rec). Turning it on changes nothing: the world, the
AI's own logs and orders are bit-for-bit the same as with it off, second by second; and the trail has what the other
lines read (members' positions / targets, state and prev_state, orders, deaths, the state tests' terms)."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental' / 'cnv' / 'simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)

pytestmark = pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')

# garrison (EnterBaseDefenses), Crush, EngageHostileTargets off: the four C questions' benches
RUNS = [('aibd1', 'a', 40), ('aicrush1', '', 40), ('aimicengoff', 'r', 40)]


def _world(w):
    s = w.sim
    bodies = tuple((n, b.x, b.y, b.hp, b.alive, getattr(b.goal, 'name', b.goal)) for n, b in sorted(s.bodies.items()))
    brains = tuple((repr(p), tuple(b.trace), tuple(b.fired), tuple(b.ids.items()),
                    tuple(getattr(getattr(b, 'tactics', None), 'log', ())),
                    tuple((r.phase, r.state, r.was, r.target) for r in getattr(b, 'tactics', None).runs.values())
                    if getattr(b, 'tactics', None) else ())
                   for p, b in sorted(w.brains.items(), key=lambda kv: repr(kv[0])))
    return bodies, tuple(sorted(s.money.items(), key=repr)), tuple(w.garrison.log), brains


def _steps(build, check, secs, record, lib):
    import build as bld
    m, t, _ = bld.resolve(build, check)
    w = simai.SimAI(simai.sim.Sim(m, t, 'normal'), lib=lib, record=record)
    out = []
    for _ in range(secs):
        w.advance(simai.FPS)
        out.append(_world(w))
    return w, out


@pytest.fixture(scope='module')
def lib():
    return simai.model()['xmldata'].Library()


@pytest.mark.parametrize('build,check,secs', RUNS)
def test_the_trail_changes_nothing_and_records(build, check, secs, lib):
    _, off = _steps(build, check, secs, False, lib)
    w, on = _steps(build, check, secs, True, lib)
    for k, (a, b) in enumerate(zip(off, on)):
        assert a == b, f'{build}: differs at s{k + 1}'
    (b,) = w.brains.values()
    rows = b.rec['frames']
    assert rows and b.rec['orders'], build
    r = next(r for r in rows if r['updated'])
    assert {'state', 'prev_state', 'foe', 'target', 'members', 'cond'} <= set(r)
    assert {'alpha', 'retreat', 'engage', 'garrisons'} <= set(r['cond'])
    assert {'name', 'pos', 'aim', 'alive', 'goal'} <= set(r['members'][0])
    off_rec = _steps(build, check, 1, False, lib)[0]
    assert not any(x.rec['frames'] or x.rec['orders'] for x in off_rec.brains.values())

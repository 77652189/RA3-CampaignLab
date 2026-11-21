"""Isolated Crush host dispatch; not the full engine_aicrush casualty replay."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai_run', ROOT / 'experimental/cnv/simai_run.py')
_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_run)
simai = _run.simai
import sim  # noqa: E402  (on the path once simai is loaded; simai names no Sim, R3 13f-2d)
pytestmark = pytest.mark.skipif(not simai.available(), reason='requires private engine model')


class Member(SimpleNamespace):
    """A team member: the model keys its keep tables by the member itself (by identity, as the simulator's bodies)."""
    __hash__ = object.__hash__
    __eq__ = object.__eq__


@pytest.mark.parametrize('name,expected', [('aicrush1', 'move'), ('aicrush0', 'attack'),
                                          ('aicrushlo', 'attack')])
def test_crush_host_dispatch(name, expected):
    """Real probe data and Brain.attach, isolated before combat can obscure the order.

    engine_aicrush's on/off/low readings motivate the dispatch distinction;
    this test asserts orders, not the old bench's timing or casualty totals.
    """
    import build
    from missions import aicrush_bench, airetreat_bench

    m, t, _ = build.resolve(name, 'a')
    w = simai.SimAI(sim.Sim(m, t, 'normal'))
    while not w.brains and w.frame < (m.facts['wake at'] + 5) * simai.FPS:
        w.advance(1)
    brain, = w.brains.values()
    tank = next(b for b in w.sim.living() if b.template == aicrush_bench.TANK)
    guard = next(b for b in w.sim.living() if 'INFANTRY' in b.kinds and b.owner != tank.owner)
    f, foe = brain.fighters([tank, guard])
    # At 100 units the measured speeds and weapon damage distinguish preference 1 / .01.
    f.pos = (foe.pos[0] - 100, foe.pos[1])
    travel = round(100 / f.speed * simai.FPS) / simai.FPS
    kill = foe.hp / f.dps(foe)
    assert .01 * kill < travel < kill
    unit = Member(body=tank)
    run = SimpleNamespace(team=SimpleNamespace(template=SimpleNamespace(micro=airetreat_bench.MICRO_ID),
                                              tactic='isolated'),
                          keep={}, keep_target={})     # the per-member keep record (D round 139)
    orders = []
    original = brain.tactics.order

    def record(u, kind, arg):
        orders.append((kind, arg))
        original(u, kind, arg)

    brain.tactics.order = record
    brain.tactics._attack_one(brain.ai, run, unit, f, foe, w.frame)
    assert orders == [(expected, foe.pos if expected == 'move' else foe.id)]
    assert tank.mode == ('move' if expected == 'move' else 'attack')
    assert (tank.goal is guard) is (expected == 'attack')
    assert any(what == 'crush' for _, what, _ in brain.tactics.log) is (expected == 'move')

    # Eligibility cannot send a unit toward a dead, allied, equal-level or airborne body.
    callback = brain.tactics.crush
    assert callback(brain.ai, f, foe)
    for obj, attr, value in [(guard, 'alive', False), (tank, 'alive', False),
                             (guard, 'owner', tank.owner),
                             (guard, 'surface', 'air'), (tank, 'surface', 'air')]:
        old = getattr(obj, attr)
        put = (lambda o, a, v: sim.locomotor.write(w.sim.world, o, surface=v)) if attr == 'surface' else setattr
        put(obj, attr, value)
        assert not callback(brain.ai, f, foe), (attr, value)
        put(obj, attr, old)
    # The levels are the CrusherInfo module's (step M3): the guard's swapped for one at the tank's own level.
    from engine.kernel import interfaces
    from engine.modules import crush
    kept = guard.modules
    guard.modules = tuple(m for m in kept if not isinstance(m, interfaces.Crush)) + (
        crush.Crush(guard, crush.CrushData(guard.crusher, tank.crusher).seal(), w.sim.world),)
    assert guard.crushable == tank.crusher and not callback(brain.ai, f, foe)
    guard.modules = kept

"""Full PullbackInjuredHealthPct replay; no injected facility or orders."""
from test_simai_bench_b import lib, _probe_run, pytestmark  # noqa: F401
from test_simai_bench_b import simai
from types import SimpleNamespace
import pytest


@pytest.fixture(scope='module')
def returns(lib):
    return {b: _probe_run(b, lib, 40.0) for b in ('aipullpctlo', 'aipullpcthi')}


def test_pullback_threshold_low_reaches_the_fight(returns):
    """checks/engine_aipullpct.py: 30% is above threshold 0.2 initially."""
    _, rows = returns['aipullpctlo']
    assert any(r['血量'] == 30 for r in rows[8:13])
    assert any(r['到远厂'] >= 3 for r in rows)
    # Bench reaches the plant s15-17, then one survivor returns at s34 after
    # further injury. This is an initial non-trigger control, never "no return".
    assert all(r['回家'] == 0 for r in rows[14:30])


def test_pullback_threshold_high_returns_before_recycling(returns):
    """checks/engine_aipullpct.py: threshold 0.5 sends the same 30% tanks home."""
    w, rows = returns['aipullpcthi']
    assert any(r['血量'] == 30 for r in rows[8:13])
    home = next((i for i, r in enumerate(rows[14:], 14) if r['回家'] >= 1), None)
    assert home is not None
    assert len(w.pullback.log) == 4
    assert all(b.tactics.pullback is not None for b in w.brains.values())
    assert all(w.pullback.busy(w.sim.bodies[name]) for _, name, _ in w.pullback.log)
    assert any(r['回家'] == 4 for r in rows[home:])
    assert all(r['到远厂'] == 0 for r in rows)
    assert all(r['坦克数'] == 4 for r in rows[14:home + 1])


@pytest.mark.xfail(strict=True, reason='Crane recycling is not implemented; this slice models injured return only. '
                   'Bench high0.5 has alive0 from s28. See work/re/handoff-c.md, next recycling slice.')
def test_pullback_threshold_high_is_recycled_after_return(returns):
    """checks/engine_aipullpct.py: high tanks disappear after reaching the Crane."""
    _, rows = returns['aipullpcthi']
    assert any(r['坦克数'] == 0 for r in rows[27:])


@pytest.fixture
def facility_world(lib):
    w = simai.run('aipullpcthi', 'a', 0, lib=lib)
    owner = w.sim.players['s1']
    tank = next(b for b in w.sim.living() if b.owner == owner and 'VEHICLE' in b.kinds)
    crane = next(b for b in w.sim.living() if b.template == 'SovietCrane')
    brain = SimpleNamespace(player=owner, tid=lambda b: b.name)
    return w, brain, tank, crane


def test_pullback_facilities_require_faction_filter_and_reachable_entry(facility_world, monkeypatch):
    w, brain, tank, crane = facility_world
    member = SimpleNamespace(body=tank)
    monkeypatch.setattr(w.sim.ground, 'within', lambda *args: [])
    tank.hp = .3 * tank.max_hp
    assert w.pullback.query(brain, member) == (.3, [(crane.name, (crane.x, crane.y), True)])
    tank.script_status.add('AIRBORNE_TARGET')
    assert w.pullback.query(brain, member) == (.3, [])
    tank.script_status.clear()
    monkeypatch.setattr(w.sim.ground, 'within', lambda *args: None)
    assert w.pullback.query(brain, member) == (.3, [])
    monkeypatch.setattr(w.sim.ground, 'within', lambda *args: [])
    crane.owner = next(p for p in w.sim.players.values() if w.sim.enemy(tank.owner, p))
    assert w.pullback.query(brain, member) == (.3, [])


def test_pullback_detachment_cancels_on_replacement_order_or_facility_loss(facility_world):
    w, _, tank, crane = facility_world
    assert w.pullback.send(tank, crane)
    assert w.pullback.busy(tank)
    tank.move_to = (0, 0)             # a new movement destination replaces the return order
    assert not w.pullback.busy(tank)
    assert w.pullback.send(tank, crane)
    w.sim.order_stop(tank)            # STOP keeps move_to, but replaces the active path
    assert not w.pullback.busy(tank)
    assert w.pullback.send(tank, crane)
    crane.alive = False
    assert not w.pullback.busy(tank)

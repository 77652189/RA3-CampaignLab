"""The pullback facility rules on a built aipullpcthi world (white box). The threshold replays are readings:
experimental/cnv/checks/engine_aipullpct.readings.toml."""
from test_simai_bench_b import lib, pytestmark  # noqa: F401
from test_simai_bench_b import simai_run
from types import SimpleNamespace
import pytest
import engine.orders.order as simorder  # noqa: E402


@pytest.fixture
def facility_world(lib):
    w = simai_run.run('aipullpcthi', 'a', 0, lib=lib)
    owner = w.sim.players['s1']
    tank = next(b for b in w.sim.living() if b.owner == owner and 'VEHICLE' in b.kinds)
    crane = next(b for b in w.sim.living() if b.template == 'SovietCrane')
    brain = SimpleNamespace(player=owner, tid=lambda b: b.name, settings=w.settings)
    return w, brain, tank, crane


def test_pullback_facilities_require_faction_filter_and_reachable_entry(facility_world, monkeypatch):
    w, brain, tank, crane = facility_world
    member = SimpleNamespace(body=tank)
    monkeypatch.setattr(w.sim.ground, 'within', lambda *args: [])
    tank.set_hp(.3 * tank.max_hp, tell=False)
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
    tank.aiupdate.move_to = (0, 0)             # a new movement destination replaces the return order
    assert not w.pullback.busy(tank)
    assert w.pullback.send(tank, crane)
    simorder.order_stop(tank)            # STOP keeps move_to, but replaces the active path
    assert not w.pullback.busy(tank)
    assert w.pullback.send(tank, crane)
    crane.alive = False
    assert not w.pullback.busy(tank)

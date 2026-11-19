"""Sickle collision-status exclusion: named native controls and replay."""
import importlib.util
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('nocoll_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_meta_nocoll_controls_change_only_observed_neighbour_status():
    import build
    from checks.engine_knock_relation import retail_shock
    from checks.engine_knock_probe import name

    for check in ('a', 'b'):
        m, t, _ = build.resolve('engine_knock_nocoll', check)
        for lane, uid in (('yuri', 'CNV_KnockYuri'), ('rocket', 'CNV_KnockRocket')):
            gun = next(u for u in m.units if u.id == uid)
            payload, = re.findall(r'<MetaImpactNugget\b.*?</MetaImpactNugget>', gun.xml, re.S)
            assert payload == retail_shock()
            victim, near = (next(o for o in m.objects if o.name == name(lane, part)) for part in ('man', 'near'))
            assert victim.side == near.side == 's1'
            assert (near.x - victim.x, near.y - victim.y) == (20, 0)
            bit = int((lane == 'yuri') != (check == 'b'))
            start = next(s for s in t.scripts if s.name == 'Test - start')
            assert ('UNIT_CHANGE_OBJECT_STATUS', near.name, 'NO_COLLISIONS', bit) in start.do
            assert (lane + ' status', 22, '==', bit, 24) in t.expect
        assert len(t.counters) == 4


@pytest.mark.parametrize('check,lane,frame,bit,delta,samples', [
    ('a', 'yuri', 173, 1, (-.00006, -.00024, -.00037),
     [(820,3750,212.5)] * 3),
    ('a', 'rocket', 174, 0, (0, -.00024, -.00079),
     [(2320,3746.7,213.40), (2320,3743.4,213.40), (2320,3740,212.5)]),
    ('b', 'yuri', 173, 0, (-.00006, -.00024, -.00037),
     [(820,3746.7,213.40), (820,3743.4,213.40), (820,3740,212.5)]),
    ('b', 'rocket', 174, 1, (0, -.00024, -.00079),
     [(2320,3750,212.5)] * 3),
])
def test_meta_nocoll_replays_native_status_dispatch_and_neighbour_path(
        check, lane, frame, bit, delta, samples, monkeypatch):
    """CampKNCA_mcp_1116_005401 / CampKNCB_mcp_1116_005616.

    Observed collision frame/centre are inputs; same-frame dispatch INFERRED.
    Scripted NO_COLLISIONS only, not its native creation/cleanup lifecycle.
    XML-filter versus a separate native status gate remains unisolated.
    """
    import build
    import sim
    import simunits
    from checks.engine_knock_probe import name

    m, t, _ = build.resolve('engine_knock_nocoll', check)
    e = sim.Sim(m, t)
    e.firing, e.volleys = [], []
    e.eng.frame = frame
    gun, victim, near = (e.bodies[name(lane, part)] for part in ('gun', 'man', 'near'))
    # The counter verifies this bit on the native host; replay it explicitly
    # at collision, rather than treating a script request as an observation.
    if bit:
        near.status.add('NO_COLLISIONS')
    else:
        near.status.discard('NO_COLLISIONS')
    centre = (victim.x - delta[0], victim.y - delta[1], 219 - delta[2])
    original = simunits.meta_impact_velocity
    called = set()
    positions = {(victim.x, victim.y): 'man', (near.x, near.y): 'near'}

    def observe(effect, position, centre, height, **kwargs):
        called.add(positions[position[:2]])
        return original(effect, position, centre, height, **kwargs)

    monkeypatch.setattr(simunits, 'meta_impact_velocity', observe)
    weapon, = gun.weapons
    e.queue_projectile_hit(frame, victim, weapon['dmg'], gun, weapon, centre)
    e.deal(1/15)
    assert called == ({'man'} if bit else {'man', 'near'})
    assert (near.serial in e.impact_flights) == (not bit)
    assert victim.hp == pytest.approx(148.5)
    assert near.hp == 150
    for tick, xyz in enumerate(samples, frame + 1):
        e.eng.frame = tick
        e.meta_impact_tick()
        assert (near.x, near.y, e.impact_ground_z(near.x, near.y) if near.z is None else near.z
                ) == pytest.approx(xyz, abs=.051)
    assert near.serial not in e.impact_flights

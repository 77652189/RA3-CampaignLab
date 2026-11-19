"""Sickle XML exclusion versus separately observed NO_COLLISIONS rejection."""
import importlib.util
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('statusgate_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_meta_statusgate_controls_remove_only_xml_status_exclusion():
    import build
    from checks.engine_knock_relation import retail_shock
    from checks.engine_knock_probe import name

    for check in ('a', 'b'):
        m, t, _ = build.resolve('engine_knock_statusgate', check)
        for lane, uid in (('yuri', 'CNV_KnockYuri'), ('rocket', 'CNV_KnockRocket')):
            gun = next(u for u in m.units if u.id == uid)
            payload, = re.findall(r'<MetaImpactNugget\b.*?</MetaImpactNugget>', gun.xml, re.S)
            assert payload == (retail_shock() if check == 'a' else
                               retail_shock().replace('StatusBitFlagsExclude="NO_COLLISIONS"', ''))
            victim, near = (next(o for o in m.objects if o.name == name(lane, p)) for p in ('man', 'near'))
            assert victim.side == near.side == 's1'
            assert near.template == victim.template
            assert (near.x - victim.x, near.y - victim.y) == (20, 0)
            bit = int(lane == 'yuri')
            start = next(s for s in t.scripts if s.name == 'Test - start')
            assert ('UNIT_CHANGE_OBJECT_STATUS', near.name, 'NO_COLLISIONS', bit) in start.do
            assert (lane + ' status', 22, '==', bit, 24) in t.expect
        assert len(t.counters) == 4


@pytest.mark.parametrize('check,lane,frame,delta', [
    ('a', 'yuri', 173, (-.00006, -.00024, -.00037)),
    ('a', 'rocket', 174, (0, -.00024, -.00079)),
    ('b', 'yuri', 173, (-.00006, -.00024, -.00037)),
    ('b', 'rocket', 174, (0, -.00024, -.00079)),
])
def test_meta_statusgate_replays_native_dispatch_and_path(check, lane, frame, delta, monkeypatch):
    """CampKSGA_mcp_1116_012814 / CampKSGB_mcp_1116_013047.

    Native evidence: work/re/c_statusgate_report.md.

    Collision frame/centre and scripted status are observed replay inputs;
    same-frame dispatch INFERRED. No native status lifecycle claim.
    """
    import build
    import sim
    import simunits
    from checks.engine_knock_probe import name

    m, t, _ = build.resolve('engine_knock_statusgate', check)
    e = sim.Sim(m, t)
    e.firing, e.volleys = [], []
    e.eng.frame = frame
    gun, victim, near = (e.bodies[name(lane, p)] for p in ('gun', 'man', 'near'))
    bit = int(lane == 'yuri')
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
    moves = check == 'b' or not bit
    assert called == ({'man', 'near'} if moves else {'man'})
    assert (near.serial in e.impact_flights) == moves
    assert int(100 * victim.hp / 150) == 99
    assert near.hp == 150
    x = 820 if lane == 'yuri' else 2320
    samples = ([(x,3750,212.5)] * 3 if not moves else
               [(x,3746.7,213.40), (x,3743.4,213.40), (x,3740,212.5)])
    for tick, xyz in enumerate(samples, frame + 1):
        e.eng.frame = tick
        e.meta_impact_tick()
        assert (near.x, near.y, e.impact_ground_z(near.x, near.y) if near.z is None else near.z
                ) == pytest.approx(xyz, abs=.051)
    assert near.serial not in e.impact_flights

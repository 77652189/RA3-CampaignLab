"""RushAttack forbidden object-status diagnostic."""
import importlib.util
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('objectgate_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_meta_objectgate_controls_isolate_forbidden_object_status():
    import build
    from model import status
    from checks.engine_knock_objectgate import BIT, payload
    from checks.engine_knock_probe import name

    for check in ('a', 'b'):
        m, t, _ = build.resolve('engine_knock_objectgate', check)
        for lane, uid in (('yuri', 'CNV_KnockYuri'), ('rocket', 'CNV_KnockRocket')):
            gun = next(u for u in m.units if u.id == uid)
            shock, = re.findall(r'<MetaImpactNugget\b.*?</MetaImpactNugget>', gun.xml, re.S)
            assert shock == (payload() if check == 'a' else
                             payload().replace(f'ForbiddenTargetObjectStatus="{BIT}"', ''))
            assert 'ShockWaveArc' not in shock and 'SpecialObjectFilter' not in shock
            assert 'ForbiddenTargetModelCondition' not in shock
            near = next(o for o in m.objects if o.name == name(lane, 'near'))
            start = next(s for s in t.scripts if s.name == 'Test - start')
            assert ('UNIT_CHANGE_OBJECT_STATUS', near.name, BIT, int(lane == 'yuri')) in start.do
            condition = next(s for s in t.scripts if s.name == 'Test - status ' + lane)
            assert condition.when == [('UNIT_HAS_OBJECT_STATUS', near.name, status(BIT))]
        assert len(t.counters) == 4


@pytest.mark.parametrize('check,lane,frame,delta', [
    ('a', 'yuri', 173, (-.00006, -.00024, -.00037)),
    ('a', 'rocket', 174, (0, -.00024, -.00079)),
    ('b', 'yuri', 173, (-.00006, -.00024, -.00037)),
    ('b', 'rocket', 174, (0, -.00024, -.00079)),
])
def test_meta_objectgate_replays_native_dispatch_and_path(check, lane, frame, delta, monkeypatch):
    """CampKOGA_mcp_1116_022622 / CampKOGB_mcp_1116_022838.

    Native evidence: work/re/c_objectgate_report.md.

    Observed collision/centre and scripted bit are replay inputs; same-frame
    dispatch INFERRED. No native leech lifecycle or full RushAttack claim.
    """
    import build
    import sim
    import engine.data.units as simunits
    from checks.engine_knock_objectgate import BIT
    from checks.engine_knock_probe import name

    m, t, _ = build.resolve('engine_knock_objectgate', check)
    e = sim.Sim(m, t)
    e.firing, e.volleys = [], []
    e.eng.frame = frame
    gun, victim, near = (e.bodies[name(lane, p)] for p in ('gun', 'man', 'near'))
    bit = int(lane == 'yuri')
    if bit:
        near.status.add(BIT)
    else:
        near.status.discard(BIT)
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
    samples = ([(x,3750,212.5)] * 7 if not moves else
               [(x+5.7,3748.6,214.27), (x+11.3,3747.2,215.45),
                (x+17,3745.7,216.04), (x+22.7,3744.3,216.04),
                (x+28.4,3742.9,215.45), (x+34.2,3741.5,214.27),
                (x+40,3740,212.5)])
    for tick, xyz in enumerate(samples, frame + 1):
        e.eng.frame = tick
        e.meta_impact_tick()
        assert (near.x, near.y, e.impact_ground_z(near.x, near.y) if near.z is None else near.z
                ) == pytest.approx(xyz, abs=.051)
    assert near.serial not in e.impact_flights


def test_meta_objectgate_retains_unmeasured_combinations_as_gaps():
    import engine.data.units as simunits
    from checks.engine_knock_objectgate import payload

    for shock in (payload().replace('LEECHED_TARGET_ACTIVE', 'NO_ATTACK'),
                  payload().replace('<MetaImpactNugget', '<MetaImpactNugget ShockWaveArc="180d"'),
                  payload().replace('<MetaImpactNugget', '<MetaImpactNugget ShockwaveDelaySeconds="1s"')):
        weapon = simunits._weapons(['<WeaponTemplate id="gap"><Nuggets>' + shock +
                                   '</Nuggets></WeaponTemplate>'])['gap']
        assert not weapon.get('meta_impacts')
        assert not weapon.get('delayed_meta_impacts')
        assert 'MetaImpactNugget' in weapon['unmodeled_effects']


@pytest.mark.parametrize('check', ['a', 'b'])
def test_meta_objectgate_named_counters_match_native(check):
    """Both runs s22..23: direct HP99/99, scripted neighbour status1/0."""
    import build
    import sim

    m, t, _ = build.resolve('engine_knock_objectgate', check)
    e = sim.Sim(m, t).run(24.)
    readings = [tuple(values) for sec, values in e.series if 22 <= sec <= 23]
    assert readings and all(row == (99, 99, 1, 0) for row in readings)

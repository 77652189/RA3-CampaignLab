"""Rush infantry selector and scripted object-status combination."""
import importlib.util
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('kindgate_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
from engine.combat.host import Peers, impact_ground_z  # noqa: E402


def test_meta_kindgate_controls():
    import build
    from checks import engine_knock_kindgate as kg
    from checks import engine_knock_probe as probe

    for check in ('a', 'b'):
        m, t, _ = build.resolve('engine_knock_kindgate', check)
        ordinary = next(u for u in m.units if u.id == probe.PROBE)
        other = next(u for u in m.units if u.id == kg.NONINF)
        assert re.search(r'KindOf="[^"]*\bINFANTRY\b', ordinary.xml)
        assert not re.search(r'KindOf="[^"]*\bINFANTRY\b', other.xml)
        normalized = other.xml.replace(kg.NONINF, probe.PROBE)
        assert normalized == re.sub(r'(\bKindOf=")([^"]*)(")',
            lambda x: x[1] + ' '.join(k for k in x[2].split() if k != 'INFANTRY') + x[3], ordinary.xml)
        for uid in ('CNV_KnockYuri', 'CNV_KnockRocket'):
            shock, = re.findall(r'<MetaImpactNugget\b.*?</MetaImpactNugget>',
                                next(u for u in m.units if u.id == uid).xml, re.S)
            assert shock == kg.payload(check == 'b')
            assert 'ForbiddenTargetObjectStatus="LEECHED_TARGET_ACTIVE"' in shock
        assert len(t.counters) == 4


def test_meta_kindgate_parses_only_measured_combo():
    import engine.data.units as simunits
    from checks.engine_knock_kindgate import payload

    def parse(xml):
        return simunits._weapons(['<WeaponTemplate id="combo"><Nuggets>' + xml +
                                 '</Nuggets></WeaponTemplate>'])['combo']

    effect, = parse(payload())['meta_impacts']
    assert effect['forbidden_status'] == ['LEECHED_TARGET_ACTIVE']
    assert effect['target_filter'] == {'rush_infantry': True}
    for xml in (payload().replace('LEECHED_TARGET_ACTIVE', 'NO_ATTACK'),
                payload().replace('Include="INFANTRY"', 'Include="VEHICLE"'),
                payload().replace('<MetaImpactNugget', '<MetaImpactNugget ShockwaveDelaySeconds="1s"'),
                payload().replace('<MetaImpactNugget', '<MetaImpactNugget InvertShockWave="false"')):
        assert not parse(xml).get('meta_impacts')


@pytest.mark.parametrize('check', ['a', 'b'])
def test_meta_kindgate_named_counters(check):
    """Native evidence and run ids: work/re/c_kindgate_report.md."""
    import build
    import sim

    m, t, _ = build.resolve('engine_knock_kindgate', check)
    e = sim.Sim(m, t).run(24.)
    readings = [tuple(values) for sec, values in e.series if 22 <= sec <= 23]
    assert readings and all(row == (99, 99, 11, 0) for row in readings)


@pytest.mark.parametrize('check,lane,delta', [
    ('a', 'yuri', (-.00006, -.00024, .00003)),
    ('a', 'rocket', (0, -.00024, -.00049)),
    ('b', 'yuri', (-.00006, -.00024, .00003)),
    ('b', 'rocket', (0, -.00024, -.00049)),
])
def test_meta_kindgate_native_dispatch_and_paths(check, lane, delta, monkeypatch):
    """Observed collision/centre input; same-frame dispatch INFERRED.

    Native run ids and raw evidence: work/re/c_kindgate_report.md.
    Synthetic noninf retains Physics; this does not cover retail vehicles.
    """
    _replay(check, lane, delta, monkeypatch)


@pytest.mark.xfail(strict=True, reason='Synthetic noninf uses vehicle landing grid in Sim; native retains infantry grid. '
                   'See work/re/c_kindgate_report.md; landing classifier remains a gap.')
def test_meta_kindgate_noninf_native_trajectory(monkeypatch):
    _replay('b', 'rocket', (0, -.00024, -.00049), monkeypatch, verify_noninf=True)


def _replay(check, lane, delta, monkeypatch, verify_noninf=False):
    import build
    import sim
    import engine.data.units as simunits
    from checks.engine_knock_objectgate import BIT
    from checks.engine_knock_probe import name

    m, t, _ = build.resolve('engine_knock_kindgate', check)
    e = sim.Sim(m, t)
    e.firing, e.volleys = [], []
    e.eng.frame = frame = 174
    gun, victim, near, other = (e.bodies[name(lane, p)] for p in ('gun', 'man', 'near', 'noninf'))
    for body in (near, other):
        (body.status.add if lane == 'yuri' else body.status.discard)(BIT)
    positions = {(b.x, b.y): part for b, part in ((victim, 'man'), (near, 'near'), (other, 'noninf'))}
    called = set()
    original = simunits.meta_impact_velocity

    def observe(effect, position, centre, height, **kwargs):
        called.add(positions[position[:2]])
        velocity = original(effect, position, centre, height, **kwargs)
        if positions[position[:2]] in ('near', 'noninf'):
            assert velocity == pytest.approx((5.9333, -.0001, -.0001), abs=.0001)
        return velocity

    monkeypatch.setattr(simunits, 'meta_impact_velocity', observe)
    centre = (victim.x - delta[0], victim.y - delta[1], 219 - delta[2])
    weapon, = gun.weapons
    e.queue_projectile_hit(frame, victim, weapon['dmg'], gun, weapon, centre)
    e.deal(1/15)
    expected = {'man'}
    if lane == 'rocket':
        expected.add('near')
        if check == 'b':
            expected.add('noninf')
    assert called == expected
    assert int(100 * victim.hp / 150) == 99
    assert near.hp == other.hp == 150
    x = 820 if lane == 'yuri' else 2320
    samples = ([(x, 3750, 212.5)] * 7 if lane == 'yuri' else
               [(x+5.7,3748.6,214.27), (x+11.3,3747.2,215.45),
                (x+17,3745.7,216.04), (x+22.7,3744.3,216.04),
                (x+28.4,3742.9,215.45), (x+34.2,3741.5,214.27),
                (x+40,3740,212.5)])
    for tick, xyz in enumerate(samples, frame + 1):
        e.eng.frame = tick
        e._harm().meta_impact_tick(e, Peers(e))
        z = lambda b: impact_ground_z(e, b.x, b.y) if b.z is None else b.z
        assert (near.x, near.y, z(near)) == pytest.approx(xyz, abs=.051)
        other_xyz = (xyz[0] + 20, xyz[1], xyz[2]) if check == 'b' and lane == 'rocket' else (x + 20, 3750, 212.5)
        if check != 'b' or lane != 'rocket' or verify_noninf:
            assert (other.x, other.y, z(other)) == pytest.approx(other_xyz, abs=.051)
    assert near.serial not in e.impact_flights
    if check != 'b' or lane != 'rocket' or verify_noninf:
        assert other.serial not in e.impact_flights

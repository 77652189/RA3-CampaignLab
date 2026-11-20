"""MagneticSingularity diagnostic: raw payload controls, then native replay."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('invert_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_meta_invert_probe_keeps_retail_filter_and_changes_only_inversion():
    import re
    import xml.etree.ElementTree as ET
    import build
    from checks.engine_knock_invert import retail_shock
    from checks.engine_knock_probe import PROBE_TANK, name

    m, t, _ = build.resolve('engine_knock_invert', 'a')
    original = ET.fromstring(retail_shock())
    for lane, uid in (('yuri', 'CNV_KnockYuri'), ('rocket', 'CNV_KnockRocket')):
        gun = next(u for u in m.units if u.id == uid)
        payload, = re.findall(r'<MetaImpactNugget\b.*?</MetaImpactNugget>', gun.xml, re.S)
        node = ET.fromstring(payload)
        expected = dict(original.attrib, InvertShockWave='true' if lane == 'yuri' else 'false')
        assert node.attrib == expected
        assert ET.tostring(node[0]) == ET.tostring(original[0])
        victim, near = (next(o for o in m.objects if o.name == name(lane, part)) for part in ('man', 'near'))
        assert victim.template == near.template == PROBE_TANK
        assert (near.x - victim.x, near.y - victim.y) == (80, 0)
        assert gun.names['rocket'] + '.xml' in gun.files
    assert t.expect == [(label, 12.0, '==', hp, 14.0)
                        for label, hp in [('yuri man', 99), ('yuri near', 100),
                                          ('rocket man', 99), ('rocket near', 100)]]


@pytest.mark.parametrize('lane,centre,velocity', [
    ('yuri', (789.53571, 3730.99951, 218.10666), (-.6028, -.1266, 0)),
    ('rocket', (2304.41748, 3730.99951, 218.03758), (1.7674, .4443, 0)),
])
def test_meta_invert_velocity_replays_native_neighbour(lane, centre, velocity):
    """CampKInvA_mcp_1116_001821: raw shockinfo; centre reconstructed from dir.

    Selected neighbours only, not proof of retail filter eligibility. Their
    half-height is six; inversion reverses the vector, not radial falloff.
    """
    import build
    import sim
    import engine.data.units as simunits
    from checks.engine_knock_probe import name

    m, t, _ = build.resolve('engine_knock_invert', 'b')
    e = sim.Sim(m, t)
    by, near = (e.bodies[name(lane, part)] for part in ('gun', 'near'))
    weapon, = by.weapons
    effect, = weapon['meta_impacts']
    height = simunits.meta_impact_body(near.template, e.own)
    assert height == 12
    assert simunits.meta_impact_velocity(effect, (near.x, near.y, 212.5), centre,
                                        height, detonation=True) == pytest.approx(velocity, abs=.00006)


def test_meta_invert_plain_probe_retains_unsupported_filter_and_vertical_variants():
    import re
    import build
    import engine.data.units as simunits
    from checks.engine_knock_invert import retail_shock

    m, _, _ = build.resolve('engine_knock_invert', 'b')
    gun = next(u for u in m.units if u.id == 'CNV_KnockYuri')
    payload, = re.findall(r'<MetaImpactNugget\b.*?</MetaImpactNugget>', gun.xml, re.S)
    assert 'SpecialObjectFilter' not in payload
    for unsupported in (retail_shock().replace('Rule="ALL"', 'Rule="ANY"'),
                        payload.replace('ShockWaveZMult="0.00"', 'ShockWaveZMult="1"'),
                        payload.replace('InvertShockWave="true"', 'InvertShockWave="unknown"'),
                        payload.replace('<MetaImpactNugget', '<MetaImpactNugget ShockwaveDelaySeconds="1s"')):
        weapon = simunits._weapons(['<WeaponTemplate id="gap"><Nuggets>' + unsupported +
                                   '</Nuggets></WeaponTemplate>'])['gap']
        assert not weapon.get('meta_impacts')
        assert not weapon.get('delayed_meta_impacts')
        assert 'MetaImpactNugget' in weapon['unmodeled_effects']


@pytest.mark.parametrize('lane,collision,centre,samples', [
    ('yuri', 173, (789.53571, 3730.99951, 218.10666),
     [(879.3,3750,212.62), (878.7,3750,212.73), (878,3750,212.81),
      (877.4,3750,212.88), (876.7,3750,212.93), (876,3750,212.97),
      (875.4,3750,212.99), (874.7,3750,212.99), (874,3750,212.97),
      (873.4,3750,212.93), (872.7,3750,212.88), (872,3750,212.81),
      (871.4,3750,212.73), (870.7,3750,212.62), (870,3750,212.5)]),
    ('rocket', 174, (2304.41748, 3730.99951, 218.03758),
     [(2382,3750,212.81), (2384,3750,212.97), (2386,3750,212.97),
      (2388,3750,212.81), (2390,3750,212.5)]),
])
def test_meta_invert_collision_replays_native_neighbour_frames(lane, collision, centre, samples):
    """CampKInvB_mcp_1116_002158: all neighbour samples through landing.

    Collision frames are observed shock frames (same-frame dispatch INFERRED),
    centre is supplied from shockinfo. No curved arrival or retail filter claim.
    """
    import build
    import sim
    from checks.engine_knock_probe import name

    m, t, _ = build.resolve('engine_knock_invert', 'b')
    e = sim.Sim(m, t)
    e.firing, e.volleys = [], []
    e.eng.frame = collision
    by, victim, near = (e.bodies[name(lane, part)] for part in ('gun', 'man', 'near'))
    weapon, = by.weapons
    e.queue_projectile_hit(collision, victim, weapon['dmg'], by, weapon, centre)
    e.deal(1/15)
    assert victim.hp == pytest.approx(548.5)
    assert near.hp == 550
    for frame, xyz in enumerate(samples, collision + 1):
        e.eng.frame = frame
        e.move(1/15)
        e.deal(1/15)
        assert (near.x, near.y, e.impact_ground_z(near.x, near.y) if near.z is None else near.z
                ) == pytest.approx(xyz, abs=.051)
    assert near.serial not in e.impact_flights


@pytest.mark.parametrize('lane,collision,centre,landing', [
    ('yuri', 173, (789.53571,3730.99951,218.10666), (870,3750)),
    ('rocket', 174, (2304.41748,3730.99951,218.03758), (2390,3750)),
])
def test_meta_invert_retail_filter_replays_native_landing(lane, collision, centre, landing):
    """Original filtered check a moved both neighbours; ground eligibility now replays."""
    import build
    import sim
    from checks.engine_knock_probe import name

    m, t, _ = build.resolve('engine_knock_invert', 'a')
    e = sim.Sim(m, t)
    e.firing, e.volleys = [], []
    e.eng.frame = collision
    by, victim, near = (e.bodies[name(lane, part)] for part in ('gun', 'man', 'near'))
    weapon, = by.weapons
    e.queue_projectile_hit(collision, victim, weapon['dmg'], by, weapon, centre)
    e.deal(1/15)
    for frame in range(collision + 1, 191):
        e.eng.frame = frame
        e.move(1/15)
        e.deal(1/15)
    assert (near.x, near.y) == pytest.approx(landing, abs=.051)

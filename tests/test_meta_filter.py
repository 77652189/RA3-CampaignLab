"""MagneticSingularity's real identity/status controls and measured replay."""
import importlib.util
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('filter_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
from engine.combat.host import Peers  # noqa: E402


def test_meta_filter_controls_keep_original_template_ids():
    import build
    from checks.engine_knock_filter import CANDIDATES
    from checks.engine_knock_invert import retail_shock
    from checks.engine_knock_probe import name

    for check in ('a', 'b'):
        m, t, _ = build.resolve('engine_knock_filter', check)
        for lane, uid in (('yuri', 'CNV_KnockYuri'), ('rocket', 'CNV_KnockRocket')):
            gun = next(u for u in m.units if u.id == uid)
            payload, = re.findall(r'<MetaImpactNugget\b.*?</MetaImpactNugget>', gun.xml, re.S)
            expected = retail_shock()
            if check == 'b':
                expected = re.sub(r'<SpecialObjectFilter\b.*?</SpecialObjectFilter>', '', expected, flags=re.S)
            assert payload == expected
            for part, (template, _, _) in CANDIDATES.items():
                obj = next(o for o in m.objects if o.name == name(lane, part))
                assert obj.template == template
                assert obj.site
                if template != 'CNV_KnockHammer':
                    unit = next(u for u in m.units if u.id == template)
                    assert f'id="{template}"' in unit.xml
                    assert unit.xml.count('ModuleTag_CNVProbe') == 1
        assert t.expect == [('yuri man', 22, '==', 99, 24), ('rocket man', 22, '==', 99, 24),
                            ('yuri status', 22, '==', 3, 24), ('rocket status', 22, '==', 3, 24)]


@pytest.mark.parametrize('check', ['a', 'b'])
@pytest.mark.parametrize('lane,frame,centre,velocities', [
    ('yuri', 173, (810.60938, 3730.99951, 218.18311),
     {'man': (3.1486, -5.6388, 0), 'normal': (-3.7567, 2.8401, 0),
      'drone': (.1581, -1.2516, 0), 'tesla': (1.7641, -.4433, 0)}),
    ('rocket', 174, (2301.78516, 3730.99951, 218.44537),
     {'man': (.6237, -6.6383, 0), 'normal': (-3.5144, 2.1144, 0),
      'drone': (.0279, -1.3137, 0), 'tesla': (2.4289, -.6910, 0)}),
])
def test_meta_filter_replays_native_ground_dispatch(check, lane, frame, centre, velocities, monkeypatch):
    """CampKFilterA_mcp_1116_003750 / CampKFilterB_mcp_1116_004009.

    Actual status-counter values were 3/3. Their input into this collision
    snapshot is explicit; script/native Iron Curtain lifecycle is not covered.
    Arrival frame/centre are native inputs, same-frame dispatch INFERRED.
    Aircraft exclusion remains unproved, so it is excluded from this assertion.
    """
    import build
    import sim
    import engine.data.units as simunits
    from checks.engine_knock_probe import name

    velocities = dict(velocities)
    if check == 'b':
        velocities.update({'near': (-2.2369, -.6125, 0), 'teslaic': (2.8938, 1.3530, 0),
                           'infantry': (.9822, 4.2585, 0)} if lane == 'yuri' else
                          {'near': (-1.5622, -.3795, 0), 'teslaic': (3.3600, 1.8672, 0),
                           'infantry': (.1731, 4.4616, 0)})
    m, t, _ = build.resolve('engine_knock_filter', check)
    e = sim.Sim(m, t)
    e.eng.frame = frame
    for part in ('near', 'teslaic'):
        e.bodies[name(lane, part)].status.add('UNDER_IRON_CURTAIN')
    # The spy records the actual dispatch consumer, before landing generation.
    original = simunits.meta_impact_velocity
    called = {}
    positions = {(b.x, b.y): b.name for b in e.bodies.values()}

    def observe(effect, position, centre, height, **kwargs):
        velocity = original(effect, position, centre, height, **kwargs)
        called[positions[position[:2]]] = velocity
        return velocity

    monkeypatch.setattr(simunits, 'meta_impact_velocity', observe)
    gun = e.bodies[name(lane, 'gun')]
    weapon, = gun.weapons
    e._harm().meta_impact_detonate(e, weapon, centre, gun, Peers(e))
    ground = ('man', 'normal', 'drone', 'tesla', 'near', 'teslaic', 'infantry')
    assert {part for part in ground if name(lane, part) in called} == set(velocities)
    assert {part for part in ground if e.bodies[name(lane, part)].serial in e.impact_flights} == set(velocities)
    for part, velocity in velocities.items():
        assert called[name(lane, part)] == pytest.approx(velocity, abs=.00006)
    for tick in range(frame + 1, 211):
        e.eng.frame = tick
        e._harm().meta_impact_tick(e, Peers(e))
    normal = e.bodies[name(lane, 'normal')]
    near = e.bodies[name(lane, 'near')]
    assert (normal.x, normal.y) == pytest.approx((810, 3730) if lane == 'yuri' else (2330, 3710), abs=.051)
    start_x = 880 if lane == 'yuri' else 2380
    assert (near.x, near.y) == pytest.approx((start_x - (10 if check == 'b' else 0), 3750), abs=.051)

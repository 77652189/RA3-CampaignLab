"""Sickle infantry inclusion: real infantry/vehicle controls and native replay."""
import importlib.util
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('kind_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_meta_kind_controls_preserve_real_kind_and_only_remove_inclusion():
    import build
    import labpaths
    from checks.engine_knock_relation import retail_shock
    from checks.engine_knock_probe import name, PROBE, PROBE_TANK

    for check in ('a', 'b'):
        m, t, _ = build.resolve('engine_knock_kind', check)
        for lane, uid, template in (('yuri', 'CNV_KnockYuri', PROBE),
                                    ('rocket', 'CNV_KnockRocket', PROBE_TANK)):
            gun = next(u for u in m.units if u.id == uid)
            payload, = re.findall(r'<MetaImpactNugget\b.*?</MetaImpactNugget>', gun.xml, re.S)
            assert payload == (retail_shock() if check == 'a' else
                               retail_shock().replace('Include="INFANTRY"', ''))
            victim, near = (next(o for o in m.objects if o.name == name(lane, p)) for p in ('man', 'near'))
            assert near.template == template
            assert near.side == victim.side == 's1'
            assert (near.x - victim.x, near.y - victim.y) == (40, 0)
            unit = next(u for u in m.units if u.id == template)
            source = Path(labpaths.SDK3) / 'SageXML' / ('Allied' if lane == 'yuri' else 'Soviet') / 'Units'
            source /= ('AlliedAntiInfantryInfantry' if lane == 'yuri' else 'SovietAntiVehicleVehicleTech1') + '.xml'
            kind = lambda xml: re.search(r'\bKindOf="([^"]*)"', xml).group(1).split()
            assert kind(unit.xml) == kind(source.read_text(encoding='utf-8'))
            assert ('INFANTRY' in kind(unit.xml)) == (lane == 'yuri')
        assert len(t.counters) == 4


@pytest.mark.parametrize('check,lane,frame,delta,moves', [
    ('a', 'yuri', 174, (-.00006, -.00024, .00009), True),
    ('a', 'rocket', 175, (0, -.00024, .00020), False),
])
def test_meta_kind_replays_native_dispatch_health_and_neighbour_path(
        check, lane, frame, delta, moves, monkeypatch):
    """CampKKindA_mcp_1116_010816: raw evidence in work/re/c_kind_evidence.

    Observed collision frame and direction residual are explicit inputs;
    same-frame dispatch INFERRED. No native status or landing-entry claim.
    """
    import build
    import sim
    import engine.data.units as simunits
    from checks.engine_knock_probe import name

    m, t, _ = build.resolve('engine_knock_kind', check)
    e = sim.Sim(m, t)
    e.firing, e.volleys = [], []
    e.eng.frame = frame
    gun, victim, near = (e.bodies[name(lane, part)] for part in ('gun', 'man', 'near'))
    centre = (victim.x - delta[0], victim.y - delta[1], 219 - delta[2])
    original = simunits.meta_impact_velocity
    called = {}
    positions = {(victim.x, victim.y): 'man', (near.x, near.y): 'near'}

    def observe(effect, position, centre, height, **kwargs):
        velocity = original(effect, position, centre, height, **kwargs)
        called[positions[position[:2]]] = velocity
        return velocity

    monkeypatch.setattr(simunits, 'meta_impact_velocity', observe)
    weapon, = gun.weapons
    e.queue_projectile_hit(frame, victim, weapon['dmg'], gun, weapon, centre)
    e.deal(1/15)
    assert set(called) == ({'man', 'near'} if moves else {'man'})
    assert (near.serial in e.impact_flights) == moves
    assert victim.hp == pytest.approx(148.5)
    assert near.hp == (150 if lane == 'yuri' else 550)
    # The displayed health counters measure 99 / 100, not absolute HP.
    assert int(100 * victim.hp / 150) == 99
    assert 100 * near.hp / (150 if lane == 'yuri' else 550) == 100
    if moves:
        assert called['near'] == pytest.approx((3.3333, 0, 0), abs=.00006)
    x = 840 if lane == 'yuri' else 2340
    samples = [(x,3746.7,213.40), (x,3743.4,213.40), (x,3740,212.50)] if moves else [(x,3750,212.5)] * 3
    for tick, xyz in enumerate(samples, frame + 1):
        e.eng.frame = tick
        e.meta_impact_tick()
        assert (near.x, near.y, e.impact_ground_z(near.x, near.y) if near.z is None else near.z
                ) == pytest.approx(xyz, abs=.051)
    assert near.serial not in e.impact_flights


@pytest.mark.parametrize('lane', ['yuri', 'rocket'])
def test_meta_kind_empty_any_replays_native_no_dispatch(lane, monkeypatch):
    """CampKKindB_mcp_1116_011040: no shock; all four probes stationary.

    Nominal centre is INFERRED because this run has no shockinfo. All subjects
    are inside Radius50 for this centre; exact collision centre remains gap.
    """
    import build
    import sim
    import engine.data.units as simunits
    from checks.engine_knock_probe import name

    m, t, _ = build.resolve('engine_knock_kind', 'b')
    e = sim.Sim(m, t)
    gun, victim, near = (e.bodies[name(lane, part)] for part in ('gun', 'man', 'near'))
    called = []
    original = simunits.meta_impact_velocity

    def observe(*args, **kwargs):
        called.append(args[1])
        return original(*args, **kwargs)

    monkeypatch.setattr(simunits, 'meta_impact_velocity', observe)
    weapon, = gun.weapons
    e.meta_impact_detonate(weapon, (victim.x, victim.y, 219), gun)
    assert called == []
    assert not e.impact_flights
    for frame in (180, 195, 210):
        e.eng.frame = frame
        e.meta_impact_tick()
        assert (victim.x, victim.y) == (800 if lane == 'yuri' else 2300, 3750)
        assert (near.x, near.y) == (840 if lane == 'yuri' else 2340, 3750)

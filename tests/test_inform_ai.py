"""Controls for the InformTarget black-box fixture; no claim of simulator coverage."""
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('inform_simbench', ROOT / 'experimental/cnv/simbench.py')
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_inform_ai_has_one_slow_projectile_and_instant_player_low_controls():
    import build
    from contract import RETAIL_COMMANDS
    from checks import engine_inform_ai as probe

    m, t, _ = build.resolve('engine_inform_ai', 'a')
    ns = {'a': 'uri:ea.com:eala:asset'}
    assert len(m.name + 'A') <= 15 and '_' not in m.name
    assert probe.COMMAND in RETAIL_COMMANDS
    assert [x[1] for x in t.counters] == [lane + ' info' for lane in probe.LANES]
    for lane, unit in zip(probe.LANES, m.units):
        root = ET.fromstring(unit.xml)
        weapons = root.findall('a:WeaponTemplate', ns)
        launch = next(w for w in weapons if w.get('id') == unit.names['weapon'])
        assert len(launch.findall('a:Nuggets/a:InformTargetNugget', ns)) == 1
        damage = root.find('.//a:DamageNugget', ns)
        assert damage.get('DamageType') == 'UNRESISTABLE'
        assert float(damage.get('Damage')) == (50 if lane == 'removed' else 150)
        projectiles = launch.findall('a:Nuggets/a:ProjectileNugget', ns)
        assert len(projectiles) == (0 if lane == 'order' else 1)
        assert float(launch.get('WeaponSpeed')) == (999999 if lane == 'order' else 75)
        for xml in unit.files.values():
            movement = ET.fromstring(xml).find('.//a:MoveInStraightLine', ns)
            assert float(movement.get('MuzzleVelocity')) == 5
        for weapon in weapons:
            if weapon is not launch:
                assert not weapon.findall('a:Nuggets/a:InformTargetNugget', ns)
    make = next(s for s in t.scripts if s.name == 'Test - make')
    creates = [a for a in make.do if a[0] == 'CREATE_NAMED_ON_TEAM_AT_WAYPOINT']
    assert [a[3] for a in creates] == [m.team('s1'), m.team('p1'), m.team('s1'), m.team('s1')]
    assert all(a[2] == 'SovietMiner' for a in creates)
    assert not any(a[0] == 'UNIT_CHANGE_OBJECT_STATUS' and a[2] == 'NO_ATTACK' for a in make.do)
    for lane in probe.LANES:
        hit = next(s for s in t.scripts if s.name == 'Test - hit ' + lane)
        assert ('UNIT_HEALTH', 'Info miner ' + lane, 0, 100) in hit.when


def test_inform_ai_response_is_reported_as_a_gap_including_retail_cache():
    import build
    import sim
    import simunits

    retail = simunits._fight_data()['weapons']['SovietAntiVehicleVehicleTech1CannonWeapon']
    assert 'InformTargetNugget' in retail['unmodeled_effects']
    weapons = simunits._weapons(['''<WeaponTemplate id="head"><Nuggets>
        <AttributeModifierNugget AttributeModifierName="unused" RequiredTargetObjectStatus="IMMOBILE"/>
        </Nuggets></WeaponTemplate><WeaponTemplate id="launch"><Nuggets>
        <ProjectileNugget ProjectileTemplate="shell" WarheadTemplate="head"/>
        <InformTargetNugget/></Nuggets></WeaponTemplate>'''])
    resolved = simunits._resolve(weapons['launch'], weapons)
    assert set(resolved['unmodeled_effects']) == {'InformTargetNugget', 'AttributeModifierNugget'}
    # The existing direct-damage fixture isolates gap propagation from this
    # new probe's script-created AI units and unsupported armor status read.
    m, t, _ = build.resolve('engine_inform', 'damage')
    engine = sim.Sim(m, t)
    engine.shot_clock = True
    rows = engine.run(16).series
    assert tuple(rows[-1][1]) == (79, 1, 79, 1)
    assert (sim.GAP_WEAPON, 'InformTargetNugget') in engine.unmodeled


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason='InformTarget advance notification and AI self-defense execution are not modeled')
def test_inform_ai_advance_response_matches_engine_inform_ai_observation():
    """Second bench: first damage87/87/1/87, first shield51/none/3/none.

    Frozen automatic readings, before manual controls; no scalar fitting of
    the unexplained ~2.4s advance window or projectile muzzle collision.
    """
    import build
    import sim

    m, t, _ = build.resolve('engine_inform_ai', 'a')
    engine = sim.Sim(m, t)
    engine.shot_clock = True
    rows = engine.run(36).series
    expected = (1187051068, 87135068, 101003068, 87135089)
    assert tuple(rows[-1][1]) == expected
    assert all(tuple(row) == expected for sec, row in rows if sec >= 31)

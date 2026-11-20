"""E158: Radar diagnostic isolation and named prerequisite readings.

These are not radar availability assertions; the HUD observation is separate.
"""
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('radar_bootstrap', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_radar_single_module_control_and_spellbook_isolation():
    import build
    from model import merged
    from contract import contract
    from package import spec_of
    on, t, _ = build.resolve('engine_radar', 'a')
    off, u, _ = build.resolve('engine_radaroff', 'a')
    assert re.sub(r'<RadarBehavior\b[^>]*/>', '', on.units[0].xml) == off.units[0].xml
    assert on.assets == off.assets
    assert '<RadarBehavior' not in on.assets[0][1]
    assert 'inheritFrom="PlayerSpellBook"' not in on.assets[0][1]
    assert on.replaces == ['GameObject:PlayerSpellBook']
    assert [o.template for o in on.objects] == ['CNVE158Radar', 'AlliedConstructionYard', 'AlliedPowerPlant']
    assert not contract(merged(on, t))
    assert not contract(merged(off, u))
    assert not any('RADAR' in str(s.do) or 'REVEAL' in str(s.do) for s in t.scripts)
    packed = spec_of(on, t)
    assert 'GameObject:PlayerSpellBook' in packed.replaces
    assert ('E158SpellBook.xml', on.assets[0][1]) in packed.unit_files


@pytest.mark.parametrize('name,before,after', [('engine_radar', 151, 303), ('engine_radaroff', 149, 308)])
def test_radar_named_prerequisite_readings(name, before, after):
    engine, world, m = replay(name)
    engine.run(frames=before)
    assert tuple(engine.value(c) for c in ('E158Dish', 'E158Support')) == (1, 1)
    engine.run(frames=after - before)
    assert tuple(engine.value(c) for c in ('E158Dish', 'E158Support')) == (0, 1)


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'E158 measured PLAYER_HAS_POWER=1; object-world condition returns 0. '
    'Power script integration is a gap, see work/re/e158_radar.md and work/re/handoff-e.md.'))
@pytest.mark.parametrize('name,frame', [('engine_radar', 151), ('engine_radaroff', 149)])
def test_radar_named_power_prerequisite(name, frame):
    engine, world, m = replay(name)
    engine.run(frames=frame)
    assert engine.value('E158Power') == 1


@pytest.mark.parametrize('name,before,after,visible', [
    ('engine_radar', 151, 303, True), ('engine_radaroff', 149, 308, False)])
def test_radar_named_hud_observations(name, before, after, visible):
    # CampRadarEA_mcp_1115_153726 / CampRadarOffEA_mcp_1115_153945,
    # 0008.png and 0018.png: minimap terrain versus the Allied emblem.
    engine, world, m = replay(name)
    from ra3model.objects import radar
    engine.run(frames=before)
    assert radar.available(world.logic, m.player('p1')) is visible
    engine.run(frames=after - before)
    assert radar.available(world.logic, m.player('p1')) is False


def test_radar_low_power_named_supply_and_lifetime():
    engine, world, m = replay('engine_radarlow')
    from ra3model.objects.rules import power_of
    world.logic.power = 'objects'
    engine.run(frames=147)
    assert power_of(world.logic, m.player('p1')) == (150, 75)
    assert tuple(engine.value(c) for c in ('E158Dish', 'E158Support')) == (1, 1)
    engine.run(frames=302 - 147)
    assert power_of(world.logic, m.player('p1')) == (50, 75)
    assert tuple(engine.value(c) for c in ('E158Dish', 'E158Support')) == (1, 1)


def test_radar_low_power_named_hud_observations():
    # CampRadarLowEA_mcp_1115_155053/0008.png and 0018.png:
    # minimap terrain at f147 and f302, independent power reading 1 -> 0.
    engine, world, m = replay('engine_radarlow')
    from ra3model.objects import radar
    world.logic.power = 'objects'
    engine.run(frames=147)
    assert radar.available(world.logic, m.player('p1')) is True
    engine.run(frames=302 - 147)
    assert radar.available(world.logic, m.player('p1')) is True


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'E159 measured PLAYER_HAS_POWER=1 at f147 then 0 at f302; '
    'object-world condition is unimplemented. See work/re/e159_radar_power.md '
    'and work/re/handoff-e.md.'))
def test_radar_low_power_named_script_prerequisite():
    engine, world, m = replay('engine_radarlow')
    world.logic.power = 'objects'
    engine.run(frames=147)
    assert engine.value('E158Power') == 1
    engine.run(frames=302 - 147)
    assert engine.value('E158Power') == 0


def test_radar_two_providers_isolated_timed_deletion():
    import build
    from contract import contract
    from model import merged
    m, t, _ = build.resolve('engine_radartwo', 'a')
    assert m.role('dish').template == m.role('second').template == 'CNVE158Radar'
    assert m.role('dish').name != m.role('second').name
    assert '<RadarBehavior' not in m.assets[0][1]
    assert not contract(merged(m, t))
    assert not any('RADAR' in str(s.do) or 'REVEAL' in str(s.do) for s in t.scripts)
    deletes = [s.do for s in t.scripts if any(a[0] == 'NAMED_DELETE' for a in s.do)]
    assert deletes == [[('NAMED_DELETE', m.role('dish').name)],
                       [('NAMED_DELETE', m.role('second').name)]]


def test_radar_two_providers_named_hud_and_lifetime():
    # CampRadarTwoEA_mcp_1115_162754/{0008,0018,0036}.png:
    # f114/f197 terrain, f386 Allied emblem. Wall-time expectations failed
    # during the slow run; the independent logic-frame readings are preserved.
    engine, world, m = replay('engine_radartwo')
    from ra3model.objects import radar
    from ra3model.objects.rules import power_of
    world.logic.power = 'objects'
    previous = 0
    for frame, alive, visible in [(114, (1, 1), True),
                                   (197, (0, 1), True),
                                   (386, (0, 0), False)]:
        engine.run(frames=frame - previous)
        previous = frame
        assert tuple(engine.value(c) for c in ('E158Dish', 'E160Second')) == alive
        assert power_of(world.logic, m.player('p1')) == (150, 0)
        assert radar.available(world.logic, m.player('p1')) is visible


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'E160 measured power AND yard/plant survival=1 at f114/f197/f386; '
    'PLAYER_HAS_POWER object-world condition is unimplemented. '
    'See work/re/e160_radar_multi.md and work/re/handoff-e.md.'))
def test_radar_two_providers_named_script_prerequisite():
    engine, world, m = replay('engine_radartwo')
    engine.run(frames=114)
    assert engine.value('E158Power') == 1


def test_radar_death_damage_entry_and_isolation():
    import build
    from contract import contract
    from model import merged
    m, t, _ = build.resolve('engine_radardeath', 'a')
    assert not contract(merged(m, t))
    assert '<RadarBehavior' not in m.assets[0][1]
    actions = [a for s in t.scripts for a in s.do]
    assert [a for a in actions if a[0] == 'NAMED_DAMAGE'] == [
        ('NAMED_DAMAGE', m.role('dish').name, 250),
        ('NAMED_DAMAGE', m.role('dish').name, 1000)]
    assert not any(a[0] in ('NAMED_DELETE', 'NAMED_KILL', 'UNIT_SET_HEALTH')
                   or 'RADAR' in a[0] or 'REVEAL' in a[0] for a in actions)


def test_radar_death_named_health_lifetime_and_hud():
    # CampRadarDeadEA_mcp_1115_170508: 0007/0008/0017 terrain;
    # 0018 at f182 is the off transition, 0019/0041 Allied emblem.
    engine, world, m = replay('engine_radardeath')
    from ra3model.objects import radar
    from ra3model.objects.rules import power_of
    world.logic.power = 'objects'
    previous = 0
    for frame, gone, hp, visible in [(87, 0, 100, True), (95, 0, 50, True),
                                     (173, 0, 50, True), (182, 1, 0, False),
                                     (192, 1, 0, False), (374, 1, 0, False)]:
        engine.run(frames=frame - previous)
        previous = frame
        assert (engine.value('E161Gone'), engine.value('E161HP')) == (gone, hp)
        assert power_of(world.logic, m.player('p1')) == (150, 0)
        assert all(world.named(m.role(r).name).alive for r in ('yard', 'power'))
        assert radar.available(world.logic, m.player('p1')) is visible


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'E161 measured power AND yard/plant survival=1 at f87/f95/f173/f182/f192/f374; '
    'PLAYER_HAS_POWER object-world condition is unimplemented. '
    'See work/re/e161_radar_death.md and work/re/handoff-e.md.'))
def test_radar_death_named_script_prerequisite():
    engine, world, m = replay('engine_radardeath')
    previous = 0
    for frame in (87, 95, 173, 182, 192, 374):
        engine.run(frames=frame - previous)
        previous = frame
        assert engine.value('E161Support') == 1


@pytest.mark.parametrize('name,before,after', [
    ('engine_radarout', 1, 2), ('engine_radarin', 2, 1)])
def test_radar_transfer_script_entry_and_isolation(name, before, after):
    import build
    from contract import contract
    from model import merged
    m, t, _ = build.resolve(name, 'a')
    assert not contract(merged(m, t))
    assert '<RadarBehavior' not in m.assets[0][1]
    assert m.role('dish').side == ('p1' if before == 1 else 's4')
    actions = [a for s in t.scripts for a in s.do]
    assert [a for a in actions if a[0] == 'NAMED_TRANSFER_OWNERSHIP_PLAYER'] == [
        ('NAMED_TRANSFER_OWNERSHIP_PLAYER', m.role('dish').name,
         m.player('p1' if after == 1 else 's4'))]
    assert not any('RADAR' in a[0] or 'REVEAL' in a[0] or 'DAMAGE' in a[0]
                   or a[0] in ('NAMED_DELETE', 'NAMED_KILL') for a in actions)


@pytest.mark.parametrize('name,readings', [
    ('engine_radarout', [(91, 1, True), (312, 2, False)]),
    ('engine_radarin', [(87, 2, False), (282, 1, True)]),
])
def test_radar_transfer_named_owner_lifetime_and_hud(name, readings):
    # E162 full HUD frames and independent owner/lifetime/power readings:
    # CampRadarOutEA_mcp_1115_174732/{0008,0041}.png.
    # CampRadarInEA_mcp_1115_175326/{0008,0033}.png.
    engine, world, m = replay(name)
    from ra3model.objects import radar
    from ra3model.objects.rules import power_of
    world.logic.power = 'objects'
    previous = 0
    for frame, owner, visible in readings:
        engine.run(frames=frame - previous)
        previous = frame
        assert (engine.value('E162Owner'), engine.value('E162Alive')) == (owner, 1)
        assert world.named(m.role('dish').name).owner == m.player('p1' if owner == 1 else 's4')
        assert all(world.named(m.role(r).name).alive
                   for r in ('yard', 'power', 'other yard', 'other power'))
        assert [power_of(world.logic, m.player(s)) for s in ('p1', 's4')] == [(150, 0), (150, 0)]
        assert radar.available(world.logic, m.player('p1')) is visible


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'E162 measured both owners powered with four live supports (counter=1); '
    'PLAYER_HAS_POWER object-world condition is unimplemented. '
    'See work/re/e162_radar_owner.md and work/re/handoff-e.md.'))
def test_radar_transfer_named_script_prerequisite():
    engine, world, m = replay('engine_radarout')
    engine.run(frames=91)
    assert engine.value('E162Support') == 1


def replay(name):
    import build
    import labpaths
    import modelpin
    from model import facing, merged, unnot
    if not (Path(labpaths.ENGINE_MODEL) / 'ra3model/objects/world.py').is_file():
        pytest.skip('no engine model (labpaths.ENGINE_MODEL)')
    modelpin.package(str(Path(labpaths.ENGINE_MODEL) / 'ra3model'))
    from ra3model import scripts
    from ra3model.objects import xmldata
    from ra3model.objects.world import LogicWorld
    m, t, _ = build.resolve(name, 'a')
    setup = merged(m, t)
    lib = xmldata.Library()
    for unit in m.units:
        lib.add_text(unit.xml, unit.id)
    world = LogicWorld(lib, areas=setup.areas, waypoints=setup.waypoints,
                       teams={m.team(o.side) for o in setup.objects})
    for obj in setup.objects:
        world.place(obj.template, obj.name, m.player(obj.side), m.team(obj.side),
                    obj.x, obj.y, facing(obj))
    engine = scripts.Engine(scripts.from_cnv(unnot(setup.scripts)), world,
                            difficulty=1, honor_inverted=False)
    return engine, world, m

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


def replay(name):
    import build
    import labpaths
    import simproxy
    from model import facing, merged, unnot
    if not (Path(labpaths.ENGINE_MODEL) / 'ra3model/objects/world.py').is_file():
        pytest.skip('no engine model (labpaths.ENGINE_MODEL)')
    simproxy._package(str(Path(labpaths.ENGINE_MODEL) / 'ra3model'))
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

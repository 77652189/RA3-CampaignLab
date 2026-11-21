"""E158: Radar diagnostic isolation and named prerequisite readings.

These are not radar availability assertions; the HUD observation is separate.
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('radar_bootstrap', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


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

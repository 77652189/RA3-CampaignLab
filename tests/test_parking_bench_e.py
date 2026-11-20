"""E157: airport module-removal control and named bench observations."""
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('parking_bootstrap', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_parking_single_module_control():
    import build
    from parts import contract, merged
    m, t, _ = build.resolve('engine_parking', 'a')
    on, off = [unit.xml for unit in m.units]
    on = on.replace('CNVE157Airfieldon', 'CNVE157Airfieldoff')
    assert re.sub(r'<ParkingPlaceBehavior\b.*?</ParkingPlaceBehavior>', '', on, flags=re.S) == off
    assert not any(o.template == 'AlliedFighterAircraft' for o in m.objects)
    assert not contract(merged(m, t))
    m, t, _ = build.resolve('engine_parkingswap', 'a')
    assert not contract(merged(m, t))


@pytest.mark.parametrize('name,frame,expected', [
    ('engine_parking', 194, (1, 0)),
    ('engine_parking', 982, (4, 0)),
    ('engine_parkingswap', 196, (1, 0)),
])
def test_parking_named_object_model_observations(name, frame, expected):
    import build
    import labpaths
    import modelpin
    from model import facing
    from parts import merged, unnot
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
    for k, obj in enumerate(setup.objects):
        assert lib.template(obj.template) is not None
        world.place(obj.template, obj.name or f'E157 support {k}', m.player(obj.side),
                    m.team(obj.side), obj.x, obj.y, facing(obj))
    engine = scripts.Engine(scripts.from_cnv(unnot(setup.scripts)), world,
                            difficulty=1, honor_inverted=False)
    # CampParkEA_mcp_1115_151840 / CampParkSwapEA_mcp_1115_152202 HUD samples.
    # No fitted production clock. Each sample is replayed independently.
    engine.run(frames=frame)
    assert (engine.value('E157on'), engine.value('E157off')) == expected

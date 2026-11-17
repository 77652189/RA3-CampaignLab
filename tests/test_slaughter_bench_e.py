"""E170: single-module carrier control and named sortie/return readings."""
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('slaughter_bootstrap', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_slaughter_carrier_only_removes_container():
    import build
    from parts import contract, merged
    m, t, _ = build.resolve('engine_slaughter_e', 'a')
    on, off = [u.xml for u in m.units]
    assert re.sub(r'<SlaughterHordeContain\b.*?</SlaughterHordeContain>', '',
                  on.replace('CNVE170On', 'CNVE170Off'), flags=re.S) == off
    assert not any(o.template == 'AlliedAttackDrone' for o in m.objects)
    assert not contract(merged(m, t))
    m, t, _ = build.resolve('engine_slaughter_e', 'b')
    assert not contract(merged(m, t))


@pytest.mark.parametrize('check', ['a', 'b'])
def test_slaughter_named_object_world_readings(check):
    import build
    import labpaths
    import simproxy
    from model import facing
    from parts import merged, unnot
    if not (Path(labpaths.ENGINE_MODEL) / 'ra3model/objects/world.py').is_file():
        pytest.skip('no engine model (labpaths.ENGINE_MODEL)')
    simproxy._package(str(Path(labpaths.ENGINE_MODEL) / 'ra3model'))
    from ra3model import scripts
    from ra3model.objects import xmldata
    from ra3model.objects.world import LogicWorld
    m, t, _ = build.resolve('engine_slaughter_e', check)
    setup = merged(m, t)
    lib = xmldata.Library()
    for unit in m.units:
        lib.add_text(unit.xml, unit.id)
    world = LogicWorld(lib, areas=setup.areas, waypoints=setup.waypoints,
                       teams={m.team(o.side) for o in setup.objects})
    for obj in setup.objects:
        assert lib.template(obj.template) is not None
        world.place(obj.template, obj.name, m.player(obj.side), m.team(obj.side), obj.x, obj.y, facing(obj))
    engine = scripts.Engine(scripts.from_cnv(unnot(setup.scripts)), world,
                            difficulty=1, honor_inverted=False)
    engine.run(frames=600)
    # Both real runs froze 600/11/0/0. This is a negative baseline,
    # not evidence that sortie, return or container consumption is modeled.
    assert [engine.value(c) for c in ('E170Frame', 'E170Hosts', 'E170Attack', 'E170Return')] == [600, 11, 0, 0]

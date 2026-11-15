"""E156: named detector probe replayed by the engine's existing object model."""
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('detector_bootstrap', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def _setup():
    import build
    import sim
    m, t, _ = build.resolve('engine_detector', 'a')
    return m, t, sim.Sim(m, t)


def test_detector_single_module_control():
    m, _, _ = _setup()
    on, off, far = [unit.xml for unit in m.units]
    on = on.replace('CNVE156Dogon', 'CNVE156Dogoff')
    assert re.sub(r'<StealthDetectorUpdate\b[^>]*/>', '', on, flags=re.S) == off
    assert far.replace('CNVE156Dogfar', 'CNVE156Dogoff') == on


def test_detector_named_object_model_observations():
    import labpaths
    import simproxy
    from parts import unnot
    if not (Path(labpaths.ENGINE_MODEL) / 'ra3model/objects/world.py').is_file():
        pytest.skip('no engine model (labpaths.ENGINE_MODEL)')
    simproxy._package(str(Path(labpaths.ENGINE_MODEL) / 'ra3model'))
    from ra3model import scripts
    from ra3model.objects import xmldata
    from ra3model.objects.world import LogicWorld
    m, _, setup = _setup()
    lib = xmldata.Library()
    for unit in m.units:
        lib.add_text(unit.xml, unit.id)
    world = LogicWorld(lib, areas=setup.areas, waypoints=setup.waypoints,
                       teams={b.team for b in setup.bodies.values() if b.team})
    for obj in m.objects:
        body = setup.body(obj.name)
        assert lib.template(body.template) is not None
        world.place(body.template, body.name, body.owner, body.team, body.x, body.y)
    engine = scripts.Engine(scripts.from_cnv(unnot(setup.mm.scripts)), world,
                            difficulty=1, honor_inverted=False)
    # Actual same-frame HUD samples (CampDetectEA_mcp_1115_150500).
    # Scan phase and the first/last reveal frames remain gaps.
    engine.run(frames=151)
    assert engine.value('E156Frame') == 151
    assert engine.value('E156Seen') == 1
    assert engine.value('E156Alive') == 111
    assert engine.value('E156Evidence') == 1
    engine.run(frames=159)
    assert engine.value('E156Frame') == 310
    assert engine.value('E156Seen') == 0
    assert engine.value('E156Alive') == 111
    assert engine.value('E156Evidence') == 3


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'E156: the plan simulator does not connect detector modules; the existing '
    'object model passes the measured snapshots. See work/re/e156_detector.md '
    'and work/re/handoff-e.md.'))
def test_detector_plan_simulator_measured_snapshot():
    m, t, setup = _setup()
    from parts import Script
    t.scripts.append(Script('Test - E156 measured snapshot', [
        ('COUNTER', 'E156Frame', 2, 151), ('COUNTER', 'E156Seen', 2, 1),
        ('COUNTER', 'E156Alive', 2, 111), ('COUNTER', 'E156Evidence', 2, 1)],
        [('SET_COUNTER', 'E156Matched', 1)]))
    import sim
    engine = sim.Sim(m, t).run(12)
    assert engine.eng.value('E156Matched') == 1

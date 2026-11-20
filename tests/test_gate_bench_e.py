"""E190: named replay of native door-template availability, not gate effects."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gate_bootstrap', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


@pytest.mark.parametrize('check', ['', 'a'])
def test_gate_runtime_cast_keeps_contract(check):
    import build
    from contract import contract
    from model import merged

    m, t, _ = build.resolve('engine_gate_e', check)
    setup = merged(m, t)
    assert contract(setup) == []
    # Doors must stay runtime creations: placing them reintroduces the SDK failure.
    assert [obj.name for obj in setup.objects] == ['E190 anchor']
    creates = [s for s in setup.scripts if s.name.startswith('Test - create ')]
    assert len(creates) == 3
    assert all(s.when == [('COUNTER', 'E190Frame', 2, 30)] for s in creates)
    assert {s.do[0][1] for s in creates} == {
        m.role(tag).name for tag in ('Romania', 'Sanitarium', 'Sentinel')}
    assert sum(s.name == 'Test - clock' for s in setup.scripts) == 1


def _replay():
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

    m, t, _ = build.resolve('engine_gate_e', 'a')
    setup = merged(m, t)
    lib = xmldata.Library()
    for unit in m.units:
        lib.add_text(unit.xml, unit.id)
    world = LogicWorld(lib, areas=setup.areas, waypoints=setup.waypoints,
                       teams={m.team(o.side) for o in setup.objects})
    for k, obj in enumerate(setup.objects):
        assert lib.template(obj.template) is not None
        world.place(obj.template, obj.name or f'E190 support {k}', m.player(obj.side),
                    m.team(obj.side), obj.x, obj.y, facing(obj))
    engine = scripts.Engine(scripts.from_cnv(unnot(setup.scripts)), world,
                            difficulty=1, honor_inverted=False)
    engine.run(frames=180)
    return engine


@pytest.mark.parametrize('counter,expected', [
    ('E190Frame', 180),
    ('E190Sentinel', 1),
    pytest.param('E190Romania', 0, marks=pytest.mark.xfail(strict=True,
        reason='E190: SDK door creates in model but is absent at bench f180; see work/re/e190_gate.md')),
    pytest.param('E190Sanitarium', 0, marks=pytest.mark.xfail(strict=True,
        reason='E190: SDK door creates in model but is absent at bench f180; see work/re/e190_gate.md')),
])
def test_gate_native_templates_named_bench(counter, expected):
    assert _replay().value(counter) == expected

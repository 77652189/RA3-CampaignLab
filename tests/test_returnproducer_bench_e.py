"""E173: produced-aircraft reference and single-module removal control."""
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('return_bootstrap', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_returnproducer_only_module_removed_and_produced_reference():
    import build
    from parts import contract, merged
    on, a, _ = build.resolve('engine_returnon_e', 'a')
    off, b, _ = build.resolve('engine_returnoff_e', 'a')
    assert re.sub(r'<ReturnToProducerSpecialPower\b[^>]*/>', '', on.units[0].xml, flags=re.S) == off.units[0].xml
    for m, t in ((on, a), (off, b)):
        assert not any(o.template == 'AlliedFighterAircraft' for o in m.objects)
        assert not contract(merged(m, t))
        assert ('MOVE_NAMED_UNIT_TO', m.role('plane').name, m.mark('sortie')) in [
            action for script in merged(m, t).scripts for action in script.do]
    # Corrected b must override the retail id through the explicit linker
    # path. It is prepared only; no b engine measurement is claimed.
    from package import spec_of
    fixed_on, ta, _ = build.resolve('engine_returnon_e', 'b')
    fixed_off, tb, _ = build.resolve('engine_returnoff_e', 'b')
    for m, t in ((fixed_on, ta), (fixed_off, tb)):
        assert not contract(merged(m, t))
        assert spec_of(m, t).replaces == ('GameObject:AlliedFighterAircraft',)
        assert m.assets[0][0] == m.units[0].id + '.xml'
    assert re.sub(r'<ReturnToProducerSpecialPower\b[^>]*/>', '', fixed_on.assets[0][1], flags=re.S) == fixed_off.assets[0][1]


@pytest.mark.parametrize('name', ['engine_returnon_e', 'engine_returnoff_e'])
@pytest.mark.parametrize('check', ['', 'a', 'b'])
def test_returnproducer_runtime_cast_keeps_contract(name, check):
    import build
    from contract import contract
    from model import merged

    m, t, _ = build.resolve(name, check)
    setup = merged(m, t)
    assert contract(setup) == []
    plane = m.role('plane').name
    assert plane not in {obj.name for obj in setup.objects}
    # Preserve real production, naming and orders, without a dummy placed plane.
    expected = {'Test - clock', 'Test - start', 'Test - produce',
                'Test - reference', 'Test - depart', 'Test - return'}
    assert {s.name for s in m.scripts} == expected
    assert all(sum(s.name == label for s in setup.scripts) == 1 for label in expected)
    reference = next(s for s in setup.scripts if s.name == 'Test - reference')
    assert reference.when == [('COUNTER', 'E173Frame', 2, 240)]
    assert reference.do == [('TEAM_SET_PLAYERS_NEAREST_UNIT_OF_TYPE_TO_REFERENCE',
                             m.role('plane').template, m.team(), plane)]


def _replay(name):
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
        if name == 'engine_returnoff_e':
            # a did not override retail; model the actual linked template,
            # rather than its ineffective removal source.
            unit = build.resolve('engine_returnon_e', 'a')[0].units[0]
        lib.add_text(unit.xml, unit.id)
    world = LogicWorld(lib, areas=setup.areas, waypoints=setup.waypoints,
                       teams={m.team(o.side) for o in setup.objects})
    for k, obj in enumerate(setup.objects):
        assert lib.template(obj.template) is not None
        world.place(obj.template, obj.name or f'E173 support {k}', m.player(obj.side),
                    m.team(obj.side), obj.x, obj.y, facing(obj))
    engine = scripts.Engine(scripts.from_cnv(unnot(setup.scripts)), world,
                            difficulty=1, honor_inverted=False)
    engine.run(frames=660)
    return engine


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'E186 departure reaches bench 7; return dispatch remains a gap. '
    'See work/re/e186_movement.md and work/re/handoff-e.md.'))
@pytest.mark.parametrize('name,final,casts', [
    ('engine_returnon_e', 11, 1), ('engine_returnoff_e', 11, 1),
])
def test_returnproducer_named_object_model_bench(name, final, casts):
    engine = _replay(name)
    assert engine.value('E173Frame') == 660
    # Both measurements use the same direct reference to a genuinely produced
    # aircraft; do not replace this prerequisite with a manually placed plane.
    assert engine.value('E173Depart') == 7
    assert engine.value('E173Final') == final
    assert engine.value('E173Cast') == casts


@pytest.mark.parametrize('name', ['engine_returnon_e', 'engine_returnoff_e'])
def test_returnproducer_departure_bench_prerequisite(name):
    engine = _replay(name)
    # a's two native observations both reached the sortie at f405 (bit 4).
    assert engine.value('E173Frame') == 660
    assert engine.value('E173Depart') == 7
    plane = engine.world.named('UNITRef - E173 Plane')
    assert plane is not None
    assert plane.producer is engine.world.named('E173 Airport')

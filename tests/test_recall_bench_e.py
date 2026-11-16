"""E184: only airport recall is removed; production and sortie stay native."""
import importlib.util
import re
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('recall_bootstrap', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_recall_only_airport_module_removed():
    import build
    from parts import contract, merged
    from package import spec_of
    from checks.engine_recall_e import REMOVE
    on, a, _ = build.resolve('recallon_e', 'a')
    off, b, _ = build.resolve('recalloff_e', 'a')
    assert re.subn(REMOVE, '', on.units[0].xml, flags=re.S) == (off.units[0].xml, 1)
    assert on.objects == off.objects
    for m, t in ((on, a), (off, b)):
        assert not contract(merged(m, t))
        assert spec_of(m, t).replaces == ('GameObject:AlliedAirfield',)
        assert not any(o.template == 'AlliedFighterAircraft' for o in m.objects)



def _replay(name):
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
    for k, obj in enumerate(setup.objects):
        assert lib.template(obj.template) is not None
        world.place(obj.template, obj.name or f'E184 support {k}', m.player(obj.side),
                    m.team(obj.side), obj.x, obj.y, facing(obj))
    engine = scripts.Engine(scripts.from_cnv(unnot(setup.scripts)), world,
                            difficulty=1, honor_inverted=False)
    engine.run(frames=660)
    return engine


@pytest.mark.parametrize('name,final,casts', [
    ('recallon_e', 3, 1),
    ('recalloff_e', 5, 0),
])
def test_recall_named_object_model_bench(name, final, casts):
    engine = _replay(name)
    assert engine.value('E184Frame') == 660
    assert engine.value('E184Depart') == 7
    assert engine.value('E184Final') == final
    assert engine.value('E184Cast') == casts



@pytest.mark.parametrize('name', ['recallon_e', 'recalloff_e'])
def test_recall_production_reference_departure_bench_prerequisite(name):
    engine = _replay(name)
    # Original f255 live/near bits 1/2 and f405 sortie bit 4, unchanged.
    assert engine.value('E184Depart') == 7
    plane = engine.world.named('UNITRef - E184 Plane')
    assert plane is not None
    assert plane.producer is engine.world.named('E184 Airport')
    assert plane.owner == plane.producer.owner
    assert plane.team == plane.producer.team
    assert len([o for o in engine.world.living() if o.template == 'AlliedFighterAircraft']) == 1

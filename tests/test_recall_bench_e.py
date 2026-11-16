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


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'E184 native production/reference replay yields departure 0 versus bench 7; '
    'recall dispatch and producer binding remain gaps. See work/re/e184_recall.md '
    'and work/re/handoff-e.md.'))
@pytest.mark.parametrize('name,final,casts', [
    ('recallon_e', 3, 1), ('recalloff_e', 5, 0),
])
def test_recall_named_object_model_bench(name, final, casts):
    engine = _replay(name)
    assert engine.value('E184Frame') == 660
    assert engine.value('E184Depart') == 7
    assert engine.value('E184Final') == final
    assert engine.value('E184Cast') == casts


"""E168: named single-rocket Bezier module-removal bench replay."""
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('bezier_bootstrap', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_bezier_projectile_only_module_is_removed():
    import build
    m, _, _ = build.resolve('engine_bezier_e', 'a')
    on, off = m.units[:2]
    assert on.xml.replace('CNVE168On', 'CNVE168Off') == off.xml
    xml = next(iter(on.files.values())).replace('CNVE168On', 'CNVE168Off')
    assert re.sub(r'<BezierProjectile\b[^>]*/>', '', xml, flags=re.S) == next(iter(off.files.values()))


def test_bezier_named_bench_single_rocket_damage_and_control():
    import build
    import labpaths
    import simproxy
    from model import facing
    from parts import merged, unnot
    if not (Path(labpaths.ENGINE_MODEL) / 'ra3model/objects/world.py').is_file():
        pytest.skip('no engine model (labpaths.ENGINE_MODEL)')
    simproxy._package(str(Path(labpaths.ENGINE_MODEL) / 'ra3model'))
    from ra3model import scripts
    from ra3model.objects import weapons, xmldata
    from ra3model.objects.world import LogicWorld

    class StandingFireWorld(LogicWorld):
        def order(self, engine, name, args):
            super().order(engine, name, args)
            if name == 'NAMED_ATTACK_NAMED':
                assert weapons.attack(self.named(args[0]), self.named(args[1]))

    m, t, _ = build.resolve('engine_bezier_e', 'a')
    setup = merged(m, t)
    lib = xmldata.Library()
    for unit in m.units:
        lib.add_text(unit.xml, unit.id)
        for filename, xml in (unit.files or {}).items():
            lib.add_text(xml, filename)
    world = StandingFireWorld(lib, areas=setup.areas, waypoints=setup.waypoints,
                              teams={m.team(obj.side) for obj in setup.objects})
    for obj in setup.objects:
        assert lib.template(obj.template) is not None
        world.place(obj.template, obj.name, m.player(obj.side), m.team(obj.side), obj.x, obj.y, facing(obj))
    engine = scripts.Engine(scripts.from_cnv(unnot(setup.scripts)), world,
                            difficulty=1, honor_inverted=False)
    engine.run(frames=240)
    assert engine.value('E168Frame') == 240
    assert [engine.value(c) for c in ('E168Base', 'E168On', 'E168Off')] == [3, 95, 100]
    assert all(world.named(m.role(tag + 'target').name).alive for tag in ('On', 'Off'))

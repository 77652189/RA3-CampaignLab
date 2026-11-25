"""The IgnoreTargets.Rule benches differ in the Rule alone; their readings are benches/ai/tactics/readings.toml#engine_aiignore_rule."""
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai_run', ROOT / 'experimental/cnv/simai_run.py')
simai_run = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai_run)      # puts experimental/cnv on the path (build, contract, model)


def test_ignore_rule_fixture_changes_only_rule():
    import build
    from contract import contract
    from model import merged

    views = []
    for name, rule in [('aiignrany', 'ANY'), ('aiignrall', 'ALL')]:
        m, t, build_name = build.resolve(name, 'r')
        assert len(build_name) <= 15 and '_' not in build_name
        assert contract(merged(m, t)) == []
        xml = ET.fromstring(m.assets[0][1])
        micro = next(e for e in xml.iter() if e.tag.endswith('}AIMicroManagerData'))
        ignore = next(e for e in micro if e.tag.endswith('}IgnoreTargets'))
        assert ignore.attrib.pop('Rule') == rule
        assert ignore.attrib == {'Include': 'NEUTRAL_TECH TIME_BOMB'}
        assert micro.get('MinDistanceFromBaseToIgnoreTargets') == '0'
        assert m.ext and m.objects[-1].template == 'CNVTeamsHost'
        assert 'MinFrames="15"' in m.units[-1].xml
        views.append((ET.tostring(xml), m.objects, m.scripts, m.waypoints,
                      m.facts, m.cnv_named, t))
    assert views[0] == views[1]

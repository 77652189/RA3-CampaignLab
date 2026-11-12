"""Base-distance gate probe: identical geometry and a single XML gate contrast."""
import xml.etree.ElementTree as ET
import importlib.util
from pathlib import Path
import pytest


ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)


def test_ignore_distance_fixture_changes_only_distance():
    import build
    from contract import contract
    from model import merged

    views = []
    for name, distance in [('aiignzero', '0'), ('aiignnear', '2000')]:
        m, t, _ = build.resolve(name, 'r')
        assert contract(merged(m, t)) == []
        xml = ET.fromstring(m.assets[0][1])
        micro = next(e for e in xml.iter() if e.tag.endswith('}AIMicroManagerData'))
        assert micro.attrib.pop('MinDistanceFromBaseToIgnoreTargets') == distance
        assert micro.get('UseSpecialPowers') == 'false'
        assert micro.get('DodgeThreats') == 'false'
        assert micro.get('PullbackInjured') == 'false'
        assert len(m.cnv_named) == 2
        assert m.facts['target earliest at'] == 26
        views.append((ET.tostring(xml), m.objects, m.scripts, m.waypoints, m.cnv_named))
    assert views[0] == views[1]


@pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')
@pytest.mark.parametrize('name', ['aiignzero', 'aiignnear'])
def test_ignore_distance_replays_named_damage_observation(name):
    w = simai.run(name, 'r', until=50)
    rows = [values for _, values in w.sim.series]
    # The targets cannot be attacked before both warriors exist. Keep the
    # rejected first probe's contamination out of the replay acceptance.
    before = [v for v in rows if 23 * simai.FPS <= v[0] < 26 * simai.FPS]
    assert before and all(v[1] == 2 and v[2:] == [0, 0] for v in before), before
    after = [v for v in rows if 28 * simai.FPS <= v[0] <= 49 * simai.FPS]
    assert after and any(v[2] == 1 for v in after), after
    first = {v[3] for v in after if v[2]}
    assert len(first) == 1 and next(iter(first)) >= 26 * simai.FPS, first

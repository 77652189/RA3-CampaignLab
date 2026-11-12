"""Native-beacon DodgeThreats contrast; unresolved consumers stay explicit gaps."""
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest


ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)


def test_micro_dodge_fixture_changes_only_the_switch():
    import build
    from contract import contract
    from model import merged

    views = []
    for name, enabled in (('aidodgeon', 'true'), ('aidodgeoff', 'false')):
        m, t, _ = build.resolve(name, 'r')
        assert contract(merged(m, t)) == []
        xml = ET.fromstring(m.assets[0][1])
        micro = next(e for e in xml.iter() if e.tag.endswith('}AIMicroManagerData'))
        assert micro.attrib.pop('DodgeThreats') == enabled
        assert micro.get('DodgeThreatsReactionTimeMin') == '0.5s'
        assert micro.get('DodgeThreatsReactionTimeMax') == '0.5s'
        assert micro.get('UseSpecialPowers') == 'false'
        assert micro.get('PullbackInjured') == 'false'
        views.append((ET.tostring(xml), m.objects, m.scripts, m.waypoints))
    assert views[0] == views[1]


@pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')
@pytest.mark.parametrize('name,limit', [
    pytest.param('aidodgeon', 1, marks=pytest.mark.xfail(strict=True, raises=AssertionError,
                 reason='native beacon: two living warriors leave the sample square with DodgeThreats on; '
                        'micro has no dodge consumer and simai.micro_team supplies no threat view/move hook. '
                        'See work/re/handoff-c.md and work/re/c_dodge_report.md')),
    ('aidodgeoff', 2),
])
def test_micro_dodge_replays_named_beacon_observation(name, limit):
    w = simai.run(name, 'r', until=34.0)
    # Use the displayed game-frame counter, as with the native readings; capture
    # wall seconds drift and made the on probe's automatic window report FAIL.
    before = [values for _, values in w.sim.series if 27 * simai.FPS <= values[0] < 29 * simai.FPS]
    assert before and all(values[1:3] == [2, 2] for values in before), before
    rows = [(s, values) for s, values in w.sim.series if 31 * simai.FPS <= values[0] < 34 * simai.FPS]
    assert rows
    assert all(values[1] == 2 for _, values in rows), rows  # leaving must not be death
    assert any(values[3] == 1 for _, values in rows), rows
    near = [values[2] for _, values in rows]
    if name == 'aidodgeon':
        assert min(near) <= limit, rows
    else:
        assert set(near) == {limit}, rows

"""Single Rule contrast; measured selection and bypass damage stay separate."""
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)


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


@pytest.fixture(scope='module')
def rule_replays():
    return {}


def _replay(name, cache):
    if name not in cache:
        cache[name] = simai.run(name, 'r', until=33, record=True)
    return cache[name]


@pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')
@pytest.mark.parametrize('name', ['aiignrany', 'aiignrall'])
def test_ignore_rule_named_damage_and_prerequisites(name, rule_replays):
    """Both rules hurt targets; this measures bypass damage, not Rule coverage."""
    w = _replay(name, rule_replays)
    rows = [v for _, v in w.sim.series]
    before = [v for v in rows if 375 <= v[0] < 390]
    assert before and all(v[1:] == [2, 0, 0] for v in before), before
    after = [v for v in rows if 421 <= v[0] <= 480]
    assert after and all(v[1] == 2 and v[2] >= 390 and v[3] == 0 for v in after), after
    assert len({v[2] for v in after}) == 1


@pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')
@pytest.mark.parametrize('name, state, has_target', [
    pytest.param('aiignrany', 0, True, marks=pytest.mark.xfail(
        strict=True, raises=AssertionError, reason=(
            'ANY permits the measured micro target, but engineer candidate/Alpha '
            'eligibility still replays state 2/no target; see work/re/e118_ignore_rule.md.'))),
    ('aiignrall', 8, False),
])
def test_ignore_rule_named_target_state(name, state, has_target, rule_replays):
    """Same-run CNVTeams readings, two members; target IDs do not imply identity."""
    w = _replay(name, rule_replays)
    rows = [row for brain in w.brains.values() for row in brain.rec['frames']
            if row['state_key'] == 'CNVStateMicro' and len(row['members']) == 2]
    actual = [(row['frame'], row['state'], row['foe_id'] is not None)
              for row in rows if row['frame'] in (406, 421)]
    assert actual == [(406, state, has_target), (421, state, has_target)], actual

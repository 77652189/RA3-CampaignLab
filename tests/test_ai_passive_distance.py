"""Named passive-distance probes; measured acceptance added after the bench."""
import xml.etree.ElementTree as ET
import importlib.util
import math
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)


def test_passive_distance_fixture():
    import build
    from contract import contract
    from model import merged

    views = []
    for name, distance in [('aipsdz', '0'), ('aipsdt', '1'), ('aipsds', '200'), ('aipsdl', '600')]:
        m, t, mod = build.resolve(name, 'r')
        assert contract(merged(m, t)) == []
        assert len(mod) <= 15 and '_' not in mod
        xml = ET.fromstring(m.assets[0][1])
        micro = next(e for e in xml.iter() if e.tag.endswith('}AIMicroManagerData'))
        assert micro.attrib.pop('PassiveTargetSearchDistance') == distance
        assert micro.get('EngageTacticalTarget') == 'false'
        assert micro.get('EngagePassiveTargets') == 'true'
        assert 'MinFrames="15"' in m.units[-1].xml
        views.append((ET.tostring(xml), m.objects, m.scripts, t.counters))
    assert all(view == views[0] for view in views)


@pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')
@pytest.mark.parametrize('name', ['aipsdz', 'aipsdt', 'aipsds', 'aipsdl'])
def test_passive_distance_named_side_selection(name):
    """The measured 0/1/200/600 runs select the side plant with four living members.

    This is a bounded selection observation, not proof of the field's consumer.
    Exact timing is asserted separately; do not fit the model's startup clock.
    """
    w = simai.run(name, 'r', until=22, record=True)
    rows = [r for b in w.brains.values() for r in b.rec['frames']
            if r['state_key'] == 'CNVStateGo']
    picked = [r for r in rows if r['foe'] == 'UNIT - CNV AI Side Plant']
    assert picked
    first = picked[0]
    assert first['state'] == 6 and len(first['members']) == 4
    assert all(m['alive'] for m in first['members'])
    assert first['foe_id'] != first['target_id']
    initial = next(r for r in rows if len(r['members']) == 4)
    side = (3400, 2823)
    distances = [math.dist(m['pos'], side) for m in first['members']]
    assert min(distances) < min(math.dist(m['pos'], side) for m in initial['members'])
    if name in ('aipsdt', 'aipsds'):
        # Bench f140: every member is >324 from the side plant, despite 1/200.
        radius = 1 if name == 'aipsdt' else 200
        assert all(d > radius for d in distances)


@pytest.mark.skipif(not simai.available(), reason='no ra3model.ai (labpaths.ENGINE_MODEL)')
@pytest.mark.parametrize('name', ['aipsdz', 'aipsdt', 'aipsds', 'aipsdl'])
@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'Same-run bench selects the side plant in state 6 at logic frame 140; '
    'model first selects at 241 (startup/search geometry gaps). '
    'See work/re/e104_passive_distance.md and work/re/handoff-e.md.'))
def test_passive_distance_named_exact_first_selection(name):
    w = simai.run(name, 'r', until=17, record=True)
    rows = [r for b in w.brains.values() for r in b.rec['frames']
            if r['state_key'] == 'CNVStateGo' and r['foe'] is not None]
    assert rows
    first = rows[0]
    assert (first['frame'], first['state'], first['foe'], len(first['members'])) == (
        140, 6, 'UNIT - CNV AI Side Plant', 4)

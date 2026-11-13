"""CountAsStructure ExcludeThing: named two-factory contrast."""
import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)


def test_build_exclude_single_input():
    import build
    views = []
    for name in ('aibex', 'aibin'):
        m, _, build_name = build.resolve(name, 'r')
        assert len(build_name) <= 15 and '_' not in build_name
        assert m.ext
        root = ET.fromstring(m.assets[-1][1])
        filt = next(e for e in root.iter() if e.tag.endswith('}CountAsStructureForBuildPurposesFilter'))
        nodes = [e for e in filt if e.tag.endswith('}ExcludeThing') and e.text == 'CNVDearPK']
        assert len(nodes) == (name == 'aibex')
        for node in nodes:
            filt.remove(node)
        views.append((ET.tostring(root), m.objects, m.scripts, [u.xml for u in m.units]))
    assert views[0] == views[1]


@pytest.mark.parametrize('name', ['aibex', 'aibin'])
def test_build_exclude_original_readings(name):
    path = Path(simai.labpaths.WORK) / 're/c_buildexclude_measured.json'
    if not path.exists():
        pytest.skip('private original bench archive unavailable')
    evidence = json.loads(path.read_text(encoding='utf-8'))[name]
    assert evidence['first_owned'] == {'CNVNewPK': 501, 'CNVDearPK': 570}
    assert evidence['orders'] == []  # registry observer did not see the factory's requests
    rows = [row[2] for row in evidence['rows'] if 36 <= row[0] <= 40]
    assert rows and all(row[:2] == [1, 1] for row in rows), rows


@pytest.mark.skipif(not simai.available(), reason='private AI model unavailable')
@pytest.mark.xfail(strict=True, raises=AssertionError, reason=(
    'Both engine variants first own CNVNewPK then CNVDearPK; early production '
    'path/basket and simultaneous IncludeThing/ExcludeThing precedence are not '
    'isolated. See work/re/c_buildexclude_report.md and handoff-c.md.'))
@pytest.mark.parametrize('name', ['aibex', 'aibin'])
def test_build_exclude_named_first_wave_replay(name):
    # Only the first production wave is compared. Later team losses and
    # replenishment do not identify the basket used for an initial request.
    w = simai.run(name, 'r', until=40)
    rows = [(second, values[:2]) for second, values in w.sim.series if any(values[:2])]
    # Original engine counters: s32..35 = 1/0, s36..40 = 1/1 in both
    # variants. Compare production, not model request logs, with that fact.
    assert rows and rows[0][1] == [1, 0], rows[:8]

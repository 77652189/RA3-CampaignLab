"""C: retail MinEnemyValue named replay; work/re/c_minvalue_report.md."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)
pytestmark = pytest.mark.skipif(not simai.available(), reason='no private AI model')


@pytest.fixture(scope='module', params=('aiminvalue', 'aiminvaluehi'))
def replay(request):
    w = simai.run(request.param, 'a', 61, lib=simai.model()['xmldata'].Library())
    rows = [(second, values) for second, values in w.sim.series if 40 <= second <= 60]
    assert len(rows) == 21
    return request.param, rows


def test_min_enemy_value_retail_named_bench_replay(replay):
    build, rows = replay
    expected = (0, 4, 4) if build == 'aiminvalue' else (0, 4, 0)
    for second, values in rows:
        assert tuple(values[:3]) == expected, (second, values)


def test_min_enemy_value_inverted_retail_named_bench_replay(replay, request):
    build, rows = replay
    if build == 'aiminvalue':
        request.node.add_marker(pytest.mark.xfail(strict=True, reason=
            'Engine low-value inverted group leaves one member home; model leaves zero. '
            'Recruitment/movement cause unresolved; see work/re/c_minvalue_report.md and handoff-c.md.'))
    expected = 1 if build == 'aiminvalue' else 4
    for second, values in rows:
        assert values[3] == expected, (second, values)

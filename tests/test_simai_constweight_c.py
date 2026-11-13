"""C: named ConstantHeuristic.Weight replays; work/re/c_constweight_report.md."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)
pytestmark = pytest.mark.skipif(not simai.available(), reason='no private AI model')


@pytest.mark.parametrize('build,home', [('aicwzero', 4), ('aicwone', 0)])
def test_constant_weight_named_replay(build, home):
    """Engine s40 infantry home/total and unregistered tank control."""
    w = simai.run(build, 'a', 41, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    rows = {t: dict(zip(labels, values)) for t, values in w.sim.series}
    row = rows[40]
    assert tuple(row[k] for k in ('步兵在家', '步兵总数', '坦克在家')) == (home, 4, 4), row

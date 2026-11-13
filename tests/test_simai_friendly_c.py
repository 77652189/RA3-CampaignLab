"""C FriendlyUnit Distance replay; original observations in private report.

The assertion concerns the tactical target, independently of team movement.
Other sort modes, relationship defaults and unique slots remain unverified.
"""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(simai)
pytestmark = pytest.mark.skipif(not simai.available(), reason='no ra3model.ai')


@pytest.mark.parametrize('build,frame,target', [('aifrnear', 478, 'UNIT - Friendly MCV'),
                                         ('aifrswap', 486, 'UNIT - Friendly second')])
def test_friendly_distance_target(build, frame, target):
    """engine_aifrdistance a: replay the observed tactical target at s30."""
    w = simai.run(build, 'a', (frame + 1) / 15, lib=simai.model()['xmldata'].Library())
    targets = {b._name(r.target) for b in w.brains.values()
               for r in b.tactics.runs.values() if r.target is not None}
    assert targets == {target}
    labels = [label for _, label in w.sim.test.counters]
    rows = [dict(zip(labels, values)) for second, values in w.sim.series if second == 30]
    assert len(rows) == 1
    assert (rows[0]['友车存活'], rows[0]['敌车存活']) == (3, 1)

"""C-line BuildEntry.Upgrade presence pair; readings in checks/engine_aiupgrade.py.

Use CNV_ENGINE_MODEL pointing at RA3-EngineModel-codexc. No level content imports.
"""
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)
pytestmark = pytest.mark.skipif(not simai.available(), reason='no private AI model')


@pytest.fixture(scope='module', params=['aicupgon', 'aicupgoff'])
def upgrade_entry_pair(request):
    build = request.param
    w = simai.run(build, 'a', 102.0)
    labels = [label for _, label in w.sim.test.counters]
    rows = [dict(zip(labels, values)) for second, values in w.sim.series if 40 <= second <= 100]
    return build, rows


def test_upgrade_entry_pair_setup(upgrade_entry_pair):
    """The refinery prerequisite and the sole upgrade seller survive the observation."""
    _, rows = upgrade_entry_pair
    assert rows
    assert all(row['矿厂数'] >= 1 and row['建造厂数'] == 1 for row in rows)


def test_upgrade_entry_pair_ownership(upgrade_entry_pair):
    """Compare the bench's Tech2 ownership with the named simulator replay: bench aicupgon:a holds 2 from s39
    (the yard and the barracks its TechUpgradeReceiver reaches), the model buys it at s20 and holds 2 from s40."""
    build, rows = upgrade_entry_pair
    holders = [row['二级持有'] for row in rows]
    assert all(n == (2 if build == 'aicupgon' else 0) for n in holders)

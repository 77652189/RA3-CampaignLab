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


def test_upgrade_ban_holds_until_the_allow_as_the_bench():
    """ALLOW_DISALLOW_ONE_UPGRADE (A264, bench aicupgon:ban): s1's Upgrade_AlliedTech2 banned at the start, allowed at
    40 s. Bench: 0 holders s1-s62, 2 from s63. The model holds none to the allow and 2 from s56 (its rebuy right at
    the allow is 7 s before the bench's, an INFERRED gap in the check's docstring); asserted: none until 10 s after
    the allow, and 2 from the bench's s63 on."""
    w = simai.run('aicupgon', 'ban', 66.0)
    labels = [label for _, label in w.sim.test.counters]
    rows = [(second, dict(zip(labels, values))['二级持有']) for second, values in w.sim.series]
    assert all(n == 0 for second, n in rows if second <= 50), rows
    assert [n for second, n in rows if second >= 63] and all(n == 2 for second, n in rows if second >= 63), rows

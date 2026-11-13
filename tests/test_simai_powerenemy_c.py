"""C: enemy-defense single-parameter control; work/re/c_powerenemy_report.md."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)
pytestmark = pytest.mark.skipif(not simai.available(), reason='no private AI model')


@pytest.mark.parametrize('build,home', [('aipenoff', 0), ('aipenon', 8)])
def test_power_enemy_defenses_named_replay(build, home):
    """Replay s40 home, army totals, live tower controls."""
    w = simai.run(build, 'a', 41, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    rows = {t: dict(zip(labels, values)) for t, values in w.sim.series}
    row = rows[40]
    assert tuple(row[k] for k in ('坦克在家', '坦克总数', '玩家坦克', '玩家防御塔')) == (home, 8, 4, 1), row

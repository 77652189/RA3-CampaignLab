"""C: named initial tech-ownership replays. See work/re/c_techshare_report.md."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('simai', ROOT / 'experimental/cnv/simai.py')
simai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(simai)
pytestmark = pytest.mark.skipif(not simai.available(), reason='no private AI model')


@pytest.fixture(scope='module', params=[('aitechlow', 1), ('aitechhigh', 2)])
def tech_share_replay(request):
    build, own = request.param
    w = simai.run(build, 'a', 41, lib=simai.model()['xmldata'].Library())
    labels = [label for _, label in w.sim.test.counters]
    rows = {t: dict(zip(labels, values)) for t, values in w.sim.series}
    return build, own, rows


def test_tech_share_ownership_control(tech_share_replay):
    """Engine ownership counter from s1 through s40; independent of gate failures."""
    _, own, rows = tech_share_replay
    assert all(t in rows and rows[t]['油井数'] == own for t in range(1, 41))


@pytest.mark.xfail(strict=True, reason='Initial tech-share gates disagree with engine; '
    'active-owner count versus configured player slots/global tech registration unresolved. '
    'See work/re/c_techshare_report.md and handoff-c.md')
def test_tech_share_initial_ownership(tech_share_replay):
    """Named s40 replay of measured home counts, never the pre-run prediction.

    The engine player denominator, global registration and native state
    weights are not observed; no formula is fitted to these outcomes.
    """
    _, _, rows = tech_share_replay
    row = rows[40]
    assert tuple(row[k] for k in ('低阈下', '低阈上', '高阈下')) == (4, 0, 4), row

"""Search-multiplier replay against benches/ai/targets/checks.py#engine_aisearch's A/B measurements."""
from test_simai_bench_b import lib, _probe_run, pytestmark  # noqa: F401


def test_search_multiplier_changes_the_passive_target_detour(lib):
    """benches/ai/targets/checks.py#engine_aisearch aisrchhi/aisrchlo: same geometry, only multiplier differs."""
    _, high = _probe_run('aisrchhi', lib, 35.0)
    _, low = _probe_run('aisrchlo', lib, 35.0)
    assert any(r['旁厂血量'] < 100 for r in high)
    assert all(r['到远厂'] == 0 for r in high)
    assert all(r['旁厂血量'] == 100 for r in low)
    assert any(r['到远厂'] >= 1 for r in low)

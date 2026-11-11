"""Finite AlphaStrike health probe and its complete, uninjected replay."""
import struct
import pytest

from test_simai_bench_b import lib, _probe_run, pytestmark, simai  # noqa: F401


def test_alpha_probe_preserves_the_float_health_script_argument():
    """Integer 70 writes an empty float slot and kills the target on the engine."""
    from missions.aialphahp_bench import mission
    from mapscript import encode_arg

    for high in (False, True):
        m = mission(high)
        script = next(s for s in m.scripts if s.name == 'CNV Alpha - target health')
        value = script.do[0][2]
        assert struct.unpack_from('<f', encode_arg(0, value), 8)[0] == 70.0
    low, high = mission(False), mission(True)
    assert low.assets[0][1] == high.assets[0][1].replace(
        'AlphaStrikeTargetHealthPct="0.9"', 'AlphaStrikeTargetHealthPct="0.01"')
    assert low.objects == high.objects
    assert low.scripts == high.scripts


@pytest.mark.parametrize('build', ['aialphalo', 'aialphahi'])
def test_alpha_threshold_first_cycle_retreats_with_the_target_alive(lib, build):
    """engine_aialphahp: BOTH measured lanes retreat, disproving the high-lane hypothesis.

    Only first-cycle arrival/return and unchanged target HP are asserted;
    exact event frames and later cycles are not matched. This is not proof
    that the AlphaStrike branch works (engine state is not observed).
    """
    _, rows = _probe_run(build, lib, 40.0)
    assert rows[5]['目标血量'] == 70
    assert any(r['到远厂'] >= 1 for r in rows[10:35])
    assert any(r['步兵在家'] >= 1 and r['步兵数'] >= 1 for r in rows[25:40])
    assert all(r['目标血量'] == 70 for r in rows)

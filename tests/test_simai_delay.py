"""MaximumDelay pair: the probe's micro data as the map compiler takes it, and the micro manager's upper endpoint.
The bench's script counters are readings: experimental/cnv/checks/engine_aidelay.readings.toml."""
import xml.etree.ElementTree as ET
import pytest

from test_simai_bench_b import pytestmark  # noqa: F401
from test_simai_bench_b import simai


@pytest.mark.parametrize('maximum', [0, 999])
def test_maximum_delay_probe_obeys_sdk_child_sequence(maximum):
    """SDK AIMicroManagerData requires delays before retreat/ignore filters.

    The parser accepts either order, but the real map compiler rejected the
    original pair before it could reach the game (2026-11-11).
    """
    import build
    m, t, _ = build.resolve('aidelay999' if maximum else 'aidelay0', 'a')
    ns = {'a': 'uri:ea.com:eala:asset'}
    micro = ET.fromstring(m.assets[0][1]).find('a:AIMicroManagerData', ns)
    assert [node.tag.rsplit('}', 1)[-1] for node in micro] == [
        'SpecificSpecialPowerDelay', 'RetreatBaseCriteria', 'IgnoreTargets']
    assert micro[0].attrib == {'PowerType': 'RUSH_ATTACK', 'MinimumDelay': '0s',
                               'MaximumDelay': f'{maximum}s'}
    assert not any(s.name in ('Test - control make', 'Test - control press') for s in t.scripts)


@pytest.mark.parametrize('maximum, second', [(0, 8), (999, 15000)])
def test_maximum_endpoint_is_consumed_after_first_success(maximum, second):
    """Deterministic upper endpoint, not an assertion about the game's RNG sample."""
    from benches.ai.tactics.scenes import aidelay_bench as aidelay_bench_tables
    aidelay_bench = aidelay_bench_tables()["shared"]
    mc, sp = simai.model()['micro'], simai.model()['specials']
    m = aidelay_bench.mission(maximum)
    data = mc.load_micro(texts=[a[1] for a in m.assets])['CNVMicroSpow']
    power = mc.load_unit_powers()['Command_JapanAntiInfantryInfantryBonzai']
    foe = sp.Thing((50, 0), frozenset({'INFANTRY'}))
    units = [mc.Unit(n, health=70, powers=[power], target=foe, weapon_range=150) for n in ('a', 'b')]
    manager = mc.MicroManager(data, rng=lambda lo, hi: hi, fire=lambda u, p: setattr(u, 'usable', False))
    for frame in range(1, second + 1):
        manager.tick(frame, mc.Team(units))
    assert [(f, n) for f, n, _ in manager.fired] == [(8, 'a'), (second, 'b')]

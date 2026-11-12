"""MaximumDelay pair: real probe data and the actual AI execution callback.

The bodies' status is read directly, and the script counters (PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS,
counted by Sim.cond since A round 164) are replayed against the bench.
"""
import collections
import xml.etree.ElementTree as ET
import pytest

from test_simai_bench_b import lib, _probe_run, pytestmark  # noqa: F401
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
    from missions import aidelay_bench
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


@pytest.mark.parametrize('build', ['aidelay0', 'aidelay999'])
def test_specific_maximum_delay_probe_trace(lib, build, monkeypatch):
    observed = []
    original = simai.Brain.fire_unit

    def fire(brain, ai, key, unit, info):
        original(brain, ai, key, unit, info)
        bodies = [b for b in brain.sim.living() if b.owner == brain.player]
        charged = [b for b in bodies if 'WEAPON_UPGRADED_02' in b.status]
        observed.append((brain.frame, key, unit.name, len(charged)))

    monkeypatch.setattr(simai.Brain, 'fire_unit', fire)
    world, rows = _probe_run(build, lib, 50)
    (brain,) = world.brains.values()
    rush = [e for e in brain.fired if 'Bonzai' in e[3]]
    peak = max(e[3] for e in observed)
    print(build, 'rush records', rush[:6], 'peak charge', peak,
          'first seen clock', max(r['曾冲'] for r in rows))
    assert rush, 'successful positive control required before interpreting delay'
    assert peak == (1 if build == 'aidelay999' else 2)
    by_unit = collections.defaultdict(list)
    for frame, _, name, _ in rush:
        by_unit[name].append(frame)
    assert all(b - a >= 450 for frames in by_unit.values() for a, b in zip(frames, frames[1:]))
    if build == 'aidelay999':
        by_team = collections.defaultdict(list)
        for frame, key, _, _ in rush:
            by_team[key].append(frame)
        assert all(len(v) == 1 for v in by_team.values()), by_team


@pytest.mark.parametrize('build, peak', [('aidelay0', 2), ('aidelay999', 1)])
def test_maximum_delay_replays_bench_script_counters(lib, build, peak):
    """engine_aidelay pair bench 2026-11-11: the script counters 冲 peak 2 / 1 and 曾冲 is set (Sim.cond counts
    PLAYER_HAS_NUMBER_OBJECTS_WITH_OBJECT_STATUS since A round 164)."""
    _, rows = _probe_run(build, lib, 50)
    assert max(r['冲'] for r in rows) == peak
    assert max(r['曾冲'] for r in rows) > 0


@pytest.mark.parametrize('build', ['aidelay0', 'aidelay999'])
@pytest.mark.xfail(strict=True, reason='engine_aidelay both builds: bench Frames - Ever = 362 '
    'in 24 positive samples each; current replay gives 270 (92 frames early). '
    'Do not change B target/movement or fit MaximumDelay to this offset; '
    'evidence and hypotheses: work/re/c_delay_clock_report.md; work/re/handoff-c.md.')
def test_maximum_delay_first_seen_clock_replays_bench(lib, build):
    """engine_aidelay a: wake-relative Frames - Ever is 362, not wall seconds.

    Recorded script samples (wall second, Frames, Ever): both (33, 373, 11),
    zero (42, 508, 146), long (42, 504, 142). Ever is a latched clock,
    including after charging stops. This dates script observation, not the
    engine's internal ability dispatch. Raw evidence: work/re/c_delay_pair_1111_readings.json.
    """
    world, rows = _probe_run(build, lib, 50)
    samples = [(t, r['帧数'], r['曾冲'])
               for (t, _), r in zip(world.sim.series, rows) if r['曾冲'] > 0]
    assert samples, 'the script must actually observe a charge'
    clocks = {frames - ever for _, frames, ever in samples}
    print(build, 'mission-clock/Frames/Ever samples', samples[:2], samples[-2:],
          'wake-relative first-seen clocks', sorted(clocks))
    assert clocks == {362}

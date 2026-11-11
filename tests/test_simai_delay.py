"""MaximumDelay pair: real probe data and the actual AI execution callback.

Read body status directly: the inherited player-status script condition is
currently unmodeled, so its zero counters cannot prove execution failure.
"""
import collections
import pytest

from test_simai_bench_b import lib, _probe_run, pytestmark  # noqa: F401
from test_simai_bench_b import simai


@pytest.mark.parametrize('maximum, second', [(0, 8), (999, 15000)])
def test_maximum_endpoint_is_consumed_after_first_success(maximum, second):
    """Deterministic upper endpoint, not an assertion about the game's RNG sample."""
    from checks import engine_aidelay
    mc, sp = simai.model()['micro'], simai.model()['specials']
    m = engine_aidelay.mission(maximum)
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

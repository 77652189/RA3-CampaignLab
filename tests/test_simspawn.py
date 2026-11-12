"""SpawnBehavior lifecycle replay, deliberately excluding drone repair and slaving."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('spawn_simbench', ROOT / 'experimental/cnv/simbench.py')
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_spawn_initial_burst_and_parent_kill_delete_match_named_bench():
    """engine_spawn:spawn: 9/333 initially, 3/3 after parent kill and deletion."""
    import build
    import sim
    m, t, _ = build.resolve('engine_spawn', 'spawn')
    e = sim.Sim(m, t)
    rows = e.run(24).series
    for first, last, expected in ((2, 9, (9, 333)), (16, 23, (3, 3))):
        got = [tuple(v[:2]) for at, v in rows if first <= at < last]
        assert got and all(v == expected for v in got), (expected, got)
    for role in ('kill', 'delete', 'keep'):
        parent = e.body(m.role(role + ' factory').name)
        assert len(parent.spawned_children) == 3
        assert all(c.owner == parent.owner for c in parent.spawned_children)
        assert all(c.alive == (role == 'keep') for c in parent.spawned_children)
    assert ('SpawnBehavior', 'AlliedWarFactory') in e.unmodeled
    # A factory built during play has an unmeasured unpack gate; do not silently spawn early.
    built = e.add('late factory', 'AlliedWarFactory', parent.owner, 100, 100, by='builder', at=24)
    assert not built.spawned_children


def test_spawn_unmeasured_flags_and_subtrees_do_not_generate_children():
    import simunits
    xml = simunits._xml('AlliedWarFactory')
    assert list(simunits.spawn_modules('AlliedWarFactory').values()) == ['AlliedWarFactoryRepairDrone']
    for changed in (xml.replace('InitialBurst="3"', 'InitialBurst="1"'),
                    xml.replace('SpawnedRequireSpawner="true"', 'SpawnedRequireSpawner="false"'),
                    xml.replace('<SpawnTemplate>AlliedWarFactoryRepairDrone</SpawnTemplate>',
                                '<SpawnTemplate>AlliedAirfieldRepairDrone</SpawnTemplate>'),
                    xml.replace('DeathTypes="ALL"', 'DeathTypes="NORMAL"')):
        assert list(simunits.spawn_modules('AlliedWarFactory', {'AlliedWarFactory': changed}).values()) == [None]


def test_spawn_refill_two_independent_deaths_match_named_bench_with_position_precondition():
    """engine_spawn_refill:refill, isolated from unmodeled AttachUpdate/SlavedUpdate flight.

    Place one initial drone at each repair target before replay; the named recipe's real
    MiG death weapons must cause the deaths. Never inject death times or count offsets.
    """
    import build
    import sim
    m, t, _ = build.resolve('engine_spawn_refill', 'refill')
    e = sim.Sim(m, t)
    parent = e.body(m.role('keep factory').name)
    first = list(parent.spawned_children)
    for child, role in zip(first, ('north', 'west')):
        target = e.body(m.role(role).name)
        child.x, child.y = target.x, target.y
    rows = e.run(30).series
    for start, end, expected in ((2, 5, 3), (9, 9, 2), (12, 15, 1), (19, 19, 2), (24, 29, 3)):
        got = [v[0] for at, v in rows if start <= at <= end]
        assert got and all(v == expected for v in got), (expected, got)
    changes = []
    for at, values in rows:
        if not changes or values[0] != changes[-1][1]:
            changes.append((at, values[0]))
    assert [count for _, count in changes] == [3, 2, 1, 2, 3]
    # New bench: s7/s10 deaths, s17/s20 refill. Compare elapsed time, since the
    # bench's whole-second sampling origin differs from the simulator's.
    for dead, refill in ((1, 3), (2, 4)):
        assert abs(changes[refill][0] - changes[dead][0] - 10) <= 1
    assert all(not c.alive and not c.deleted for c in first[:2])
    assert first[2].alive
    assert len(parent.spawned_children) == 5
    assert sum(c.alive for c in parent.spawned_children) == 3
    assert all(c.spawn_parent is parent and c.owner == parent.owner for c in parent.spawned_children)


def test_spawn_refill_tracks_actual_death_frame_and_parent_removal_cancels_pending():
    import build
    import sim
    for delete in (False, True):
        m, t, _ = build.resolve('engine_spawn_refill', 'refill')
        e = sim.Sim(m, t)
        parent = e.body(m.role('keep factory').name)
        e.advance(45)  # arbitrary death time, unrelated to recipe's explosion timers
        child = parent.spawned_children[0]
        died = e.frame_now()
        e.destroy(child, 'test death')
        e.destroy(child, 'duplicate notification')
        assert len(parent.spawn_refills) == 1
        e.spawn_due(died + 149)
        assert sum(c.alive for c in parent.spawned_children) == 2
        e.spawn_due(died + 150)
        assert sum(c.alive for c in parent.spawned_children) == 3
        e.destroy(parent.spawned_children[-1], 'replacement death')
        assert len(parent.spawn_refills) == 1
        e.destroy(parent, 'parent removed', delete=delete)
        assert not parent.spawn_refills
        e.spawn_due(died + 1000)
        assert len(parent.spawned_children) == 4
        assert not any(c.alive for c in parent.spawned_children)


def test_spawn_power_outage_and_recovery_match_named_bench():
    """engine_spawn_power:power; use real supply/demand and the recipe's plant lifecycle."""
    import build
    import sim
    m, t, _ = build.resolve('engine_spawn_power', 'power')
    e = sim.Sim(m, t)
    assert e.power(m.player('p1')) == (100, 50)
    rows = e.run(60).series
    for start, end, expected in ((2, 8, (3, 3, 101)), (16, 28, (3, 3, 12)),
                                 (42, 59, (3, 3, 101))):
        got = [tuple(v[:3]) for at, v in rows if start <= at <= end]
        assert got and all(v == expected for v in got), (expected, got)
    # Bench counts stay at 3 through BOTH transitions, not just at the endpoints.
    assert all(v[:2] == [3, 3] for at, v in rows if at >= 2)
    assert all(v[3] == 0 for at, v in rows if 2 <= at < 28)
    assert all(v[3] >= 100 for at, v in rows if at >= 42)
    # Implementation guard: identity was not observable on the bench. Keeping the
    # original children is the minimal interpretation of its unchanged counts.
    parent = e.body(m.role('factory').name)
    assert len(parent.spawned_children) == 3
    assert all(c.alive for c in parent.spawned_children)
    assert not parent.spawn_refills
    assert e.power(m.player('p1')) == (100, 50)


def test_unpack_spawn_reads_each_refinery_s_one_collector_and_nothing_else():
    """SpawnOnUnpack (round 177): the three refineries' one-shot collector; the war factory's drones are not it, and a
    changed attribute is not it either (stays spawn_modules' gap)."""
    import simunits
    assert simunits.unpack_spawn('AlliedRefinery') == {'ModuleTag_Spawn': 'AlliedMiner'}
    assert simunits.unpack_spawn('SovietRefinery') == {'ModuleTag_Spawn': 'SovietMiner'}
    assert simunits.unpack_spawn('JapanRefinery') == {'ModuleTag_Spawn': 'JapanMiner'}
    assert simunits.unpack_spawn('AlliedWarFactory') == {}
    xml = simunits._xml('AlliedRefinery')
    changed = xml.replace('IsOneShotData="true"', 'IsOneShotData="false"')
    assert changed != xml and simunits.unpack_spawn('AlliedRefinery', {'AlliedRefinery': changed}) == {}


def test_a_placed_refinery_gives_its_collector_a_built_one_does_not():
    """Placed by the map: its collector at the start, on its spot, outliving it; built (by=...): a gap, none made
    (simai gives the AI's its own)."""
    import build
    import sim
    m, t, _ = build.resolve('mineniag', 'p')
    e = sim.Sim(m, t)
    ref = e.body(m.role('refinery').name)
    own = [b for b in e.bodies.values() if b.unpack_parent is ref]
    assert len(own) == 1 and own[0].template == 'AlliedMiner' and own[0].owner == ref.owner
    assert (own[0].x, own[0].y) == (ref.x, ref.y)
    e.destroy(ref, 'test')
    assert own[0].alive
    late = e.add('late refinery', 'AlliedRefinery', ref.owner, 100, 100, by='builder', at=1.0)
    assert not [b for b in e.bodies.values() if b.unpack_parent is late]

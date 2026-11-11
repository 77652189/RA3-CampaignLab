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

"""Regression tests for the snapshot family's closing review."""
import argparse
import gzip

import pytest

from test_plans import small  # noqa: F401,I001  (puts experimental/cnv on the path)
import build  # noqa: E402
import sim  # noqa: E402
import simai  # noqa: E402
import simaisnap  # noqa: E402
import simbench_peak  # noqa: E402
import simrecord  # noqa: E402
import simsmall  # noqa: E402
import simsnap  # noqa: E402
import snapfile  # noqa: E402
from engine.kernel import snap  # noqa: E402
from engine.ports.command import Command  # noqa: E402
from missions import aipeak_bench  # noqa: E402


@pytest.fixture
def ai_model():
    if not simai.available():
        pytest.skip('the engine model (ra3model.ai) is not on this computer')


@pytest.mark.parametrize('reference', ['returner', 'wrapper'])
def test_missing_ai_serial_is_refused_before_restore(reference, ai_model):
    mission, check, _ = build.resolve('aipeak', '')
    run = simai.SimAI(sim.Sim(mission, check, model=False)).advance(1)
    brain = next(iter(run.brains.values()))
    facility = next(b for b in run.sim.bodies.values() if b.owner == brain.player)
    unit = run.sim.add('test unit', 'AlliedAntiInfantryInfantry', brain.player, facility.x + 100, facility.y)
    brain.units(brain.ai, run.frame)
    unit.path = [(1.0, 2.0)]
    run.pullback.returning[unit.serial] = (facility, unit.move_to, unit.owner, unit.path)
    taken = simaisnap.snapshot(run)
    missing = run.sim.world.made
    if reference == 'returner':
        dict(taken['ai'])['pullback.returning']['$items'][0][0] = missing
    else:
        taken['brains'][0][3]['wrappers'][0][1] = missing

    fresh = simai.SimAI(sim.Sim(mission, check, model=False))
    before = simaisnap.snapshot(fresh)
    with pytest.raises(ValueError, match=rf'things \[{missing}\] are held but not kept'):
        simaisnap.restore(fresh, taken)
    assert simaisnap.snapshot(fresh) == before


def test_resume_refuses_an_unrelated_record(tmp_path):
    record = tmp_path / 'record.gz'
    snapshot = tmp_path / 'cut.gz'
    args = argparse.Namespace(cmd='one', name='heal_a', path=str(record), executor=None, snap='0.5',
                              save=str(snapshot), resume=None)
    simrecord._main(args)
    with gzip.open(record, 'rt', encoding='utf-8') as source:
        *earlier, last = source.readlines()
    with gzip.open(record, 'wt', encoding='utf-8') as out:
        out.writelines(earlier)
    with gzip.open(record, 'at', encoding='utf-8') as out:
        out.write(last.rsplit(' || ', 1)[0] + ' || unrelated prefix\n')
    before = record.read_bytes()
    args.save, args.resume = None, str(snapshot)
    with pytest.raises(ValueError, match='first half'):
        simrecord._main(args)
    assert record.read_bytes() == before


@pytest.mark.parametrize('explicit_path', [False, True])
def test_ai_start_follows_resolved_mission_content(tmp_path, monkeypatch, explicit_path, ai_model):
    monkeypatch.setattr(snapfile, 'cache_dir', lambda: str(tmp_path))
    path = str(tmp_path / 'start.json.gz') if explicit_path else None
    first, start = simbench_peak.ai_start(0.0, path=path)
    yard = 'UNIT - CNV Peak Yard 1'
    old = first.sim.bodies[yard]
    _, reused = simbench_peak.ai_start(0.0, path=path)
    assert not reused['taken'] and reused['sha'] == start['sha']

    monkeypatch.setitem(aipeak_bench.BASES, 's1', ('east base', 'CNV Peak Base 1'))
    mission, _, _ = build.resolve('aipeak', '')
    expected = mission.find(yard)
    assert (expected.x, expected.y) != (old.x, old.y)
    fresh, refreshed = simbench_peak.ai_start(0.0, path=path)
    body = fresh.sim.bodies[yard]
    assert (body.x, body.y) == (expected.x, expected.y)
    assert refreshed['taken'] and refreshed['sha'] != start['sha']
    assert (refreshed['file'] == start['file']) == explicit_path


@pytest.mark.parametrize('codec', ['kernel', 'ai'])
def test_old_file_is_refused_after_an_existing_encoding_rule_changes(tmp_path, monkeypatch, codec):
    world = simsmall.small_world(
        [(name, 'AlliedAntiInfantryInfantry', 'Player_1', x, 2350)
         for name, x in [('probe', 2000), ('decoy', 2050)]], model=False)
    assert world.commands.post(Command('move', units=('probe',), place='@850,650'), 0) == (True, '')
    root = simai.SimAI(world)
    saved = tmp_path / 'snapshot.gz'
    snapfile.save(saved, simaisnap.snapshot(root))
    host_version, ai_version = simsnap.version(), simaisnap.version()
    if codec == 'kernel':
        encode = snap.encode

        def renamed_tuple(value, *args, **kwargs):
            if type(value) is tuple and value == ('probe',):
                value = ('decoy',)
            return encode(value, *args, **kwargs)

        monkeypatch.setattr(snap, 'encode', renamed_tuple)
        assert snap.encode(('probe',)) == {'$tuple': ['decoy']}
    else:
        mark = simaisnap._mem_mark

        def reversed_memory(mem, run):
            result = mark(mem, run)
            return not result if result is not None else result

        monkeypatch.setattr(simaisnap, '_mem_mark', reversed_memory)
        assert simaisnap._mem_mark(object(), None) is True
    with pytest.raises(ValueError, match='taken in shape'):
        snapfile.load(saved)
    assert (simsnap.version() != host_version) == (codec == 'kernel')
    assert (simaisnap.version() != ai_version) == (codec == 'ai')


def test_snapshot_names_unclassified_kernel_world_fields():
    world = simsmall.small_world(model=False)
    before = simsnap.version()
    assert simsnap.unclassified(world) == []
    world.world.review_field = 9
    assert simsnap.unclassified(world) == ['sim.world.review_field']
    assert simsnap.version() == before

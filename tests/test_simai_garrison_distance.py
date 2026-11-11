"""Replay the recorded engine_aigarrison geometry, before its scenery relocation.

Only the retail 150 distance's near/far behavior is measured. Exact boundary,
other configured distances and entry/death timing remain unmeasured.
"""
from test_simai_bench_b import lib, _probe_run, pytestmark, simai  # noqa: F401


def test_garrison_distance_replays_recorded_near_far_and_disabled(lib, monkeypatch):
    """engine_aigarrison: aigar1 owns house, aigar0/aigarfar never do (11-09).

    Restore EAST=40: those readings precede the map's EAST=0 scenery fix.
    Assert ownership counters rather than inferring entry from survival alone.
    """
    from missions import aigarrison_bench

    monkeypatch.setattr(aigarrison_bench, 'EAST', 40.0)
    for build in ('aigar1', 'aigar0', 'aigarfar'):
        world, rows = _probe_run(build, lib, 75.0)
        assert rows
        owned = [r['楼归AI'] for r in rows]
        entries = [e for e in world.garrison.log if not e[3]]
        print(build, 'ownership_max/final', max(owned), owned[-1],
              'entries', len(entries), 'first_owned_row',
              next((i for i, v in enumerate(owned) if v), None))
        if build == 'aigar1':
            assert max(owned) == 1, (build, owned)
            assert owned[-1] == 1
            assert len(entries) >= 3, entries
        else:
            assert max(owned) == 0, (build, owned)
            assert entries == [], entries

    # Model sensitivity only, not an engine reading at distance 0: ensure the
    # integrated consumer actually reads this field instead of hardcoding 150.
    micro_data = simai.model()['tactics'].MicroData
    original_num = micro_data.num
    reads = []

    def zero_distance(data, name, key):
        value = original_num(data, name, key)
        if key == 'EnterGarrisonableStructureDistance':
            reads.append(value)
            return 0.0
        return value

    monkeypatch.setattr(micro_data, 'num', zero_distance)
    world, rows = _probe_run('aigar1', lib, 75.0)
    assert reads and set(reads) == {150.0}, reads
    assert all(r['楼归AI'] == 0 for r in rows)
    assert not [e for e in world.garrison.log if not e[3]]
    print('model_only_distance0', 'field_reads', len(reads), 'ownership_max', 0)

"""QueueDockBehavior's rules the bench's counters cannot see (the collector loop: engine/objects/mine.py). Read on the
bench: checks/engine_queuedock.readings.toml (250 a trip, 8 a frame); D165's dock phases (work/re/e164_queuedock.md):
no QueueDock on the refinery faults the game at the first delivery, the cargo shows only when loading ends."""
import math

import pytest

from test_plans import small  # noqa: F401,I001  (tests/ is on the path by its conftest; puts experimental/cnv on it)
import engine.data.units as simunits  # noqa: E402
import engine.objects.mine as simmine  # noqa: E402
import engine.testing.small as simsmall  # noqa: E402


def _world():
    return simsmall.small_world([('ref', 'AlliedRefinery', 'Player_1', 0.0, 0.0),
                                 ('node', 'OreNode', 'PlyrCivilian', 300.0, 0.0),
                                 ('miner', 'AlliedMiner', 'Player_1', 150.0, 60.0)])


def test_presence_follows_the_parent_and_not_a_comment():
    own = {'DockParent': '<GameObject id="DockParent"><Behaviors>'
           '<QueueDockBehavior id="dock"/></Behaviors></GameObject>',
           'DockChild': '<GameObject id="DockChild" inheritFrom="DockParent"/>',
           'NoDock': '<GameObject id="NoDock"><!-- <QueueDockBehavior id="fake"/> --></GameObject>'}
    assert simunits.queue_dock('DockChild', own)
    assert not simunits.queue_dock('NoDock', own)


def test_a_refinery_without_it_is_refused_before_any_payment(monkeypatch):
    s, paid = _world(), []
    monkeypatch.setattr(simmine.simunits, 'queue_dock', lambda template, own=None: False)
    mining = simmine.Mining()
    with pytest.raises(ValueError, match="QueueDock missing on refinery 'ref' selected by miner 'miner'"):
        for frame in range(1, 900):
            mining.mine_due(s, frame, lambda owner, give: paid.append(give))
    m = s.bodies['miner'].mine
    assert (m['state'], m['load'], paid) == ('find refinery', 250, [])


def test_the_front_node_miner_goes_direct_and_one_finding_the_pads_held_queues():
    """E207 / D187: the front node's miner unloads beside the side node's; one off its node while the other is on the
    pads waits till they are free (its unload + 30 + 14), then drives in by pad 0 and pad 1 (+ 18 + 22)."""
    s = simsmall.small_world([('ref', 'AlliedRefinery', 'Player_1', 0.0, 0.0),
                              ('n1', 'OreNode', 'PlyrCivilian', 180.0, 0.0),
                              ('n2', 'OreNode', 'PlyrCivilian', 0.0, 300.0),
                              ('m1', 'AlliedMiner', 'Player_1', 180.0, 0.0),
                              ('m2', 'AlliedMiner', 'Player_1', 0.0, 300.0)])
    s.bodies['n1'].angle, s.bodies['n2'].angle = math.pi, -math.pi / 2       # facing the refinery
    mining, last, unloads, queued = simmine.Mining(), {}, {'m1': [], 'm2': []}, []
    for frame in range(1, 640):
        mining.mine_due(s, frame, lambda owner, give: None)
        for n in unloads:
            st = s.bodies[n].mine['state']
            if st != last.get(n):
                unloads[n] += [frame] if st == 'unloading' else []
                queued += [(n, frame)] if st == 'to pad' and frame < mining.docks.get(s.bodies['ref'].serial, 0) else []
                last[n] = st
    assert 0 < unloads['m1'][0] - unloads['m2'][0] < 30                       # beside it
    assert queued == [('m1', 576)] and unloads['m1'][-1] == unloads['m2'][-1] + 30 + 14 + 18 + 22


def test_the_cargo_shows_only_when_loading_ends():
    s, seen = _world(), []
    mining = simmine.Mining()
    for frame in range(1, 900):
        mining.mine_due(s, frame, lambda owner, give: None)
        m = s.bodies['miner'].mine
        seen.append((m['state'], m['load']))
        if m['state'] == 'find refinery':
            break
    assert any(st == 'loading' for st, _ in seen)
    assert all(load == 0 for st, load in seen if st in ('docked', 'loading'))
    assert seen[-1] == ('find refinery', 250) and 'pending_load' not in m

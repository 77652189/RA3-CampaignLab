"""L6 script actions on what a side sees (ADR 0029, docs/engine/sim-layers.md; the L3 visibility state): map reveals.

Each action is `fn(sim, name, a, script)`, moved verbatim out of Sim.act's chain; simact.act looks them up in ACTIONS.
They still reach the Sim directly (sim.reveals, sim.peeks, ...): the reveal state moves to L3 with visibility, and
these then call its interface."""
from simworld import GAP_ACTION


def map_reveal_all(sim, name, a, script):
    # Bench 11-10 engine_vision all / allundo (docs/engine/vision.md 2): MAP_REVEAL_ALL lapses as a waypoint
    # reveal does (137 frames by default, 15 x N - 13); _PERM holds until MAP_REVEAL_ALL_UNDO_PERM, which
    # shuts it the frame it runs (no reshroud delay). Another side's: kept for good (INFERRED, not benched)
    if a and a[0] != sim.human and a[0] in sim.players.values():   # another side's: its own sight
        sim.revealed_to.add(a[0])
    elif name == 'MAP_REVEAL_ALL':
        hold = max(0, int(round(sim.reshroud * 15)) - 13)
        sim.reveal_all_until = max(sim.reveal_all_until, sim.frame_now() + hold)
        sim.note('揭图', '全图（暂时）')
    else:
        sim.reveal_all = True
        sim.note('揭图', '全图')


def map_reveal_all_undo_perm(sim, name, a, script):
    if a and a[0] != sim.human and a[0] in sim.players.values():
        sim.revealed_to.discard(a[0])
    else:
        sim.reveal_all = False
        sim.note('揭图', '全图收回')


def map_reveal_permanently_at_waypoint(sim, name, a, script):
    p = sim.point(a[0])
    if p:
        if name == 'MAP_REVEAL_AT_WAYPOINT':
            # docs/engine/vision.md 2 (bench 11-06 engine_vision resh*): it holds 15 x N - 13 frames
            hold = max(0, int(round(sim.reshroud * 15)) - 13)
            sim.peeks.append((p[0], p[1], float(a[1]), sim.frame_now() + hold))
        else:
            sim.reveals[a[3]] = (p[0], p[1], float(a[1]))
        sim.note('揭图', f'{a[0]} 半径 {a[1]:g}')


def map_undo_reveal_permanently_at_waypoint(sim, name, a, script):
    # bench 11-09 engine_vision undo: back to fog at once (no reshroud delay), by the reveal's name
    sim.reveals.pop(a[0], None)


def map_reveal_permanently_in_trigger(sim, name, a, script):
    # (area, player, reveal name) INFERRED as the waypoint one: the area open to the player till the undo;
    # another side's not simulated (its sight)
    if a[1] == sim.human:
        sim.reveal_areas[a[2]] = a[0]
        sim.note('揭图', f'{a[0]}（区域）')
    else:
        sim.gap(GAP_ACTION, name, '给其他玩家揭区域不模拟')


def map_undo_reveal_permanently_in_trigger(sim, name, a, script):
    # (reveal name) INFERRED: back to fog at once
    sim.reveal_areas.pop(a[0], None)


ACTIONS = {
    'MAP_REVEAL_ALL': map_reveal_all,
    'MAP_REVEAL_ALL_PERM': map_reveal_all,
    'MAP_REVEAL_ALL_UNDO_PERM': map_reveal_all_undo_perm,
    'MAP_REVEAL_PERMANENTLY_AT_WAYPOINT': map_reveal_permanently_at_waypoint,
    'MAP_REVEAL_AT_WAYPOINT': map_reveal_permanently_at_waypoint,
    'MAP_UNDO_REVEAL_PERMANENTLY_AT_WAYPOINT': map_undo_reveal_permanently_at_waypoint,
    'MAP_REVEAL_PERMANENTLY_IN_TRIGGER': map_reveal_permanently_in_trigger,
    'MAP_UNDO_REVEAL_PERMANENTLY_IN_TRIGGER': map_undo_reveal_permanently_in_trigger,
}

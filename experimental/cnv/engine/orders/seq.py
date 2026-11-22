"""L5 UNIT_EXECUTE_SEQUENTIAL_SCRIPT (ADR 0029): each unit's queue of sequential scripts moves one step a frame once
the unit is idle -- apart from engine.orders.order. Over the world (WORLD_API only); the host by simorder.Peers
(PEERS): the queue lives on it (Sim.seq, the scripts' records, written here alone: the script actions call queue /
stop)."""

from engine.world.handle import same_team

PEERS = frozenset({'seq', 'garrison'})


def _of_team(r, team):
    """r is the team's record: one name bare, the other 'player/team', either way round (same_team; 1122uu #5)."""
    return r['b'] is None and (same_team(r['team'], team) or same_team(team, r['team']))


def queue(seq, b, script, loops, team=None, group=()):
    """UNIT_EXECUTE_SEQUENTIAL_SCRIPT: `script` behind the unit's others, a subroutine now; `loops` runs more.
    TEAM_EXECUTE_SEQUENTIAL_SCRIPT: b None, behind the team's others, `group` its members at the call (d115 14)."""
    script.subroutine = True
    seq.append({'b': b, 'team': team, 'group': list(group), 'script': script, 'step': -1, 'loops': loops})


def stop(seq, b, team=None):
    """UNIT_STOP_SEQUENTIAL_SCRIPT (engine_seqstop:a): the unit's scripts go (a move a step gave goes on); with
    `team` (b None) TEAM_STOP_SEQUENTIAL_SCRIPT: the team's (engine_seqteam:t)."""
    seq[:] = [r for r in seq if r['b'] is not b or (team is not None and not _of_team(r, team))]


def wait(seq, frames, b=None, team=None):
    """IDLE_FOR_* on the unit `b` / the team (TEAM_GUARD_FOR_SECONDS too): its first record waits `frames` frames
    before the next step (d115 14 step 2, l2_scripts1 3); no record, nothing written. engine_seqguard:g: from the step
    before to the step after, exactly the count (90 / 90 / 75 frames), the two steps' own frames inside it (INFERRED
    why: not read) -- so 2 fewer frames skipped."""
    r = next((r for r in seq if r['b'] is b and (b is not None or _of_team(r, team))), None)
    if r is not None:
        r['wait'] = frames - 2


def _key(r):
    return r['team'] if r['b'] is None else r['b'].serial


def idle(peers, b):
    """The unit's AI has nothing to do (a sequential script's next step waits for it, d115 14): no way to walk,
    no living target, no path, not turning to a facing (engine_seqguard:g: a half turn holds the next step 8 frames),
    not firing at the ground, not running off."""
    return not b.path and b.face is None and not (isinstance(b.goal, type(b)) and b.goal.alive) and not b.follow \
        and not getattr(b, 'ground_fire', None) and not getattr(b, 'flee', None) \
        and b.serial not in peers.garrison.going


def seq_due(world, peers):
    """UNIT_EXECUTE_SEQUENTIAL_SCRIPT's frame (d115 14, the engine's "Advancing SeqScript"): of each unit's queue
    only the head moves -- the unit idle, its next action run (with <This Object> = the unit); past the last one
    it is done (loops 0), or goes to the back of the unit's queue to run again (loops - 1; -1 for ever). A dead
    unit's records go. Bench 11-13 engine_acts_seq: 跑 1 -> 11 at P -> 111 back and no more (one run, each step
    after the move before it), 排 0 -> 11 (the second script after the first's move). A record's wait (`wait`) counts
    down first, the unit not asked (d115 14 step 2; engine_seqguard:g; engine_acts2's 等 never waited: its 5.0 read
    as 0)."""
    heads, firsts = set(), []               # each unit's first record, picked before any step (review ll #2: not
    for r in peers.seq:                     # a scan of the queue for every record behind it)
        if _key(r) not in heads:
            heads.add(_key(r))
            firsts.append(r)
    for r in firsts:
        if all(x is not r for x in peers.seq):
            continue                        # stopped this frame by another unit's step (review kk #1)
        b = r['b']
        group = [b] if b is not None else [x for x in r['group'] if x.alive]
        if not all(x.alive for x in group) or not group:
            peers.seq.remove(r)             # the unit dead, the team's group empty (d115 14)
            continue
        if r.get('wait', 0) > 0:
            r['wait'] -= 1
            continue
        if not all(idle(peers, x) for x in group):
            continue                        # a team's: every living member of its group idle (INFERRED)
        r['step'] += 1
        acts = [x for x in r['script'].actions if x.enabled]
        if r['step'] >= len(acts):
            peers.seq.remove(r)
            if r['loops']:
                r['loops'] -= r['loops'] != -1
                r['step'] = -1
                peers.seq.append(r)
            continue
        act = acts[r['step']]
        if b is None:
            world.executor.action(act.name, [r['team'] if x == '<This Team>' else x for x in act.args], r['script'])
            continue
        args = [b.name if x == '<This Object>' else (b.team if x == '<This Team>' else x) for x in act.args]
        if '<This Object>' in act.args:
            written = {}                    # the unit's name written as well: that one reads as written -- the
            if b.name in act.args and world.body(b.name) is not None:   # reference or the object of that name, not
                tok = b.name + AS_WRITTEN                               # the unit (same-name audit 11-19b O19)
                written[tok] = world.body(b.name)
                args = [tok if x == b.name else y for x, y in zip(act.args, args)]
            _as_itself(world, b, lambda: world.executor.action(act.name, args, r['script']), written)
        else:
            world.executor.action(act.name, args, r['script'])
        if not b.alive and r in peers.seq:
            peers.seq.remove(r)


_NONE = object()
# the suffix of a sequential step's token for the unit's name written as well as <This Object> (O19): the token reads
# as the object the name read before the step; a place by the name (Sim.point: waypoint, area, mark, site) is read by
# the name itself, before any object, as without the token (review 11-19 w P2 #2)
AS_WRITTEN = ' <as written>'


def _as_itself(world, b, step, written=()):
    """Run `step` (a sequential script's action, <This Object> written as `b`'s name) with that name reading as `b`
    itself: a reference of the same name, or another object made under it since, cannot take the unit's place
    (same-name audit 11-19, S5). For the step's length the name is in world.acting, which world.body and world.point
    read before the references (every action finds its object by name through them, either executor); the
    references are not written, so one the step points at the name itself stays (review 11-19 n P3 #3; #4: a point
    by the name is the unit's). Only a step written with <This Object> runs here (the caller; #2). Arguments and the
    log's text unchanged. A step writing both <This Object> and the unit's name gives the written one as a token of
    its own in `written` (token -> what the name read before the step: O19), in world.acting for the step too."""
    had = {k: world.acting.get(k, _NONE) for k in (b.name, *written)}
    world.acting[b.name] = b
    world.acting.update(written)
    try:
        step()
    finally:
        for k, v in had.items():
            if v is _NONE:
                world.acting.pop(k, None)
            else:
                world.acting[k] = v

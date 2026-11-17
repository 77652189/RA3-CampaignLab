"""E148: three VISION_UNITS filters and blocked port VISION, one map.

E149 prerequisite repair: valid AIRCRAFT/SHIP markers and port near point at
500 within inherited 600 vision. Before entry, an extra 200000 means all seven
lane objects are alive with their declared owner/template at their placed
locations, and all three discovery controls are hidden. This bit ends at entry.
PAUSED after E149: only air passed; infantry/ship identity gates failed and
port match was already discovered before entry. No effect coverage is claimed.
See work/re/e149_infiltrator.md and handoff-e.md before another run.

E150 variant b is an unrun prerequisite diagnostic, not effect coverage. Each
row independently publishes the 25 original conditions as a binary pass mask:
bit 0 = before Entry; bits 1..21 = alive/owner/template-in-40 for host,
friendly host, spy, friendly spy, match, wrong, third (in that order);
bits 22..24 = match/wrong/third hidden. All pass = 33554431. A missing
bit identifies the failed predicate without changing its radius or threshold.
The original aggregate readings cannot reconstruct these bits retroactively.
Port second is outside the original 25 predicates. See work/re/e150_infbatch.md.

Prediction before bench: enemy spies consumed, friendly spies refused, owners
unchanged. Existing matching same-owner units may be revealed (INFERRED);
wrong-kind and third-owner controls stay hidden for VISION_UNITS. Port local
VISION may also expose nearby third-owner units. No continuous window or exact
observer clock is assumed. Port second entry at 25s should be blocked.
Each row encodes enemy spy=1, friendly spy=10, unchanged owner=100,
matching discovery=1000, wrong kind/far discovery=10000, third owner=100000;
port second spy alive=1000000. Raw observations: work/re/e149_infiltrator.md.
"""
from parts import NOT, Script, Test, square


def prerequisites(m, t, lane):
    """The original gate, in the documented diagnostic bit order."""
    roles = [lane, lane + ' friend', lane + ' spy', lane + ' friend spy',
             lane + ' match', lane + ' wrong', lane + ' third']
    conditions = [('TIMER_EXPIRED', 'Entry', NOT)]
    for role in roles:
        obj = m.role(role)
        area = 'Test identity ' + role
        t.areas[area] = square(*m.point(role), 40)
        conditions += [
            ('NAMED_NOT_DESTROYED', obj.name),
            ('NAMED_OWNED_BY_PLAYER', m.player(obj.side), obj.name),
            ('PLAYER_HAS_COMPARISON_UNIT_TYPE_IN_TRIGGER_AREA',
             m.player(obj.side), 3, 1, obj.template, area)]
    conditions += [('NAMED_DISCOVERED', m.player('p1'), m.role(lane + ' ' + role).name, NOT)
                   for role in ('match', 'wrong', 'third')]
    return conditions


def check(m):
    t = Test()
    p, ally = m.player('p1'), m.player('s5')
    t.scripts = [Script('Test - start', [], [
        ('PLAYER_RELATES_PLAYER', p, ally, (2, 0.0, 'Friend')),
        ('PLAYER_RELATES_PLAYER', ally, p, (2, 0.0, 'Friend')),
        ('SET_MILLISECOND_TIMER', 'Entry', 10.0),
        ('SET_MILLISECOND_TIMER', 'Second', 25.0)] + [
        ('UNIT_CHANGE_OBJECT_STATUS', obj.name, 'NO_ATTACK', 1) for obj in m.objects])]
    t.scripts.append(Script('Test - enter', [('TIMER_EXPIRED', 'Entry')], [
        ('NAMED_GARRISON_SPECIFIC_BUILDING', m.role(lane + suffix + ' spy').name,
         m.role(lane + suffix).name)
        for lane in ('air', 'infantry', 'ship', 'port') for suffix in ('', ' friend')]))
    t.scripts.append(Script('Test - second', [('TIMER_EXPIRED', 'Second')], [
        ('NAMED_GARRISON_SPECIFIC_BUILDING', m.role('port second').name, m.role('port').name)]))
    for lane, side in (('air', 's1'), ('infantry', 's2'), ('ship', 's3'), ('port', 's4')):
        c = 'Infiltration ' + lane
        t.counters.append((c, lane))
        t.scripts.append(Script('Test - reset ' + lane, [], [('SET_COUNTER', c, 0)], once=False))
        conditions = [
            ('spy', ('NAMED_NOT_DESTROYED', m.role(lane + ' spy').name), 1),
            ('friend', ('NAMED_NOT_DESTROYED', m.role(lane + ' friend spy').name), 10),
            ('owner', ('NAMED_OWNED_BY_PLAYER', m.player(side), m.role(lane).name), 100)]
        conditions += [(role, ('NAMED_DISCOVERED', p, m.role(lane + ' ' + role).name), bit)
                       for role, bit in (('match', 1000), ('wrong', 10000), ('third', 100000))]
        if lane == 'port':
            conditions.append(('second', ('NAMED_NOT_DESTROYED', m.role('port second').name), 1000000))
        for label, cond, bit in conditions:
            t.scripts.append(Script('Test - ' + lane + label, [cond], [('INCREMENT_COUNTER', bit, c)], once=False))
        t.scripts.append(Script('Test - prerequisites ' + lane, prerequisites(m, t, lane),
                                [('INCREMENT_COUNTER', 200000, c)], once=False))
        baseline = 1200111 if lane == 'port' else 200111
        t.expect.append((lane, 1, '==', baseline, 7))
    t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=4))]
    return t


def diagnostic(m):
    """Publish independent predicates; no infiltration effect assertion."""
    t = check(m)
    # Keep the same setup and entry orders, without the old aggregate counters.
    t.scripts = t.scripts[:3]
    t.counters = []
    t.expect = []
    for lane in ('air', 'infantry', 'ship', 'port'):
        counter = 'Prerequisites ' + lane
        t.counters.append((counter, lane))
        t.scripts.append(Script('Test - reset bits ' + lane, [],
                                [('SET_COUNTER', counter, 0)], once=False))
        for bit, condition in enumerate(prerequisites(m, t, lane)):
            t.scripts.append(Script(f'Test - {lane} bit {bit}', [condition],
                                    [('INCREMENT_COUNTER', 1 << bit, counter)], once=False))
        t.expect.append((lane, 1, '==', 33554431, 7))
    t.bench = [('bench_watch', dict(seconds=8, every=1, sheet=False, lines=4))]
    return t


CHECKS = {'engine_infbatch': {'a': check, 'b': diagnostic}}

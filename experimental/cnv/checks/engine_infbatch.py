"""E148: three VISION_UNITS filters and blocked port VISION, one map.

PAUSED diagnostic: first run used nonexistent air/ship marker templates and
the port marker lies outside its inherited vision. Do not infer effect rules
or coverage from this scene. Correct these prerequisites in a new item before
another bench run. See work/re/e148_infiltrator.md and handoff-e.md.

Prediction before bench: enemy spies consumed, friendly spies refused, owners
unchanged. Existing matching same-owner units may be revealed (INFERRED);
wrong-kind and third-owner controls stay hidden for VISION_UNITS. Port local
VISION may also expose nearby third-owner units. No continuous window or exact
observer clock is assumed. Port second entry at 25s should be blocked.
Each row encodes enemy spy=1, friendly spy=10, unchanged owner=100,
matching discovery=1000, wrong kind/far discovery=10000, third owner=100000;
port second spy alive=1000000. Raw observations: work/re/e148_infiltrator.md.
"""
from parts import Script, Test


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
        baseline = 1000111 if lane == 'port' else 111
        t.expect.append((lane, 1, '==', baseline, 7))
    t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=4))]
    return t


CHECKS = {'engine_infbatch': {'a': check}}

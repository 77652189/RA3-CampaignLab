"""STEAL_MONEY: retail Amount=2000, BlockedDuration=30s, enemy-only spies.

Predict p1 1000 -> 3000, enemy 5000 -> 3000;
enemy spy consumed, full-health refinery retains owner; allied spy refused.
The refinery's income blocking, repeated entry and exact timing remain gaps.
E60 second run: cleanup below did not remove the spawned miners. No-miner
bits stayed zero: s1-s9 11100/11100/1000/5000; s10-s13
1100/11100/3000/3000; s18-s30 1100/11100/3000/3250;
s35+ 1100/11100/3000/3500. Predictions deliberately remain failing.
Paused after two engine runs; see work/re/e_infmoney_e60.md. The named replay
is strict xfail; this diagnostic is not evidence for implemented STEAL_MONEY.
"""
from parts import Script, Test, counted, kindof, square


def check(m):
    t = Test()
    p, ally = m.player('p1'), m.player('s2')
    t.scripts = [Script('Test - start', [], [
        ('MAP_REVEAL_ALL_PERM', p),
        ('PLAYER_RELATES_PLAYER', p, ally, (2, 0.0, 'Friend')),
        ('PLAYER_RELATES_PLAYER', ally, p, (2, 0.0, 'Friend')),
        ('PLAYER_SET_MONEY', p, 1000),
        ('PLAYER_SET_MONEY', m.player('s1'), 5000),
        ('PLAYER_SET_MONEY', ally, 5000),
        ('SET_MILLISECOND_TIMER', 'Money enter', 10.0)] + [
        ('UNIT_CHANGE_OBJECT_STATUS', m.role(role).name, 'NO_ATTACK', 1)
        for role in ('enemy', 'ally', 'enemy spy', 'ally spy')]),
        Script('Test - enter', [('TIMER_EXPIRED', 'Money enter')], [
            ('NAMED_GARRISON_SPECIFIC_BUILDING', m.role(role + ' spy').name, m.role(role).name)
            for role in ('enemy', 'ally')])]
    for role, side in (('enemy', 's1'), ('ally', 's2')):
        # Remove the refinery's unnamed spawned miner: isolate the transfer
        # from harvesting income without changing the retail refinery module.
        ref = 'UNITRef Money miner ' + role
        t.scripts.append(Script('Test - no miner ' + role, [], [
            ('SET_REF_TO_NEREST_TEAM_OF_UNNAMED_TYPE_OWNED_BY_PLAYER',
             'AlliedMiner', m.player(side), m.teams['Clean' + role], ref),
            ('NAMED_DELETE', ref)], once=False))
        c = 'Money ' + role
        counted(c, role, t, health=m.role(role).name)
        area = 'Money area ' + role
        t.areas[area] = square(*m.site(role + ' refinery'), 500)
        for label, cond, value in (
                ('no miners', ('PLAYER_HAS_COMPARISON_UNIT_KIND_IN_TRIGGER_AREA',
                               m.player(side), 2, 0, kindof('HARVESTER'), area), 100000),
                ('owner', ('NAMED_OWNED_BY_PLAYER', m.player(side), m.role(role).name), 1000),
                ('spy', ('NAMED_NOT_DESTROYED', m.role(role + ' spy').name), 10000)):
            t.scripts.append(Script('Test - ' + role + label, [cond],
                                    [('INCREMENT_COUNTER', value, c)], once=False))
    for side in ('p1', 's1'):
        c = 'Money balance ' + side
        t.counters.append((c, side + ' money'))
        t.scripts.append(Script('Test - balance ' + side, [], [
            ('SET_PLAYER_MONEY_TO_COUNTER', m.player(side), c)], once=False))
    t.expect = [('enemy', 2, '==', 111100, 7), ('enemy', 18, '==', 101100),
                ('ally', 2, '==', 111100), ('p1 money', 2, '==', 1000, 7),
                ('s1 money', 0, '==', 5000, 7),
                ('p1 money', 18, '==', 3000), ('s1 money', 18, '==', 3000)]
    t.bench = [('bench_watch', dict(seconds=35, every=1, sheet=False, lines=4))]
    return t


CHECKS = {'engine_infmon': {'a': check}}

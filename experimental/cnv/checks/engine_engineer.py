"""EngineerContain four routes, using ordinary scripted entry (not INSTANTLY).

Retail GenericEngineerContain admits the three engineers; RepairAlliesEngineerContain
adds Relationship=ALLIES. Predict neutral/enemy power plants captured, allied
half-health plant repaired without changing owner, hostile defence refused.
Each row = HP percent + 1000 if owned by p1 + 10000 if the engineer still lives.
Expected final rows: 1050 / 1050 / 100 / 10050. Capture preserves health.
Engineers start 180 south;
entry at mission second 10, so loading cannot swallow the baseline.
Check b: full-health allied plants, Allied/Soviet/Japan engineers in the first
three lanes; fourth lane is a half-health Allied-engineer repair control.
Prediction: 10100 / 10100 / 10100 / 100 after entry (baseline control 10050).
Retail admits all three templates but has no full-health rule; refusal and
survival are a hypothesis to measure, not a schema-derived fact.
Bench 2026-11-10 b PASS: s1-s11 10100/10100/10100/10050;
s12-s37 10100/10100/10100/100. Full-health engineers survive, all owners stay s2.
ReplaceWith/bridge repair and exact travel timing remain outside this slice;
these checks do not register the whole module as benched.

Bench 2026-11-10: first run explained capture preserving HP and background
computer-player repair (50->63 before capture; refused tower 50->100).
With s1/s2 credits held at zero: PASS, s1-s11 all 10050;
s12-s38 1050 / 1050 / 100 / 10050. Captures consume the engineers without
healing their targets; repair consumes its engineer and preserves the ally owner.
"""
from maps import probe_range
from parts import Mission, Script, Test, counted

LANES = ('neutral', 'enemy', 'ally', 'refused')


def mission():
    m = Mission(name='CampEngineer', map=probe_range, units=[])
    for role, lane, side, template in (
            ('neutral', 'base', 'neutral', 'AlliedPowerPlant'),
            ('enemy', 'high', 's1', 'AlliedPowerPlant'),
            ('ally', 'order', 's2', 'AlliedPowerPlant'),
            ('refused', 'removed', 's1', 'SovietBaseDefenseGround')):
        m.put(template, lane + ' gun', side=side, role=role, name='Engineer ' + role)
        m.put('AlliedEngineer', lane + ' gun', 0, -180, role=role + ' man', name='Man ' + role)
    return m


def check(m):
    t = Test()
    p, ally = m.player('p1'), m.player('s2')
    t.scripts = [Script('Test - start', [], [
        ('MAP_REVEAL_ALL_PERM', p),
        ('PLAYER_RELATES_PLAYER', p, ally, (2, 0.0, 'Friend')),
        ('PLAYER_RELATES_PLAYER', ally, p, (2, 0.0, 'Friend')),
        ('UNIT_CHANGE_OBJECT_STATUS', m.role('refused').name, 'NO_ATTACK', 1),
        ('SET_MILLISECOND_TIMER', 'Engineer enter', 10.0),
        *[('UNIT_SET_HEALTH', m.role(role).name, 50.0) for role in LANES]]),
        # The container's computer players repaired before entry in the first run:
        # power plants +~1 percent/s, turret +~1.6 percent/s. Remove their budget.
        Script('Test - no repair budget', [], [
            ('PLAYER_SET_MONEY', m.player(side), 0) for side in ('s1', 's2')], once=False),
        Script('Test - enter', [('TIMER_EXPIRED', 'Engineer enter')], [
            ('NAMED_GARRISON_SPECIFIC_BUILDING', m.role(role + ' man').name, m.role(role).name)
            for role in LANES])]
    for role in LANES:
        c, target, man = 'Eng ' + role, m.role(role).name, m.role(role + ' man').name
        counted(c, role, t, health=target)
        t.scripts += [
            Script('Test - owner ' + role, [('NAMED_OWNED_BY_PLAYER', p, target)],
                   [('INCREMENT_COUNTER', 1000, c)], once=False),
            Script('Test - alive ' + role, [('NAMED_NOT_DESTROYED', man)],
                   [('INCREMENT_COUNTER', 10000, c)], once=False)]
    t.expect = [(role, 30, '==', value, 34)
                for role, value in zip(LANES, (1050, 1050, 100, 10050))]
    t.bench = [('bench_watch', dict(seconds=36, every=1, sheet=False, lines=4))]
    return t


def check_full_health(m):
    """Three full-health allies plus a half-health positive control, ordinary entry."""
    for role, engineer in zip(LANES, ('AlliedEngineer', 'SovietEngineer',
                                      'JapanEngineer', 'AlliedEngineer')):
        target, man = m.role(role), m.role(role + ' man')
        target.template, target.side = 'AlliedPowerPlant', 's2'
        m.find(target.name).template, m.find(target.name).side = target.template, target.side
        man.template = engineer
        m.find(man.name).template = engineer
    t = check(m)
    t.scripts[0].do = [
        (a[0], a[1], 100.0) if a[0] == 'UNIT_SET_HEALTH'
        and a[1] != m.role('refused').name else a for a in t.scripts[0].do]
    t.expect = [(role, 30, '==', value, 34)
                for role, value in zip(LANES, (10100, 10100, 10100, 100))]
    return t


def check_damaged_allies(m):
    """c: Allied/Soviet/Japan repair half-health allies; full-health control.

    Retail GenericEngineerContain admits all three templates. Predict all three
    fill the allied plant without changing owner and are consumed; fourth lane
    repeats the measured full-health refusal. Exact travel timing is INFERRED.
    Baseline 10050/10050/10050/10100; expected final 100/100/100/10100.
    Bench 2026-11-10 PASS: s1-s11 baseline; s12-s38 expected final.
    """
    t = check_full_health(m)
    t.scripts[0].do = [
        (a[0], a[1], 100.0 if a[1] == m.role('refused').name else 50.0)
        if a[0] == 'UNIT_SET_HEALTH' else a for a in t.scripts[0].do]
    t.expect = [(role, 30, '==', value, 34)
                for role, value in zip(LANES, (100, 100, 100, 10100))]
    return t


MISSION = {'engine_engineer': mission}
CHECKS = {'engine_engineer': {'a': check, 'b': check_full_health, 'c': check_damaged_allies}}

"""E163: retail engineer heals another player's ally, then rejects an enemy.

AlliedEngineer.xml AllowFilter is ALLIES/INFANTRY, not same-owner only.
At 8s enable one source, set both player directions Friend, and hurt three
infantry to 50%. Predict own/foreign/inactive = 100/100/50 by 24s.
At 30s set both directions Enemy and hurt again: predict 100/50/50 by 46s.
NO_ATTACK prevents combat; source health is the independent survival control.
This isolates the module with its required status, not the deployment button.
Exact survey phase, self-healing and overlapping sources remain gaps.

Observed a: own/foreign healed together to 100, inactive stayed 50. Original
capture-second expectations failed on a slow game and remain unchanged.
b measured f240 friend snapshot=15, then ended at f448; f450 enemy/position
snapshots were not reached, so their zero readings are not negative evidence.
See work/re/e163_areaally.md. No third run in E163.
"""
from maps import probe_range
from parts import Mission, Script, Test, counted, square


def mission():
    m = Mission(name='CampAreaAlly', map=probe_range, units=[])
    m.put('AlliedEngineer', 'order gun', role='source', name='Ally Area Source')
    m.put('AlliedEngineer', 'base gun', role='off', name='Ally Area Off')
    for role, site, dx, side in (
            ('own', 'order gun', -40, 'p1'),
            ('foreign', 'order gun', 40, 's1'),
            ('inactive', 'base gun', 40, 's1')):
        m.put('AlliedAntiInfantryInfantry', site, dx, 0,
              side=side, role=role, name='Ally Area ' + role)
    return m


def check(m):
    t = Test()
    p, other = m.player('p1'), m.player('s1')
    roles = ('own', 'foreign', 'inactive')
    t.scripts = [Script('Test - start', [], [
        ('MAP_REVEAL_ALL_PERM', p),
        *[('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, 'NO_ATTACK', 1)
          for r in (*roles, 'source', 'off')],
        ('SET_MILLISECOND_TIMER', 'Area friends', 8.0),
        ('SET_MILLISECOND_TIMER', 'Area enemies', 30.0)])]
    for timer, relation, code in (('Area friends', 'Friend', 2), ('Area enemies', 'Enemy', 0)):
        t.scripts.append(Script('Test - ' + timer, [('TIMER_EXPIRED', timer)], [
            ('PLAYER_RELATES_PLAYER', p, other, (code, 0.0, relation)),
            ('PLAYER_RELATES_PLAYER', other, p, (code, 0.0, relation)),
            ('UNIT_CHANGE_OBJECT_STATUS', m.role('source').name, 'GENERIC_TOGGLE_STATE', 1),
            *[('UNIT_SET_HEALTH', m.role(r).name, 50.0) for r in roles]]))
    for role in (*roles, 'source'):
        label = role + ' HP'
        counted('CNV_AreaAlly_' + role, label, t, health=m.role(role).name)
        t.expect += [(label, 1, '==', 100, 5),
                     (label, 24, '==', 50 if role == 'inactive' else 100, 27),
                     (label, 46, '==', 100 if role in ('own', 'source') else 50, 49)]
    t.bench = [('bench_watch', dict(seconds=49, every=1, sheet=False, lines=4))]
    return t


def framed(m):
    """E163 second run: freeze friend/enemy observations at f240/f450.

    Original a's capture-second expectations failed on a slow run; preserve a.
    Here each snapshot has bits 1=own full, 2=foreign full (friend) / exactly
    half (enemy), 4=inactive exactly half, 8=source full. Predict 15/15.
    Frame count saturates at 500 so a late capture retains complete evidence.
    Actual b stopped at f448, friend=15/enemy=0/positions=0. The original
    expectations failed; only the completed f240 snapshot is replay evidence.
    """
    t = Test()
    p, other = m.player('p1'), m.player('s1')
    t.counters = [('E163Frame', 'frame'), ('E163Friend', 'friend snapshot'),
                  ('E163Enemy', 'enemy snapshot'), ('E163Position', 'positions')]
    t.scripts = [Script('Test - framed start', [], [
        ('MAP_REVEAL_ALL_PERM', p),
        *[('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, 'NO_ATTACK', 1)
          for r in ('own', 'foreign', 'inactive', 'source', 'off')]]),
        Script('Test - frame', [('COUNTER', 'E163Frame', 0, 500)],
               [('INCREMENT_COUNTER', 1, 'E163Frame')], once=False)]
    for frame, relation, code in ((90, 'Friend', 2), (270, 'Enemy', 0)):
        t.scripts.append(Script('Test - relation ' + relation,
            [('COUNTER', 'E163Frame', 2, frame)], [
                ('PLAYER_RELATES_PLAYER', p, other, (code, 0., relation)),
                ('PLAYER_RELATES_PLAYER', other, p, (code, 0., relation)),
                ('UNIT_CHANGE_OBJECT_STATUS', m.role('source').name, 'GENERIC_TOGGLE_STATE', 1),
                *[('UNIT_SET_HEALTH', m.role(r).name, 50.)
                  for r in ('own', 'foreign', 'inactive')]]))
    for frame, counter in ((240, 'E163Friend'), (450, 'E163Enemy')):
        for bit, role, hp in ((1, 'own', 100),
                              (2, 'foreign', 100 if frame == 240 else 50),
                              (4, 'inactive', 50), (8, 'source', 100)):
            t.scripts.append(Script(f'Test - snapshot {frame} {role}', [
                ('COUNTER', 'E163Frame', 2, frame),
                ('UNIT_HEALTH', m.role(role).name, 3, hp),
                ('UNIT_HEALTH', m.role(role).name, 1, hp)],
                [('INCREMENT_COUNTER', bit, counter)]))
    # Independent position evidence at the final snapshot; no movement orders.
    for bit, role in ((1, 'source'), (2, 'own'), (4, 'foreign'), (8, 'inactive')):
        site = 'base gun' if role == 'inactive' else 'order gun'
        area = 'Ally Area ' + role + ' site'
        x, y = m.site(site)[:2]
        t.areas[area] = square(x, y, 95)
        t.scripts.append(Script('Test - position ' + role, [
            ('COUNTER', 'E163Frame', 2, 450),
            ('NAMED_INSIDE_AREA', m.role(role).name, area)],
            [('INCREMENT_COUNTER', bit, 'E163Position')]))
    for label, value in (('frame', 500), ('friend snapshot', 15),
                         ('enemy snapshot', 15), ('positions', 15)):
        t.expect.append((label, 105, '==', value, 110))
    t.bench = [('bench_watch', dict(seconds=110, every=2, sheet=False, lines=4))]
    return t


MISSION = {'engine_areaally': mission}
CHECKS = {'engine_areaally': {'a': check, 'b': framed}}

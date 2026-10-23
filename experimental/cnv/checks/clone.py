"""Clone tests: at CONTROL_AT both clones use their control on the engineer of ours beside them; at KILL_AT the map
kills clone A only. Whether each engineer is ours is the readout.

hold: both engineers are taken after CONTROL_AT; A's comes back after KILL_AT (the user's choice C: the control lasts
as long as the clone lives), B's -- whose clone lives on -- does not.
free: as hold, and the mind maiden, sent to her spot at WALK_AT, uses hers by B's engineer at FREE_AT: it is ours again, clone B alive; the
  enemy engineer by her, whom no clone holds, stays the enemy's.
"""
from parts import Script, Test, counted, status
from units.clone import MARK

CONTROL_AT, KILL_AT, FREE_AT, WALK_AT = 10.0, 25.0, 18.0, 12.0


def free(m):
    t = hold(m)
    t.scripts.append(Script('Test - free timer', [], [('SET_MILLISECOND_TIMER', 'Test - free timer', FREE_AT),
                                                      ('SET_MILLISECOND_TIMER', 'Test - walk timer', WALK_AT)]))
    t.scripts.append(Script('Test - walk', [('TIMER_EXPIRED', 'Test - walk timer')],
                            [('MOVE_NAMED_UNIT_TO', m.role('maiden').name, m.mark('maiden spot'))]))
    t.scripts.append(Script('Test - free', [('TIMER_EXPIRED', 'Test - free timer')],
                            [('NAMED_USE_COMMANDBUTTON_ABILITY', m.role('maiden').name,
                              m.ability('maiden', 'control'))]))
    counted('Test Stranger', '路人归我', t, owner=m.role('stranger').name)
    t.expect = [e for e in t.expect if e[0] != 'B 工程师归我']
    t.expect += [('B 工程师归我', CONTROL_AT + 2, 'ever==', 0, FREE_AT), ('B 工程师归我', FREE_AT + 4, '==', 1),
                 ('路人归我', 0, '==', 0)]
    return t


def free_any(m):
    """The control, with a maiden who takes any enemy: the stranger by her is taken too."""
    t = free(m)
    t.expect = [e for e in t.expect if e[0] != '路人归我'] + [('路人归我', FREE_AT + 4, '==', 1)]
    return t


def hold(m):
    t = Test()
    t.scripts.append(Script('Test - start', [], [('MAP_REVEAL_ALL_PERM', m.player('p1')),
                                                 ('SET_MILLISECOND_TIMER', 'Test - control timer', CONTROL_AT),
                                                 ('SET_MILLISECOND_TIMER', 'Test - kill timer', KILL_AT)]))
    t.scripts.append(Script('Test - control', [('TIMER_EXPIRED', 'Test - control timer')],
                            [('NAMED_USE_COMMANDBUTTON_ABILITY', m.role(f'clone {k}').name,
                              m.ability(f'clone {k}', 'control')) for k in 'AB']))
    t.scripts.append(Script('Test - kill', [('TIMER_EXPIRED', 'Test - kill timer')],
                            [('NAMED_KILL', m.role('clone A').name)]))
    for k in 'AB':
        counted(f'Test Ours {k}', f'{k} 工程师归我', t, owner=m.role(f'victim {k}').name)
    counted('Test Held B', 'B 方带标记', t, status=status(MARK), player=m.player(m.role('clone B').side))
    t.expect += [('A 工程师归我', 0, 'ever==', 1, CONTROL_AT),
                 ('A 工程师归我', CONTROL_AT + 2, 'ever==', 0, KILL_AT),
                 ('A 工程师归我', KILL_AT + 3, '==', 1),
                 ('B 工程师归我', CONTROL_AT + 6, '==', 0)]
    t.bench = [('bench_watch', dict(seconds=40, every=2, sheet=False, lines=len(t.counters)))]
    return t

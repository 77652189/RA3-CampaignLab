"""Ordinary VISION: enemy entry, friendly refusal and actual discovered markers.

Retail AlliedConstructionYard uses VISION/Duration=-1s/VisionObserver;
Amount defaults to zero and the default enter filter accepts enemy spies only.
Predict enemy spy consumed, yard stays full HP and owned by s1; ally refuses.
Near marker (700 north of yard) starts outside spy vision, inside yard shroud.
Far same-owner and third-player controls distinguish local from whole-side vision.
No map reveal: expected near discovered after entry; distant bits are measured,
not assumed. RADAR_FREEZE also exists on the retail yard and is outside scope.
Bench 2026-11-11: s1-s10 11100/11100/0; s11-s15 1100/11100/0;
s16-s37 1100/11100/1. Only local near marker is discovered. Five-second
activation delay is a sampled fit (INFERRED), not a measured engine mechanism.
"""
from parts import NOT, Script, Test, counted


def check(m):
    t = Test()
    p, ally = m.player('p1'), m.player('s2')
    t.scripts = [Script('Test - start', [], [
        ('PLAYER_RELATES_PLAYER', p, ally, (2, 0.0, 'Friend')),
        ('PLAYER_RELATES_PLAYER', ally, p, (2, 0.0, 'Friend')),
        ('SET_MILLISECOND_TIMER', 'Vision enter', 10.0)] + [
        ('UNIT_CHANGE_OBJECT_STATUS', m.role(role).name, 'NO_ATTACK', 1)
        for role in ('enemy', 'ally', 'enemy spy', 'ally spy', 'near', 'far', 'control')]),
        Script('Test - enter', [('TIMER_EXPIRED', 'Vision enter')], [
            ('NAMED_GARRISON_SPECIFIC_BUILDING', m.role(role + ' spy').name, m.role(role).name)
            for role in ('enemy', 'ally')])]
    for role, side in (('enemy', 's1'), ('ally', 's2')):
        c = 'Vision ' + role
        counted(c, role, t, health=m.role(role).name)
        for label, cond, value in (
                ('owner', ('NAMED_OWNED_BY_PLAYER', m.player(side), m.role(role).name), 1000),
                ('spy', ('NAMED_NOT_DESTROYED', m.role(role + ' spy').name), 10000)):
            t.scripts.append(Script('Test - ' + role + label, [cond],
                                    [('INCREMENT_COUNTER', value, c)], once=False))
    c = 'Vision seen'
    t.counters.append((c, 'vision'))
    t.scripts.append(Script('Test - reset seen', [], [('SET_COUNTER', c, 0)], once=False))
    for role, bit in (('near', 1), ('far', 10), ('control', 100)):
        t.scripts.append(Script('Test - seen ' + role,
                                [('NAMED_DISCOVERED', p, m.role(role).name)],
                                [('INCREMENT_COUNTER', bit, c)], once=False))
    t.expect = [('enemy', 0, '==', 11100, 7), ('enemy', 18, '==', 1100),
                ('ally', 0, '==', 11100), ('vision', 0, '==', 0, 7),
                ('vision', 12, '==', 0, 14), ('vision', 18, '==', 1)]
    t.bench = [('bench_watch', dict(seconds=35, every=1, sheet=False, lines=3))]
    return t


def check_soviet(m):
    """b: Soviet yard shares the retail ordinary VISION include with Allied yard.

    Predict the same enemy consumption, unchanged HP/owner, friendly refusal,
    and local-only discovered marker; preserve a's timing windows and controls.
    Radar freeze, exact timing and observer cleanup remain outside this slice.
    Bench: s1-s10 11100/11100/0; s11-s17 1100/11100/0;
    s18-s38 1100/11100/1. First discovery differs from a; no timing fit added.
    """
    for role in ('enemy', 'ally'):
        yard = m.role(role)
        yard.template = 'SovietConstructionYard'
        m.find(yard.name).template = yard.template
    return check(m)


def check_japan(m):
    """c: Japan yard shares ordinary VISION; shroud is 1000, vision is 100.

    Predict unchanged a/b stable readings with the same controls and windows.
    Radar freeze and exact activation timing remain outside this slice.
    Bench: s1-s10 11100/11100/0; s11-s18 1100/11100/0;
    s19-s39 1100/11100/1. FAIL at s18; preserve that diagnostic window.
    """
    for role in ('enemy', 'ally'):
        yard = m.role(role)
        yard.template = 'JapanConstructionYard'
        m.find(yard.name).template = yard.template
    return check(m)


def trio(m, send=('allied', 'soviet', 'japan')):
    """A406: the three yards in one run, counted per script pass (not per captured second).

    Rows allied / soviet / japan: passes from the spy's disappearance to the first pass its near marker is
    discovered; entries: the passes before each disappearance, allied + 1000 soviet + 1000000 japan.
    Prediction (the simulator: five seconds after entry for every yard): one delay for all three. a/b/c's 5 / 7 / 8 s
    after s11 came from three runs, so they do not tell a host difference from a run-to-run phase.
    """
    t = Test()
    lanes = ('allied', 'soviet', 'japan')
    t.counters = [('Vision3 ' + k, k) for k in lanes] + [('Vision3 entries', 'entries')]
    t.scripts = [Script('Vision3 start', [], [('SET_MILLISECOND_TIMER', 'Vision3 enter', 10.0)] + [
        ('UNIT_CHANGE_OBJECT_STATUS', obj.name, 'NO_ATTACK', 1) for obj in m.objects] + [
        ('SET_FLAG', 'Vision3 gone ' + k, 1) for k in lanes if k not in send]),
        Script('Vision3 enter', [('TIMER_EXPIRED', 'Vision3 enter')], [
            ('NAMED_GARRISON_SPECIFIC_BUILDING', m.role(k + ' spy').name, m.role(k).name) for k in send])]
    for k, unit in zip(lanes, (1, 1000, 1000000)):
        gone, seen = 'Vision3 gone ' + k, 'Vision3 seen ' + k
        t.scripts += [
            Script('Vision3 count ' + k, [('FLAG', gone, 0)],
                   [('INCREMENT_COUNTER', unit, 'Vision3 entries')], once=False),
            Script('Vision3 latch ' + k, [('NAMED_NOT_DESTROYED', m.role(k + ' spy').name, NOT)],
                   [('SET_FLAG', gone, 1)]),
            Script('Vision3 see ' + k, [('NAMED_DISCOVERED', m.player('p1'), m.role(k + ' near').name)],
                   [('SET_FLAG', seen, 1)]),
            Script('Vision3 wait ' + k, [('FLAG', gone, 1), ('FLAG', seen, 0)],
                   [('INCREMENT_COUNTER', 1, 'Vision3 ' + k)], once=False)]
    t.expect = [(k, 1, 'ever>=', 1, 40) for k in send]
    t.bench = [('bench_watch', dict(seconds=40, every=1, sheet=False, lines=4))]
    return t


def trio_allied(m):
    """b: only the Allied spy is ordered in (H1: one observer per player, a later entry moves it away);
    the unsent Soviet / Japan yards are the no-entry control (H3: a reveal from elsewhere): their rows count
    from the first pass until their near marker is discovered.
    Prediction (H1): Allied stops counting; Soviet / Japan keep counting."""
    return trio(m, send=('allied',))


CHECKS = {'engine_infvis': {'a': check, 'b': check_soviet, 'c': check_japan},
          'engine_infvis3': {'a': trio, 'b': trio_allied}}

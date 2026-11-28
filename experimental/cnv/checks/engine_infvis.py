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
from parts import NOT, Script, Test, counted, square


def check(m, send=('enemy', 'ally')):
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
            for role in send])]
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


def check_unentered(m):
    """d (A408 H4): a without the enemy spy's entry -- the control a/b/c lacked. A407 saw a marker discovered with
    no entry on another map; if the near marker is still seen around s16 here, a/b/c's reveal is not VISION either.
    Prediction (the simulator): enemy stays 11100, near never seen."""
    t = check(m, send=('ally',))
    t.expect = [('vision', 0, '==', 0, 7), ('enemy', 0, '==', 11100, 18)]
    return t


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


def trio_still(m):
    """c (A410 H5): no spy is sent; the entries row instead counts the passes before each near marker leaves the
    60-square it was placed on (allied + 1000 soviet + 1000000 japan). b's minimap showed a red dot walking south
    onto the Japan yard (its spy is 180 south) before the s22 discovery.
    Prediction (H5, the marker walks into an idle spy's sight): a lane is discovered only after its marker left."""
    t = trio(m, send=())
    t.counters[-1] = ('Vision3 entries', 'moved')
    t.scripts = [s for s in t.scripts if not s.name.startswith('Vision3 count')]
    for k, unit in zip(('allied', 'soviet', 'japan'), (1, 1000, 1000000)):
        near = m.find(m.role(k + ' near').name)
        t.areas['Vision3 home ' + k] = square(near.x, near.y, 60.0)
        t.scripts.append(Script('Vision3 home ' + k, [('NAMED_INSIDE_AREA', near.name, 'Vision3 home ' + k)],
                                [('INCREMENT_COUNTER', unit, 'Vision3 entries')], once=False))
    t.expect = [('moved', 1, 'ever>=', 1, 40)]
    return t


def trio_still_s4(m):
    """d (A410 H7): c with the near markers handed to the idle spare Soviet_4 (the yards stay s1's). Walks on:
    the engineer's own idle behaviour; stays (moved keeps counting): Soviet_1 moves them (its yards / its AI)."""
    for k in ('allied', 'soviet', 'japan'):
        m.role(k + ' near').side = m.find(m.role(k + ' near').name).side = 's4'
    return trio_still(m)


# A430: (near, far) north of each yard's centre: inside / outside its VisionRange (150 / 150 / Japan 100), outside
# its footprint (bounding radius 85 / 58 / 61) and 300+ from its spy's start (sight 200).
CLOSE = {'allied': (120, 250), 'soviet': (120, 250), 'japan': (90, 200)}


def trio_close(m, send=('allied', 'soviet', 'japan'), spots=CLOSE):
    """e (A430, the positive control A406-A410 lacked): trio with each near marker moved into its yard's VisionRange,
    a far one outside it, both the idle Soviet_4's (they do not walk, d). Rows count only from the pass the lane's
    spy is gone (no p1 unit left near): near seen + 1000 x far seen. Prediction (A409 H6: the observer sees the
    yard's VisionRange from entry): near rises every pass from entry, far stays 0."""
    t = trio(m, send=send)
    for k, (near, far) in spots.items():
        yard, marker = m.find(m.role(k).name), m.find(m.role(k + ' near').name)
        marker.y, marker.side = yard.y + near, 's4'
        m.role(k + ' near').side = 's4'
        m.put('AlliedEngineer', 'air', 2000 * list(CLOSE).index(k), far, side='s4', role=k + ' far',
              name='Vision3 far ' + k)
    t.scripts = [s for s in t.scripts if not s.name.startswith('Vision3 wait')]
    for k in CLOSE:
        gone, row = 'Vision3 gone ' + k, 'Vision3 ' + k
        for role, unit in (('near', 1), ('far', 1000)):
            t.scripts.append(Script('Vision3 seen %s %s' % (role, k),
                                    [('FLAG', gone, 1), ('NAMED_DISCOVERED', m.player('p1'), m.role(k + ' ' + role).name)],
                                    [('INCREMENT_COUNTER', unit, row)], once=False))
    t.bench = [('bench_watch', dict(seconds=45, every=1, sheet=False, lines=4))]
    t.expect = [(k, 1, 'ever>=', 1, 45) for k in send] or [('entries', 0, '==', 0)]
    return t


def trio_close_unsent(m):
    """f: e with no spy sent (every lane counts from the first pass): the markers' sight from anything but VISION.
    Prediction: all three rows 0 to the end."""
    return trio_close(m, send=())


def trio_close_deleted(m):
    """g: e with each spy deleted at 10 s instead of entering -- e's counterfactual: what p1 sees once its spy is gone
    without VISION (the fog closing back over what the spy saw). Prediction: all three rows 0 to the end."""
    t = trio_close(m)
    enter = next(s for s in t.scripts if s.name == 'Vision3 enter')
    enter.do = [('NAMED_DELETE', m.role(k + ' spy').name) for k in CLOSE]
    t.expect = [(k, 1, '==', 0) for k in CLOSE]
    return t


def trio_shroud(m):
    """h: e's markers at 900 / 1100 north (inside / outside the yards' 1000 shroud clearing; 1080+ from the spies'
    start, past their 500, so no fog left over from the spy's own sight -- g: 10 s). e saw the 250 / 200 marker 35 s
    after entry, so the observer is not the yard's VisionRange (A409 H6 is wrong). Prediction (shroud): near rises
    every pass from entry, far stays 0."""
    return trio_close(m, spots={k: (900, 1100) for k in CLOSE})


def trio_owner(m):
    """i: h with the yard owner's own things 900 north -- a Soviet_1 engineer (s1 walks it, A410 H7) and 100 east of
    it a Soviet_1 power plant (does not walk). Rows: engineer seen + 1000 x plant seen + 1000000 x passes the engineer
    stands in a 60-square at its spot (counted from the start). a / b's Soviet_1 markers went unseen 30 s after entry
    though within 1000: H9 a walking thing is not shown, H10 the owner's own things are not. Prediction (sim): both
    seen every pass from entry."""
    t = trio_close(m, spots={k: (900, 1100) for k in CLOSE})
    for k in CLOSE:
        eng, far = m.find(m.role(k + ' near').name), m.find(m.role(k + ' far').name)
        eng.side = m.role(k + ' near').side = far.side = m.role(k + ' far').side = 's1'
        far.template, far.x, far.y = 'SovietPowerPlant', eng.x + 100, eng.y
        t.areas['Vision3 spot ' + k] = square(eng.x, eng.y, 60.0)
        t.scripts.append(Script('Vision3 spot ' + k, [('NAMED_INSIDE_AREA', eng.name, 'Vision3 spot ' + k)],
                                [('INCREMENT_COUNTER', 1000000, 'Vision3 ' + k)], once=False))
    return t


def units(m):
    """A411 VISION_UNITS on the hosts our levels have (missions/infiltrator_vision.py units), both spies sent at 10 s.

    Rows (script passes, cumulative): entries = passes before each spy is gone, veh + 1000 inf; veh = passes the
    Tsunami is discovered + 1000 x the Japan infantry's; inf = the still conscript's + 1000 x the walker's (sent
    1200 west at 10 s). XML: VISION_UNITS, UnitDuration 30 s, filter KindOf VEHICLE / INFANTRY.
    Prediction (XML + E199's 0/1/1/1/1): the Tsunami and both conscripts seen 4 in 5 passes from entry for 450
    passes, then not (about 360); the outsider never. Simulator: Japan / Soviet hosts are gaps, the spies never
    enter, all zero."""
    t = Test()
    t.counters = [('Unitvis entries', 'entries'), ('Unitvis veh', 'veh'), ('Unitvis inf', 'inf')]
    walker = m.find(m.role('walker').name)
    t.waypoints['Unitvis west'] = (walker.x - 1200, walker.y)
    t.scripts = [Script('Unitvis start', [], [('SET_MILLISECOND_TIMER', 'Unitvis enter', 10.0)] + [
        ('UNIT_CHANGE_OBJECT_STATUS', obj.name, 'NO_ATTACK', 1) for obj in m.objects]),
        Script('Test - Unitvis enter', [('TIMER_EXPIRED', 'Unitvis enter')], [
            ('NAMED_GARRISON_SPECIFIC_BUILDING', m.role(k + ' spy').name, m.role(k).name) for k in ('veh', 'inf')] + [
            ('MOVE_NAMED_UNIT_TO', walker.name, 'Unitvis west')])]
    for k, unit in (('veh', 1), ('inf', 1000)):
        gone = 'Unitvis gone ' + k
        t.scripts += [Script('Unitvis count ' + k, [('FLAG', gone, 0)],
                             [('INCREMENT_COUNTER', unit, 'Unitvis entries')], once=False),
                      Script('Unitvis latch ' + k, [('NAMED_NOT_DESTROYED', m.role(k + ' spy').name, NOT)],
                             [('SET_FLAG', gone, 1)])]
    for role, unit, row in (('tank', 1, 'veh'), ('outsider', 1000, 'veh'), ('still', 1, 'inf'), ('walker', 1000, 'inf')):
        t.scripts.append(Script('Unitvis see ' + role, [('NAMED_DISCOVERED', m.player('p1'), m.role(role).name)],
                                [('INCREMENT_COUNTER', unit, 'Unitvis ' + row)], once=False))
    t.expect = [('entries', 1, 'ever>=', 1, 50)]
    t.bench = [('bench_watch', dict(seconds=50, every=1, sheet=False, lines=3))]
    return t


def units_long(m):
    """b (A412 H1 / H2): a run to 90 s, plus 'there' = passes the walker stands in a 60-square at its goal.
    Prediction (H1, the observer lives while the host does): the Tsunami / still conscript keep rising to s90;
    (H2, a walker is picked up only once it stops): the walker's first sighting is its first pass 'there'."""
    t = units(m)
    walker = m.find(m.role('walker').name)
    t.areas['Unitvis there'] = square(walker.x - 1200, walker.y, 60.0)
    t.counters.append(('Unitvis there', 'there'))
    t.scripts.append(Script('Unitvis there', [('NAMED_INSIDE_AREA', walker.name, 'Unitvis there')],
                            [('INCREMENT_COUNTER', 1, 'Unitvis there')], once=False))
    t.bench = [('bench_watch', dict(seconds=90, every=1, sheet=False, lines=4))]
    return t


CHECKS = {'engine_infvis': {'a': check, 'b': check_soviet, 'c': check_japan, 'd': check_unentered},
          'engine_infvis3': {'a': trio, 'b': trio_allied, 'c': trio_still, 'd': trio_still_s4,
                             'e': trio_close, 'f': trio_close_unsent, 'g': trio_close_deleted,
                             'h': trio_shroud, 'i': trio_owner},
          'engine_infunit': {'a': units, 'b': units_long}}

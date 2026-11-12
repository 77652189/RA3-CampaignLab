"""E70: independent retail engineer area healing, without drones or dispatch.

SDK AlliedEngineer: radius 100, heals 10%/s, allied INFANTRY only,
requires GENERIC_TOGGLE_STATE. Script that status directly to isolate this
module from the deployment button. At second 8 damage four targets to 50%:
active engineer's infantry at 40 / infantry at 400 / vehicle at 60, and
inactive engineer's infantry at 40. Predict only the first heals to 100.
At second 30 clear the status and damage that infantry again: predict 50
thereafter. No claim about survey phase, exact rate, stacking or attachment.

Bench E70 2026-11-11 PASS: near/far/vehicle/inactive HP at s24-s26 =
100/50/50/50, after status off and second damage at s35-s38 = 50/50/50/50.
Capture s7-s10 near HP 63/63/76/90 is retained in work/re/e_passive_e70.md;
capture timestamps do not establish the game's heal phase or exact rate.
"""
from maps import probe_range
from parts import Mission, Script, Test, counted


def mission():
    m = Mission(name='CampPassive', map=probe_range, units=[])
    m.put('AlliedEngineer', 'order gun', role='on', name='Area On')
    m.put('AlliedEngineer', 'base gun', role='off', name='Area Off')
    for role, template, site, x, y in (
            ('near', 'AlliedAntiInfantryInfantry', 'order gun', 0, 40),
            ('far', 'AlliedAntiInfantryInfantry', 'order gun', 0, 400),
            ('vehicle', 'AlliedAntiVehicleVehicleTech1', 'order gun', 60, 0),
            ('inactive', 'AlliedAntiInfantryInfantry', 'base gun', 0, 40)):
        m.put(template, site, x, y, role=role, name='Area ' + role)
    return m


def check(m):
    t = Test()
    source = m.role('on').name
    roles = ('near', 'far', 'vehicle', 'inactive')
    t.scripts = [Script('Test - start', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1')),
        ('SET_MILLISECOND_TIMER', 'Area hurt', 8.0),
        ('SET_MILLISECOND_TIMER', 'Area stop', 30.0)]),
        Script('Test - hurt', [('TIMER_EXPIRED', 'Area hurt')], [
            ('UNIT_CHANGE_OBJECT_STATUS', source, 'GENERIC_TOGGLE_STATE', 1),
            *[('UNIT_SET_HEALTH', m.role(role).name, 50.0) for role in roles]]),
        Script('Test - stop', [('TIMER_EXPIRED', 'Area stop')], [
            ('UNIT_CHANGE_OBJECT_STATUS', source, 'GENERIC_TOGGLE_STATE', 0),
            ('UNIT_SET_HEALTH', m.role('near').name, 50.0)])]
    for role in roles:
        counted('CNV_Area_' + role, role + ' HP', t, health=m.role(role).name)
        t.expect += [(role + ' HP', 1, '==', 100, 5),
                     (role + ' HP', 24, '==', 100 if role == 'near' else 50, 27),
                     (role + ' HP', 35, '==', 50, 39)]
    t.bench = [('bench_watch', dict(seconds=39, every=1, sheet=False, lines=4))]
    return t


def frames(m, start=8.0):
    """E72: intermediate heal crossings counted in game-script frames.

    Count frames after damage while HP is below 51/64/78/91. At 15 fps,
    continuous 10%/s predicts crossing gaps near 19-21 frames. A
    20-frame batch of 13 1/3 percentage points predicts 20/20/20 gaps.
    The absolute first-crossing phase is unknown; never fit it from captures.
    E72 bench: 11/31/51/71, gaps 20/20/20; first phase remains unresolved.
    See work/re/e_passive_e72.md; the model replay remains a strict xfail.
    E71's earlier 51/55/60/100 readings remain in work/re/e_passive_e71.md.
    """
    t = Test()
    source, target = m.role('on').name, m.role('near').name
    t.scripts = [Script('Test - start', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1')),
        ('SET_MILLISECOND_TIMER', 'Area frame hurt', start)]),
        Script('Test - frame hurt', [('TIMER_EXPIRED', 'Area frame hurt')], [
            ('UNIT_CHANGE_OBJECT_STATUS', source, 'GENERIC_TOGGLE_STATE', 1),
            ('UNIT_SET_HEALTH', target, 50.0),
            ('SET_FLAG', 'Area frame started', 1)])]
    for threshold, upper in ((51, 30), (64, 50), (78, 70), (91, 90)):
        counter, label = f'CNV_Area_Below{threshold}', f'below {threshold}'
        t.counters.append((counter, label))
        t.scripts.append(Script(f'Test - below {threshold}', [
            ('FLAG', 'Area frame started', 1), ('UNIT_HEALTH', target, 0, threshold)],
            [('INCREMENT_COUNTER', 1, counter)], once=False))
        # Pre-run bounds: allow unknown survey phase, require eventual healing.
        t.expect += [(label, 20, '>=', 1, 24),
                     (label, 20, '<=', upper, 24)]
    t.bench = [('bench_watch', dict(seconds=24, every=1, sheet=False, lines=4))]
    return t


def shifted_frames(m):
    """E73 phase control: shift only activation/damage from 8 to 9 seconds.

    Pre-run hypotheses: fixed 20-frame phase predicts 16/36/56/76;
    fixed activation delay predicts 11/31/51/71. Bench: 16/36/56/76.
    Scheduler source remains a gap; see work/re/e_passive_e73.md.
    """
    return frames(m, start=9.0)


MISSION = {'engine_passivearea': mission}
CHECKS = {'engine_passivearea': {'a': check, 'f': frames, 'g': shifted_frames}}

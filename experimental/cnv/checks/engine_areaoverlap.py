"""E166: two full-health retail engineer sources versus one and zero.

At f60 activate designated sources and hurt only three infantry to 50%.
Existing E72/E74 batches predict single HP 76 2/3 at f100 (75..80 band),
double HP 100 if additive, off HP 50. A nonstacking double stays in the
single band. f61 freezes the injury baseline; f210 predicts 100/100/50.
Sources stay full; separate bits freeze source health and independent survival.
Clock phase/rate are retained INFERRED assumptions, not fitted in this probe.
No cap, mixed-rule, source-as-beneficiary or activation-button claim.

MEASURED a: f61=31, f100=29, f210=31, complete f240. Additive-full
prediction is rejected, but double's exact intermediate HP is not established.
b tests the alternative double 75..80 band alongside the same single control.
Original a prediction stays unchanged. See work/re/e166_areaoverlap.md.
MEASURED b: f61/f100/f210=31/31/31, complete f240. Single and double
both lie in 75..80 at f100, off stays 50, sources full and all alive.
This supports one contribution for the measured pair, not an exact HP claim.
"""
from maps import probe_range
from parts import Mission, Script, Test, NOT

TARGETS = ('single', 'double', 'off')
SOURCES = ('one', 'two_a', 'two_b', 'disabled')
ROLES = TARGETS + SOURCES


def mission():
    m = Mission(name='CampAreaStack', map=probe_range, units=[])
    for role, site, dx in (('one', 'base gun', -40),
                           ('two_a', 'order gun', -40),
                           ('two_b', 'order gun', 40),
                           ('disabled', 'high gun', -40)):
        m.put('AlliedEngineer', site, dx, 0, role=role, name='Stack ' + role)
    for role, site in zip(TARGETS, ('base gun', 'order gun', 'high gun')):
        m.put('AlliedAntiInfantryInfantry', site, 0, 40,
              role=role, name='Stack ' + role)
    return m


def check(m):
    return _probe(m, (100, 100))


def nonstack(m):
    return _probe(m, (75, 80))


def _probe(m, double_band):
    t = Test()
    t.counters = [('E166Frame', 'frame'), ('E166Base', 'baseline'),
                  ('E166Mid', 'middle'), ('E166Late', 'late')]
    t.scripts = [Script('Test - start', [], [
        ('MAP_REVEAL_ALL_PERM', m.player('p1')),
        *[('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, 'NO_ATTACK', 1) for r in ROLES]]),
        Script('Test - frame', [('COUNTER', 'E166Frame', 0, 240)],
               [('INCREMENT_COUNTER', 1, 'E166Frame')], once=False),
        Script('Test - hurt activate', [('COUNTER', 'E166Frame', 2, 60)], [
            *[('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, 'GENERIC_TOGGLE_STATE', 1)
              for r in SOURCES[:3]],
            *[('UNIT_SET_HEALTH', m.role(r).name, 50.) for r in TARGETS]])]
    for frame, counter, bands in (
            (61, 'E166Base', ((50, 50),) * 3),
            (100, 'E166Mid', ((75, 80), double_band, (50, 50))),
            (210, 'E166Late', ((100, 100), (100, 100), (50, 50)))):
        at = [('COUNTER', 'E166Frame', 2, frame)]
        for bit, (role, (lo, hi)) in enumerate(zip(TARGETS, bands)):
            t.scripts.append(Script(f'Test - HP {frame} {role}', at + [
                ('UNIT_HEALTH', m.role(role).name, 3, lo),
                ('UNIT_HEALTH', m.role(role).name, 1, hi)],
                [('INCREMENT_COUNTER', 1 << bit, counter)]))
        t.scripts.append(Script(f'Test - sources {frame}', at + [
            ('UNIT_HEALTH', m.role(r).name, 3, 100) for r in SOURCES],
            [('INCREMENT_COUNTER', 8, counter)]))
        t.scripts.append(Script(f'Test - alive {frame}', at + [
            ('NAMED_DESTROYED', m.role(r).name, NOT) for r in ROLES],
            [('INCREMENT_COUNTER', 16, counter)]))
    t.expect = [(label, 0, 'ever>=', value) for label, value in
                (('frame', 240), ('baseline', 31), ('middle', 31), ('late', 31))]
    t.bench = [('bench_watch', dict(seconds=100, every=1, sheet=False,
                                  lines=4, until='c1>=240'))]
    return t


MISSION = {'engine_areaoverlap': mission}
CHECKS = {'engine_areaoverlap': {'a': check, 'b': nonstack}}

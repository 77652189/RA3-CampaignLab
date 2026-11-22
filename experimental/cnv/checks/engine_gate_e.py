"""E190: native door-template resolution after the SDK rejects the module.

The SDK schemas reject GateOpenAndCloseBehavior inside Behaviors. Do not
replace it with scripted model flags. Place both native templates without
compiling their XML, using the same script creation action as a known retail
building sentinel. Map placement also forced SDK compilation and failed.
Predict f180 frame/Romania door/sanitarium door/sentinel = 180/0/0/1.
This is a template prerequisite diagnostic, NOT a gate-module deletion
control or opening/pathing coverage. See work/re/e190_gate.md for the failed
four-door initialization probe and the exact compiler evidence.
MEASURED a PASS: f180=180/0/0/1; only the known building exists at sampling.
The simulator makes both doors (readings: a mismatch row). Missing versus
rejected creation is INFERRED; no template-resolution/acceptance field is
available in the four HUD rows. No gate effect coverage is registered.
"""
from maps import probe_range
from model import Mission, Role, Script, Test


def mission():
    m = Mission(name='CampGateNatE', map=probe_range, units=[])
    m.put('AlliedConstructionYard', 'base factory', role='anchor', name='E190 anchor')
    # Runtime cast creation belongs to the mission, including builds without a check.
    m.scripts = [Script('Test - clock', [('COUNTER', 'E190Frame', 0, 180)],
                        [('INCREMENT_COUNTER', 1, 'E190Frame')], once=False)]
    for template, tag, site in [
        ('RM_AlliedBlastDoor', 'Romania', 'base gun'),
        ('SS_Door', 'Sanitarium', 'high gun'),
        ('AlliedPowerPlant', 'Sentinel', 'removed gun')]:
        m.cast[tag] = Role(template, 'E190 ' + tag, 'p1', [site])
        m.waypoint(tag, 'E190 point ' + tag, site)
        m.scripts.append(Script('Test - create ' + tag, [('COUNTER', 'E190Frame', 2, 30)],
            [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', m.role(tag).name,
              m.role(tag).template, m.team(), m.mark(tag))]))
    return m


def check(m):
    t = Test()
    t.counters = [('E190Frame', 'frame'), ('E190Romania', 'Romania'),
                  ('E190Sanitarium', 'Sanitarium'), ('E190Sentinel', 'sentinel')]
    for tag in ('Romania', 'Sanitarium', 'Sentinel'):
        t.scripts.append(Script('Test - live ' + tag, [
            ('COUNTER', 'E190Frame', 2, 180),
            ('NAMED_NOT_DESTROYED', m.role(tag).name)],
            [('SET_COUNTER', 'E190' + tag, 1)]))
    t.expect = [('frame', 0, 'ever==', 180), ('Romania', 0, '==', 0),
                ('Sanitarium', 0, '==', 0), ('sentinel', 0, 'ever==', 1)]
    t.bench = [('bench_watch', dict(seconds=100, every=1, sheet=False, lines=4, until='c1>=180'))]
    return t


MISSION = {'engine_gate_e': mission}
CHECKS = {'engine_gate_e': {'a': check}}

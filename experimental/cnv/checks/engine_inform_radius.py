"""InformTarget radius discriminator using the existing read-only incoming probe.

Before bench: radius200 (base, instant order) should notify the primary and
the neighbour80 away, not the neighbour320 away (INFERRED). Default radius0
(high) should notify only its primary; removed has no launch notification.
Only InformTarget changes; projectile/warhead damage remains single-target.
Read incoming rows at launch, not HP or shield as a proxy for notification.
No wall-clock expectations: retain all logical-frame observations privately.
"""
from checks import engine_inform_ai as inform
from checks import engine_inform_probe as probe


def mission():
    m = probe.mission()
    m.name = 'CampIRad'
    for lane in inform.LANES:
        for label, offset in (('near', 80), ('far', 320)):
            m.waypoint(lane + ' ' + label, 'Info ' + lane + ' ' + label,
                       lane + ' gun', offset, 450)
    return m


def check(m):
    for lane in ('base', 'order', 'removed'):
        unit = m.units[inform.LANES.index(lane)]
        assert unit.xml.count('<InformTargetNugget/>') == 1
        nugget = '' if lane == 'removed' else '<InformTargetNugget Radius="200"/>'
        unit.xml = unit.xml.replace('<InformTargetNugget/>', nugget, 1)
    t = probe._probed(m, inform.check(m))
    make = next(s for s in t.scripts if s.name == 'Test - make')
    for lane in inform.LANES:
        for label in ('near', 'far'):
            name = 'Info ' + lane + ' ' + label
            make.do += [('CREATE_NAMED_ON_TEAM_AT_WAYPOINT', name, probe.PROBE,
                         m.team('p1' if lane == 'high' else 's1'), m.mark(lane + ' ' + label)),
                        ('UNIT_CHANGE_OBJECT_STATUS', name, 'IMMOBILE', 1)]
    # Counter remains a health control, independent of notification assertions.
    for script in t.scripts:
        if script.name.startswith('Test - display '):
            script.do = script.do[:2]
    t.expect = []
    return t


def swapped(m):
    """Second run: move radius200 from base/order to the player high lane.

    Predict launch302: base/order primary only; high primary+near, far none;
    removed remains empty. Timing/damage still follows the primary shot.
    """
    t = check(m)
    for lane in ('base', 'order'):
        unit = m.units[inform.LANES.index(lane)]
        unit.xml = unit.xml.replace('<InformTargetNugget Radius="200"/>', '<InformTargetNugget/>')
    unit = m.units[inform.LANES.index('high')]
    unit.xml = unit.xml.replace('<InformTargetNugget/>', '<InformTargetNugget Radius="200"/>', 1)
    return t


MISSION = {'engine_inform_radius': mission}
CHECKS = {'engine_inform_radius': {'a': check, 'b': swapped}}

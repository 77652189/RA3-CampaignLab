"""InformTarget natural expiry, independent of actual projectile arrival.

Before bench: preserve engine_inform_probe's shell velocity, positions and
scripts. Change only WeaponSpeed75 ->750 (base) /7500 (low damage lane).
At the previous launch302, predict (hit, expiry)=(309,313)/(302,304),
versus default player control (377,404). Actual shells still hit389.
INFERRED before measurement: retain through expiry, remove strictly after;
the read-only incoming log decides cleanup timing, counters only check HP.
Full placement/flight/AI replay and damage history remain outside this slice.

Measured a: deadlines313/304, physical removals336/312; b: deadlines303/317,
physical removals336/320. Shared periodic sweep prediction was falsified.
Only launch tuples replay green; autonomous cleanup remains strict xfail.
The first wall-clock HP window failed before logical fire; kept unchanged.
Two-run budget exhausted; see work/re/c_inform_expiry_report.md.
"""
from checks import engine_inform_ai as inform
from checks import engine_inform_probe as probe


def mission():
    m = probe.mission()
    m.name = 'CampIExp'
    return m


def check(m):
    for lane, speed in (('base', 750), ('removed', 7500)):
        unit = m.units[inform.LANES.index(lane)]
        assert unit.xml.count('WeaponSpeed="75"') == 1
        unit.xml = unit.xml.replace('WeaponSpeed="75"', f'WeaponSpeed="{speed}"', 1)
    t = probe._probed(m, inform.check(m))
    # Keep the original firing/control actions. Display raw HP rather than
    # the automatic-shield latches, whose timing is not this experiment.
    for script in t.scripts:
        if script.name.startswith('Test - display '):
            script.do = script.do[:2]
    t.expect = [(lane + ' info', 31, '==', hp, 34)
                for lane, hp in zip(inform.LANES, (68, 68, 68, 89))]
    return t


def crossed_deadlines(m):
    """Second discriminator: move deadlines across the observed cleanup frames.

    Prediction: base hit302/expiry303, low hit302/expiry317. If cleanup
    is a shared periodic sweep (INFERRED), removals swap to312/336.
    No wall-clock HP assertion: first a's s31 window preceded logical fire
    under load; preserve that failed prediction, judge the frame log instead.
    """
    t = check(m)
    for lane, factors in (('base', 'MinTimeToImpactFudgeFactor=".01" MaxTimeToImpactFudgeFactor=".1"'),
                          ('removed', 'MaxTimeToImpactFudgeFactor="16"')):
        unit = m.units[inform.LANES.index(lane)]
        assert unit.xml.count('<InformTargetNugget/>') == 1
        unit.xml = unit.xml.replace('<InformTargetNugget/>', f'<InformTargetNugget {factors}/>')
    t.expect = []
    return t


MISSION = {'engine_inform_expiry': mission}
CHECKS = {'engine_inform_expiry': {'a': check, 'b': crossed_deadlines}}

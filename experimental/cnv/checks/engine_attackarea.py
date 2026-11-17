"""NAMED_ATTACK_AREA retail Dreadnought region contrast.

Four retail uses are a02 Leviathans bombarding one trigger region.
Prediction/evidence: work/re/c_attackarea_report.md. At 4s order a north,
b south (with map revealed); the other plant and same-player uncommanded ship are controls.
At 18s directly attack the other plant and the control plant (positive).
Actual HP, control HP plus ship-position mask, and logical frames are read.
MEASURED: neither area order damages either plant; direct orders at 18s hit.
Both ships remain on their start pads through the reliable live-control window.
Area target-kind/autoacquire/visibility selection is unresolved; no no-op rule
is inferred. Post-control-death counter accumulation is not a movement reading.
Random impact choice, exact dispatch timing and other templates remain gaps.
"""
from maps import island
from parts import Mission, Script, Test, square
from checks import engine_scripts8 as s8


def mission():
    m = Mission(name='CampAtkArea', map=island, units=[], facts={})
    for role, x, y, template, side in (
        ('gun', 450., 2500., 'SovietAntiStructureShip', 'p1'),
        ('control', 4550., 2500., 'SovietAntiStructureShip', 'p1'),
        ('north', 1250., 2350., 'AlliedPowerPlant', 's4'),
        ('south', 1250., 2650., 'AlliedPowerPlant', 's4'),
        ('other', 3750., 2500., 'AlliedPowerPlant', 's4')):
        m.put(template, 'start', x-1250., y-2500., side=side,
              role=role, name='CNV Area '+role)
        m.waypoint(role, 'CNV Area '+role+' spot', 'start', x-1250., y-2500.)
    return m


def check(m, which):
    t = Test()
    for role in ('north', 'south', 'gun', 'control'):
        t.areas['CNV Area '+role] = square(*m.point(role), 20. if role in ('north', 'south') else 100.)
    t.scripts.append(Script('Test Area hold', [], [
        ('UNIT_ALLOW_AI_AUTOACQUIRE', m.role(r).name, 0) for r in ('gun', 'control')] + [
        ('UNIT_CHANGE_OBJECT_STATUS', m.role(r).name, 'NO_ATTACK', 1)
        for r in ('north', 'south', 'other')]))
    if which == 'b':
        t.scripts.append(Script('Test Area reveal', [], [('MAP_REVEAL_ALL_PERM', m.player())]))
    selected, other = ('north', 'south') if which == 'a' else ('south', 'north')
    s8.at(t, 'area order', 4., [('NAMED_ATTACK_AREA', m.role('gun').name, 'CNV Area '+selected)])
    s8.at(t, 'area positive', 18., [
        ('NAMED_ATTACK_NAMED', m.role('gun').name, m.role(other).name),
        ('NAMED_ATTACK_NAMED', m.role('control').name, m.role('other').name)])
    for role, label in (('north', '北靶血量'), ('south', '南靶血量')):
        c = 'CNV_AA_'+role
        t.counters.append((c, label))
        t.scripts.append(Script('Test Area HP '+role, [], [
            ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', m.role(role).name, c)], once=False))
    c = 'CNV_AA_Control'
    t.counters.append((c, '对照位置码'))
    t.scripts.append(Script('Test Area control HP', [], [
        ('SET_UNIT_HEALTH_PERCENTAGE_TO_COUNTER', m.role('other').name, c)], once=False))
    for k, role in enumerate(('gun', 'control')):
        t.scripts.append(Script('Test Area position '+role,
            [('NAMED_INSIDE_AREA', m.role(role).name, 'CNV Area '+role)],
            [('INCREMENT_COUNTER', 1000*(1 << k), c)], once=False))
    s8.frames(t, 'CNV_AA_Frame', '逻辑帧', [])
    t.expect = [('北靶血量', 0., 'ever==', 100, 3.),
                ('南靶血量', 0., 'ever==', 100, 3.),
                ('北靶血量' if selected == 'north' else '南靶血量', 8., 'ever<', 100, 17.),
                ('对照位置码', 2., '==', 3100, 17.)]
    s8.watch(t, 30., .5)
    return t


MISSION = {'engine_attackarea': mission}
CHECKS = {'engine_attackarea': {w: (lambda m, w=w: check(m, w)) for w in 'ab'}}


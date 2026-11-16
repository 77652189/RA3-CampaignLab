"""Native transport disguise: autonomous enemy fire and EVACUATE cancellation.

Four lanes: native disguise held / native disguise then empty EVACUATE /
removed SPN / removed SPN with only scripted DISGUISED. Reuse the measured
retail host, marker and four pads. A separate retail conscript 100 units east
is released to acquire autonomously at 10s; never order it to attack.
At 16s press Command_DisguisedEvacuate on high only, without passengers.
Packed = alive*1000 + disguiseWeaponHit*100 + enemyDamageSeen*10 + DISGUISED.
INFERRED prediction: before release 1101/1101/1100/1101; after cancellation
1101/1110/1110/1111. EVACUATE cancelling an empty transport is a hypothesis,
not an SDK guarantee. Script bit alone is not claimed to confer identity.
No whole-item promotion; spy, render identity and exact clocks remain gaps.
Evidence: work/re/c_spncancel_report.md.
MEASURED empty a: s8-13 1101/1101/1100/1101; s14-33
1101/1101/1110/1111. Empty EVACUATE did not clear the native disguise.
The original cancellation prediction remains visible in a's expectations.
Loaded b adds one passive UNATTACKABLE passenger and observes ENCLOSED:
high additionally packs passengerAlive*100000 + ENCLOSED*10000.
INFERRED loaded prediction after EVACUATE: 1101/101110/1110/1111.
MEASURED loaded a: s10-14 1101/111101/1100/1101; s15-24
1101/111101/1110/1111; s25 1101/101100/1110/1111; s26-39
1101/101110/1110/1111. The passenger exits, disguise clears, then damage
is observed. The original s22-24 prediction is too early on the capture
clock and remains FAIL; no exact clock rule is inferred from these samples.
"""
from copy import deepcopy

from checks import engine_spntrans as transport
from model import Script, status


def mission(loaded=False):
    m = transport.mission()
    m.name = 'CampSPNCargo' if loaded else 'CampSPNCancel'
    # high is the intact native consumer; order is the removed-SPN control.
    for index, source in ((1, 0), (2, 3)):
        old, unit = m.units[index], deepcopy(m.units[source])
        unit.xml = unit.xml.replace(unit.id, old.id)
        for link, new_link in zip(unit.link, old.link):
            unit.xml = unit.xml.replace(link.split(':', 1)[1], new_link.split(':', 1)[1])
        unit.id, unit.link = old.id, old.link
        m.units[index] = unit
    for lane in transport.CASES:
        m.put('SovietAntiInfantryInfantry', lane+' gun', 100, 0, side='s1',
              angle=3.14159, name='SPC '+lane+' observer')
    if loaded:
        crew = m.crew('SPCCargo')
        m.put('SovietAntiInfantryInfantry', 'high gun', -50, 0,
              name='SPC passenger', props={'originalOwner': crew})
    return m


def check(m, loaded=False):
    t = transport.check(m)
    # Retain independent marker latch and native fire window, replace readouts.
    t.counters = []
    t.scripts = [s for s in t.scripts if not s.name.startswith(
        ('Test - reset ', 'Test - caster ', 'Test - victim ', 'Test - disguise '))]
    start, release = [], []
    for lane in transport.CASES:
        caster, observer = 'SPT '+lane+' caster', 'SPC '+lane+' observer'
        start += [('UNIT_CHANGE_OBJECT_STATUS', observer, 'NO_ATTACK', 1),
                  ('UNIT_CHANGE_OBJECT_STATUS', observer, 'IMMOBILE_ALLOW_ROTATE', 1)]
        release.append(('UNIT_CHANGE_OBJECT_STATUS', observer, 'NO_ATTACK', 0))
        counter, hit = 'CNV_SPC_'+lane, 'SPC damage '+lane
        t.counters.append((counter, lane+' packed'))
        t.scripts += [
            Script('Test - enemy damage '+lane, [('UNIT_HEALTH', caster, 0, 100)],
                   [('SET_COUNTER', hit, 10)]),
            Script('Test - packed '+lane, [], [('SET_COUNTER', counter, 0),
                   ('COUNTER_MATH_COUNTER', counter, 0, 'SPT marker '+lane),
                   ('COUNTER_MATH_VALUE', counter, 2, 10),
                   ('COUNTER_MATH_COUNTER', counter, 0, hit)], once=False),
            Script('Test - alive '+lane, [('NAMED_NOT_DESTROYED', caster)],
                   [('INCREMENT_COUNTER', 1000, counter)], once=False),
            Script('Test - condition '+lane, [('UNIT_HAS_MODELCONDITION', caster, 'DISGUISED')],
                   [('INCREMENT_COUNTER', 1, counter)], once=False)]
    t.scripts.insert(0, Script('Test - observers hold', [], start))
    for label, at, actions in (
            ('release', 10., release),
            ('cancel', 16., [('NAMED_USE_COMMANDBUTTON_ABILITY', 'SPT high caster',
                             'Command_DisguisedEvacuate')])):
        timer = 'SPC '+label
        t.scripts[0].do.append(('SET_MILLISECOND_TIMER', timer, at))
        t.scripts.append(Script('Test - '+label, [('TIMER_EXPIRED', timer)], actions))
    if loaded:
        t.scripts[0].do += [
            ('UNIT_CHANGE_OBJECT_STATUS', 'SPC passenger', 'NO_ATTACK', 1),
            ('UNIT_CHANGE_OBJECT_STATUS', 'SPC passenger', 'UNATTACKABLE', 1),
            ('SET_MILLISECOND_TIMER', 'SPC load', 1.)]
        t.scripts += [
            Script('Test - load', [('TIMER_EXPIRED', 'SPC load')],
                   [('TEAM_GARRISON_SPECIFIC_BUILDING_INSTANTLY', m.teams['SPCCargo'],
                     'SPT high caster')]),
            Script('Test - passenger alive', [('NAMED_NOT_DESTROYED', 'SPC passenger')],
                   [('INCREMENT_COUNTER', 100000, 'CNV_SPC_high')], once=False),
            Script('Test - passenger enclosed',
                   [('UNIT_HAS_OBJECT_STATUS', 'SPC passenger', status('ENCLOSED'))],
                   [('INCREMENT_COUNTER', 10000, 'CNV_SPC_high')], once=False)]
    t.expect = [(label, 22, '==', value, 24) for (_, label), value in
                zip(t.counters, (1101, 101110 if loaded else 1110, 1110, 1111))]
    t.bench = [('bench_watch', dict(seconds=24., every=.5, sheet=False, lines=4))]
    return t


def loaded_mission():
    return mission(loaded=True)


def loaded_check(m):
    return check(m, loaded=True)


MISSION = {'engine_spncancel': mission, 'engine_spncargo': loaded_mission}
CHECKS = {'engine_spncancel': {'a': check}, 'engine_spncargo': {'a': loaded_check}}

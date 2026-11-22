"""E192: retail civilian AnimalAIUpdate near/far threat and deletion control.

BaseCivilian declares FleeRadius=300, blind radius=75, wander radius=30,
normal/panic speeds=17/75. Retain these values and the complete female host.
Replace the inherited AI container identically, except remove AnimalAIUpdate
in Off. No movement order, damage or synthetic panic status is injected.
Near/Off have a stationary enemy 100 east; Far has one 700 east. All live
on isolated pads. Prediction: by f240 Near has left its 100-half-side start
square, Off/Far have not; all six units survive. Four HUD lines freeze
frame / ever-left bits (Near=1,Off=2,Far=4) / live bits / initial-area bits.
Random wander, threat qualification and exact flee time are unmeasured;
the predicted distinction is not evidence until the named bench runs.
MEASURED first a: f240=240/0/7/7, no lane left; original prediction stays.
engine_animalfire_e:a adds actual gunfire at adjacent power plants from f45,
with ext observation enabled. Live bits add 8/16/32 only after each plant
has lost health AND reports the conscript as damage source. Predict gate63.
This tests a firing-threat prerequisite, not damage to the civilians.
MEASURED firing a: f240=240/0/7/7 too; the legal-hit prerequisite FAILED.
Two runs do not establish flee behavior or absence of an effect. No model
rule added. Firing acceptance/aim readiness and flee trigger remain gaps;
same input paused, hypothesis table and observations: work/re/e192_animal.md.
"""
import re
from pathlib import Path

import labpaths
from maps import probe_range
from model import Mission, Script, Test, Unit, square


def mission(firing=False):
    m = Mission(name='CampAnimalE', map=probe_range, units=[])
    m.ext = firing
    root = Path(labpaths.SDK3) / 'SageXML'
    source = (root / 'Civilian/Units/CivilianFemale01.xml').read_text(encoding='utf-8-sig')
    base = (root / 'BaseObjects/BaseCivilian.xml').read_text(encoding='utf-8-sig')
    animal = re.search(r'<AnimalAIUpdate\b[^>]*/>', base).group()
    for tag, site, distance in [('Near', 'base gun', 100), ('Off', 'order gun', 100),
                                ('Far', 'removed gun', 700)]:
        ident = 'CNVE192' + tag
        xml = source.replace('id="CivilianFemale1"', f'id="{ident}"', 1)
        ai = '<AI xmlns:xai="uri:ea.com:eala:asset:instance" xai:joinAction="Replace">'
        ai += (animal if tag != 'Off' else '') + '</AI>'
        xml = xml.replace('</GameObject>', ai + '</GameObject>')
        m.units.append(Unit(ident, xml))
        m.put(ident, site, role=tag, name='E192 ' + tag)
        m.put('SovietAntiInfantryInfantry', site, distance, 0, side='s1',
              role=tag + ' enemy', name='E192 ' + tag + ' enemy')
        m.waypoint(tag, 'E192 start ' + tag, site)
        if firing:
            m.put('AlliedPowerPlant', site, distance, 140, role=tag + ' target',
                  name='E192 ' + tag + ' target')
    return m


def check(m, firing=False):
    t = Test()
    t.counters = [('E192Frame', 'frame'), ('E192Left', 'left'),
                  ('E192Live', 'live'), ('E192Start', 'start')]
    t.scripts = [Script('Test - clock', [('COUNTER', 'E192Frame', 0, 240)],
        [('INCREMENT_COUNTER', 1, 'E192Frame')], once=False),
        Script('Test - reveal', [], [('MAP_REVEAL_ALL_PERM', m.player('p1'))])]
    for tag, bit in [('Near', 1), ('Off', 2), ('Far', 4)]:
        name, enemy = m.role(tag).name, m.role(tag + ' enemy').name
        area = 'E192 start ' + tag
        t.areas[area] = square(*m.point(tag), 100)
        t.scripts += [
            Script('Test - quiet ' + tag, [], [
                ('UNIT_CHANGE_OBJECT_STATUS', enemy, 'NO_ATTACK', 1),
                ('UNIT_CHANGE_OBJECT_STATUS', enemy, 'IMMOBILE', 1)]),
            Script('Test - left ' + tag, [('COUNTER', 'E192Frame', 0, 241),
                ('NAMED_NOT_DESTROYED', name), ('NAMED_INSIDE_AREA', name, area, 'NOT')],
                [('INCREMENT_COUNTER', bit, 'E192Left')]),
            Script('Test - live ' + tag, [('COUNTER', 'E192Frame', 2, 240),
                ('NAMED_NOT_DESTROYED', name), ('NAMED_NOT_DESTROYED', enemy)],
                [('INCREMENT_COUNTER', bit, 'E192Live')]),
            Script('Test - start ' + tag, [('COUNTER', 'E192Frame', 2, 240),
                ('NAMED_INSIDE_AREA', name, area)], [('INCREMENT_COUNTER', bit, 'E192Start')])]
        if firing:
            target = m.role(tag + ' target').name
            t.scripts += [
                Script('Test - fire ' + tag, [('COUNTER', 'E192Frame', 2, 45)], [
                    ('UNIT_CHANGE_OBJECT_STATUS', enemy, 'NO_ATTACK', 0),
                    ('NAMED_ATTACK_NAMED', enemy, target)]),
                Script('Test - legal hit ' + tag, [('NAMED_NOT_DESTROYED', target),
                    ('UNIT_HEALTH', target, 0, 100),
                    ('NAMED_ATTACKED_BY_OBJECTTYPE', target, 'SovietAntiInfantryInfantry')],
                    [('INCREMENT_COUNTER', 8 * bit, 'E192Live')])]
    t.expect = [('frame', 0, 'ever==', 240), ('left', 0, 'ever==', 1),
                ('live', 0, 'ever==', 63 if firing else 7), ('start', 0, 'ever==', 6)]
    t.bench = [('bench_watch', dict(seconds=100, every=1, sheet=False, lines=4, until='c1>=240'))]
    return t


MISSION = {'engine_animal_e': mission, 'engine_animalfire_e': lambda: mission(firing=True)}
CHECKS = {'engine_animal_e': {'a': check},
          'engine_animalfire_e': {'a': lambda m: check(m, firing=True)}}
CONTROL_ARMS = {name: ('Near', 'Off') for name in MISSION}

"""Retail MagneticSingularity filter, real template identities, two controls.

a retains the retail filter, b removes only that filter. Both lanes invert.
Prediction: normal Hammer moves in both; ordinary infantry/aircraft and the
iron-curtained Hammer are rejected by a; the two IncludeThing identities
(Terror Drone and Tesla Trooper, both INFANTRY) override kind exclusion.
Their status precedence is tested by the iron-curtained Tesla Trooper.
No whole-power, airborne radius or native Iron Curtain lifecycle claim.
Bench a/b PASS: both99/99/status3/status3; shocks per lane4/7.
Aircraft has no shock in either control and no probe-position record: gap.
Retail candidates publish shock records but not the attempted probe module;
only the Hammer probes' positions are used in landing assertions.
"""
import os
import re

import labpaths
from model import Obj, Script, Unit, status
from checks import engine_knock_invert as invert
from checks import engine_knock_probe as probe


# Keep original IDs: renaming a copy would invalidate IncludeThing evidence.
CANDIDATES = {
    'drone': ('SovietScoutVehicle', 0, 65),
    'tesla': ('SovietHeavyAntiVehicleInfantry', -65, 0),
    'teslaic': ('SovietHeavyAntiVehicleInfantry', -45, -45),
    'infantry': ('AlliedAntiInfantryInfantry', 0, -65),
    'aircraft': ('SovietAntiGroundAircraft', 45, 45),
    'normal': (probe.PROBE_TANK, 45, -45),
}


def observed_template(template):
    side = 'Allied' if template.startswith('Allied') else 'Soviet'
    path = os.path.join(labpaths.SDK3, 'SageXML', side, 'Units', template + '.xml')
    with open(path, encoding='utf-8') as f:
        xml = f.read()
    assert xml.count('<Behaviors>') == 1
    xml = xml.replace('<Behaviors>', '<Behaviors><DeletionUpdate id="ModuleTag_CNVProbe" '
                      'MinFrames="15" MaxFrames="3000"/>', 1)
    return Unit(template, xml, names={'unit': template},
                what='Retail identity with read-only position probe')


def mission():
    m = invert.mission()
    m.name = 'CampKFilter'
    for lane in ('yuri', 'rocket'):
        victim = next(o for o in m.objects if o.name == probe.name(lane, 'man'))
        for part, (template, dx, dy) in CANDIDATES.items():
            m.objects.append(Obj(template, victim.x + dx, victim.y + dy,
                                 side=victim.side, name=probe.name(lane, part), site=victim.site))
    return m


def check(m, plain=False):
    t = invert.check(m, plain=True)
    payload = invert.retail_shock()
    if plain:
        payload = re.sub(r'<SpecialObjectFilter\b.*?</SpecialObjectFilter>', '', payload, flags=re.S)
    for uid in ('CNV_KnockYuri', 'CNV_KnockRocket'):
        gun = next(u for u in m.units if u.id == uid)
        gun.xml, n = re.subn(r'<MetaImpactNugget\b.*?</MetaImpactNugget>', lambda _: payload, gun.xml, flags=re.S)
        assert n == 1
    m.units += [observed_template(tpl) for tpl in sorted({c[0] for c in CANDIDATES.values()})
                if tpl != probe.PROBE_TANK]
    start = next(s for s in t.scripts if s.name == 'Test - start')
    for lane in ('yuri', 'rocket'):
        for part in CANDIDATES:
            start.do.append(('UNIT_CHANGE_OBJECT_STATUS', probe.name(lane, part), 'NO_ATTACK', 1))
        for part in ('near', 'teslaic'):
            start.do.append(('UNIT_CHANGE_OBJECT_STATUS', probe.name(lane, part), 'UNDER_IRON_CURTAIN', 1))
    # Observe the two actual status bits rather than equating a script command
    # with successful state creation. Health of the direct victims is retained.
    t.counters = [c for c in t.counters if c[1].endswith('man')]
    t.scripts = [s for s in t.scripts if not (s.name.startswith('Test - health') and s.name.endswith('near'))]
    for lane in ('yuri', 'rocket'):
        counter = 'CNV_KFilter_' + lane
        t.counters.append((counter, lane + ' status'))
        t.scripts.append(Script('Test - status reset ' + lane, [], [('SET_COUNTER', counter, 0)], once=False))
        for part, weight in (('near', 1), ('teslaic', 2)):
            t.scripts.append(Script('Test - status ' + lane + part,
                [('UNIT_HAS_OBJECT_STATUS', probe.name(lane, part), status('UNDER_IRON_CURTAIN'))],
                [('INCREMENT_COUNTER', weight, counter)], once=False))
    t.expect = [(lane + ' man', 22, '==', 99, 24) for lane in ('yuri', 'rocket')]
    t.expect += [(lane + ' status', 22, '==', 3, 24) for lane in ('yuri', 'rocket')]
    return t


MISSION = {'engine_knock_filter': mission}
CHECKS = {'engine_knock_filter': {'a': check, 'b': lambda m: check(m, plain=True)}}
